import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from automation.collectors import CredentialError, collector_credentials, credentials_for, get_collector
from automation.models import AutomationRun, AutomationSource
from automation.pipeline import collection_pipeline_payload
from automation.queue import claim_next_run, enqueue_run
from automation.services.pje.browser import texto_diagnostico_seguro
from automation.services.pje.persistence import salvar_expedientes
from automation.services.pje.runner import _enqueue_next_source, executar_coleta
from automation.services.pje.sources import PJE_SOURCE_ORDER, get_source_profile
from automation.services.pje.trt21 import TRT21Collection
from automation.services.pjeoffice.identity import prepare_identity, verify_token
from automation.services.pjeoffice import identity
from expedientes.models import Expediente, ExpedienteEvent
from expedientes.tests import payload


class CredentialIsolationTests(SimpleTestCase):
    def setUp(self):
        reader = patch("automation.collectors.credential_values", side_effect=lambda: dict(os.environ))
        reader.start()
        self.addCleanup(reader.stop)

    def test_diagnostics_redact_credentials_for_both_owners(self):
        values = {
            "PJE_MURILO_CERT_PIN": "first-pin", "PJE_MURILO_TOTP_SECRET": "first-otp",
            "PJE_CRISTIANO_CERT_PIN": "second-pin", "PJE_CRISTIANO_TOTP_SECRET": "second-otp",
        }
        with patch.dict(os.environ, values, clear=True):
            result = texto_diagnostico_seguro(" ".join(values.values()))
        self.assertEqual(result, " ".join(["[omitido]"] * 4))

    def test_cristiano_never_uses_the_legacy_pin_or_totp(self):
        with patch.dict(os.environ, {"PJE_CERT_PIN": "legacy", "PJE_TOTP_SECRET": "legacy"}, clear=True):
            with self.assertRaisesMessage(RuntimeError, "PJE_CRISTIANO_CERT_PIN"):
                credentials_for("cristiano")

    def test_environment_is_restored_after_failure(self):
        values = {"PJE_CERT_PIN": "legacy", "PJE_TOTP_SECRET": "legacy-otp",
                  "PJE_CRISTIANO_CERT_PIN": "other-pin", "PJE_CRISTIANO_TOTP_SECRET": "other-otp"}
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaises(ValueError):
                with collector_credentials("cristiano"):
                    self.assertEqual(os.environ["PJE_CERT_PIN"], "other-pin")
                    self.assertEqual(os.environ["PJE_TOTP_SECRET"], "other-otp")
                    raise ValueError("coleta interrompida")
            self.assertEqual(dict(os.environ), values)

    def test_rejects_wrong_or_multiple_tokens_before_launching_office(self):
        with TemporaryDirectory() as directory:
            module = Path(directory) / "driver.so"
            module.touch()
            for output in ("serial num : wrong", "serial num : 027ef6e7\nserial num : wrong"):
                with self.subTest(output=output), patch.dict(os.environ, {"PJE_CRISTIANO_PKCS11_MODULE": str(module)}), patch(
                    "automation.services.pjeoffice.identity.subprocess.run",
                    return_value=SimpleNamespace(returncode=0, stdout=output),
                ):
                    with self.assertRaisesMessage(RuntimeError, "antes de tentar o PIN"):
                        verify_token(get_collector("cristiano"))

    def test_does_not_manage_the_desktop_signer(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "automation.services.pjeoffice.identity.subprocess.Popen"
        ) as launch:
            with self.assertRaisesMessage(RuntimeError, "worker Docker"):
                prepare_identity("cristiano")
            launch.assert_not_called()

    def test_identity_profile_copies_only_site_authorizations(self):
        with TemporaryDirectory() as directory:
            home = Path(directory)
            base = home / ".pjeoffice-pro"
            base.mkdir()
            (base / "pjeoffice-pro.config").write_text(
                "list.server=https://trusted.example\nlist.a3=other-driver\n"
                "list.a1=other-certificate\nremembered=other-selection\n"
            )
            module = home / "driver.so"
            module.touch()
            process = SimpleNamespace(pid=12345, poll=lambda: None)
            with (
                patch.dict(os.environ, {"PJE_OFFICE_MANAGED": "true"}),
                patch.object(identity.Path, "home", return_value=home),
                patch.object(identity, "PID_FILE", home / "office.pid"),
                patch.object(identity, "_current_identity", None),
                patch.object(identity, "verify_token", return_value=module),
                patch.object(identity, "_stop_managed_office") as stop,
                patch.object(identity.subprocess, "Popen", return_value=process) as launch,
                patch.object(identity.socket, "create_connection"),
            ):
                prepare_identity("cristiano")
                profile_home = base / "identities" / "cristiano"
                config = profile_home / ".pjeoffice-pro" / "pjeoffice-pro.config"
                self.assertEqual(config.read_text().splitlines(), [
                    f"list.a3={module}", "list.a1=", "list.server=https://trusted.example",
                ])
                self.assertEqual(launch.call_args.kwargs["env"]["PJE_OFFICE_USER_HOME"], str(profile_home))
                self.assertEqual((home / "office.pid").read_text(), "12345")
                stop.assert_called_once()


@override_settings(PJE_COLLECTORS=("murilo", "cristiano"))
class CollectorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user("collector-operator"))

    def test_rerun_enqueues_only_the_requested_owner(self):
        with patch("automation.views.validar_token_fisico"):
            response = self.client.post("/api/automation/runs/", {
                "source": "pje-tjrn", "collector": "cristiano", "rerun": True,
            }, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["collector"], "cristiano")
        self.assertEqual(AutomationRun.objects.get().collector, "cristiano")

    @override_settings(PJE_COLLECTORS=("murilo",))
    def test_api_rejects_a_disabled_owner(self):
        with patch("automation.views.validar_token_fisico"):
            response = self.client.post("/api/automation/runs/", {
                "source": "pje-tjrn", "collector": "cristiano", "rerun": True,
            }, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertFalse(AutomationRun.objects.exists())


@override_settings(PJE_COLLECTORS=("murilo", "cristiano"))
class CollectorPipelineTests(TestCase):
    def setUp(self):
        reader = patch("automation.collectors.credential_values", side_effect=lambda: dict(os.environ))
        reader.start()
        self.addCleanup(reader.stop)

    def test_rejected_pin_skips_owner_and_continues_next_owner(self):
        run = enqueue_run(AutomationSource.objects.get(code="pje-tjrn"), "manual", collector="murilo")
        with patch.dict(os.environ, {"PJE_CERT_PIN": "test", "PJE_TOTP_SECRET": "test"}), patch(
            "automation.services.pje.runner.prepare_identity"
        ), patch("automation.services.pje.runner.abrir_pje", side_effect=CredentialError("PIN rejeitado")) as browser:
            with self.assertRaises(CredentialError):
                executar_coleta(run)
        run.refresh_from_db()
        self.assertTrue(run.credential_failure)
        self.assertEqual(browser.call_count, 1)
        following = AutomationRun.objects.get(status="pending")
        self.assertEqual((following.collector, following.source.code), ("cristiano", "pje-tjrn"))
        # Mesmo um trabalho já existente no ciclo não pode reenviar o PIN.
        blocked = AutomationRun.objects.create(source=AutomationSource.objects.get(code="pje2g-tjrn"), collector="murilo", cycle_id=run.cycle_id)
        with patch("automation.services.pje.runner.abrir_pje") as browser:
            with self.assertRaises(CredentialError):
                executar_coleta(blocked)
        browser.assert_not_called()

    @override_settings(PJE_COLLECTORS=("murilo",))
    def test_single_owner_steps_identify_the_current_collector(self):
        run = enqueue_run(AutomationSource.objects.get(code="pje-tjrn"), "manual")

        dashboard = collection_pipeline_payload()

        self.assertEqual(dashboard["current_collector"], "murilo")
        current = next(step for step in dashboard["steps"] if step["run_id"] == run.pk)
        self.assertEqual(current["collector"], dashboard["current_collector"])
        self.assertEqual(current["group"], "TJRN")

    def test_rerun_updates_only_the_requested_collectors_step(self):
        source = AutomationSource.objects.get(code="pje-tjrn")
        original = AutomationRun.objects.create(source=source, collector="murilo", status="success")
        AutomationRun.objects.create(
            source=source, collector="cristiano", status="failed", cycle_id=original.cycle_id,
        )
        rerun = enqueue_run(source, "rerun", collector="cristiano")

        dashboard = collection_pipeline_payload()
        steps = {step["collector"]: step for step in dashboard["steps"] if step["code"] == source.code}

        self.assertEqual(steps["murilo"]["run_id"], original.pk)
        self.assertEqual(steps["murilo"]["status"], "success")
        self.assertEqual(steps["cristiano"]["run_id"], rerun.pk)
        self.assertEqual(steps["cristiano"]["status"], "pending")
        self.assertEqual(dashboard["current_collector"], "cristiano")

    def test_runs_all_sources_for_murilo_then_restarts_for_cristiano(self):
        AutomationSource.objects.filter(code__in=PJE_SOURCE_ORDER).update(enabled=True)
        first = enqueue_run(AutomationSource.objects.get(code=PJE_SOURCE_ORDER[0]), "manual")
        observed = []

        def capture(code, **kwargs):
            observed.append((os.environ["PJE_CERT_PIN"], code))
            if get_source_profile(code).collector == "trt21":
                return TRT21Collection([], "")
            return []

        with patch.dict(os.environ, {
            "PJE_CERT_PIN": "murilo-pin", "PJE_TOTP_SECRET": "murilo-otp",
            "PJE_CRISTIANO_CERT_PIN": "cristiano-pin", "PJE_CRISTIANO_TOTP_SECRET": "cristiano-otp",
        }), patch("automation.services.pje.runner.prepare_identity") as prepare, patch(
            "automation.services.pje.runner.abrir_pje", side_effect=capture,
        ):
            for _ in range(2 * len(PJE_SOURCE_ORDER)):
                run = claim_next_run()
                self.assertIsNotNone(run)
                executar_coleta(run)
            self.assertIsNone(claim_next_run())
        self.assertEqual(observed, [(f"{owner}-pin", code) for owner in ("murilo", "cristiano") for code in PJE_SOURCE_ORDER])
        self.assertEqual([call.args[0] for call in prepare.call_args_list], [owner for owner in ("murilo", "cristiano") for _ in PJE_SOURCE_ORDER])
        self.assertEqual(AutomationRun.objects.filter(cycle_id=first.cycle_id, status="success").count(), 24)
        dashboard = collection_pipeline_payload()
        self.assertEqual(dashboard["completed"], 24)
        self.assertEqual(dashboard["total"], 25)  # DJEN continua independente.
        self.assertEqual(dashboard["steps"][12]["collector"], "cristiano")

    def test_failed_source_continues_with_the_same_owner(self):
        run = AutomationRun.objects.create(source=AutomationSource.objects.get(code="pje-tjrn"), collector="cristiano")
        with patch.dict(os.environ, {
            "PJE_CRISTIANO_CERT_PIN": "pin", "PJE_CRISTIANO_TOTP_SECRET": "otp",
        }), patch("automation.services.pje.runner.prepare_identity", side_effect=RuntimeError("token errado")), patch(
            "automation.services.pje.runner.abrir_pje"
        ) as browser, self.assertLogs("automation", "ERROR"):
            with self.assertRaisesMessage(RuntimeError, "token errado"):
                executar_coleta(run)
        browser.assert_not_called()
        next_run = AutomationRun.objects.get(status="pending")
        self.assertEqual((next_run.collector, next_run.source.code), ("cristiano", "pje2g-tjrn"))

    def test_next_phase_is_not_enqueued_twice_and_reruns_do_not_chain(self):
        run = AutomationRun.objects.create(source=AutomationSource.objects.get(code=PJE_SOURCE_ORDER[-1]), status="success")
        _enqueue_next_source(run)
        _enqueue_next_source(run)
        self.assertEqual(AutomationRun.objects.filter(status="pending", collector="cristiano").count(), 1)
        run.trigger = "rerun"
        _enqueue_next_source(run)
        self.assertEqual(AutomationRun.objects.filter(status="pending").count(), 1)


class CollectorReconciliationTests(TestCase):
    def setUp(self):
        self.source = AutomationSource.objects.get(code="pje-tjrn")
        self.murilo = AutomationRun.objects.create(source=self.source, collector="murilo", status="success")
        self.cristiano = AutomationRun.objects.create(source=self.source, collector="cristiano", status="success")

    def collect(self, records, run):
        return salvar_expedientes(records, source=self.source, run=run)

    def test_empty_cristiano_box_does_not_archive_murilo_items(self):
        self.collect([payload()], self.murilo)
        result = self.collect([], self.cristiano)
        self.assertEqual(result["resolvidos"], 0)
        self.assertTrue(Expediente.objects.get().ativo)

    def test_shared_item_is_unique_and_only_resolves_when_absent_for_both(self):
        self.collect([payload()], self.murilo)
        self.collect([payload()], self.cristiano)
        self.assertEqual(Expediente.objects.count(), 1)
        self.assertEqual(Expediente.objects.get().collection_accounts, {"murilo": True, "cristiano": True})
        self.assertEqual(self.collect([], self.murilo)["resolvidos"], 0)
        self.assertTrue(Expediente.objects.get().ativo)
        self.assertEqual(self.collect([], self.cristiano)["resolvidos"], 1)
        self.assertFalse(Expediente.objects.get().ativo)
        event = ExpedienteEvent.objects.filter(kind="resolved").get()
        self.assertEqual(event.changes["collection_accounts"]["after"], {"murilo": False, "cristiano": False})

    def test_legacy_record_belongs_to_murilo_and_returns_after_resolution(self):
        self.collect([payload()], self.murilo)
        Expediente.objects.update(collection_accounts={})
        self.collect([], self.cristiano)
        self.assertTrue(Expediente.objects.get().ativo)
        self.collect([], self.murilo)
        self.assertFalse(Expediente.objects.get().ativo)
        self.collect([payload()], self.cristiano)
        self.assertTrue(Expediente.objects.get().ativo)
