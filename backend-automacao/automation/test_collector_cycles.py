from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from automation.collectors import CredentialError
from automation.models import AutomationRun, AutomationSource
from automation.pipeline import collection_pipeline_payload
from automation.queue import claim_next_run, enqueue_run
from automation.services.pje.runner import executar_coleta
from automation.services.pje.sources import PJE_SOURCE_ORDER, get_source_profile
from automation.services.pje.trt21 import TRT21Collection


@override_settings(PJE_COLLECTORS=("murilo", "cristiano"))
class CollectorCycleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user("cycle-operator"))
        validator = patch("automation.views.validar_token_fisico")
        validator.start()
        self.addCleanup(validator.stop)

    def test_explicit_owner_starts_an_owner_cycle(self):
        response = self.client.post("/api/automation/runs/", {"collector": "cristiano"}, format="json")
        self.assertEqual(response.status_code, 202)
        run = AutomationRun.objects.get()
        self.assertEqual((run.collector, run.trigger, run.source.code), ("cristiano", "collector", PJE_SOURCE_ORDER[0]))

    def test_omitting_owner_keeps_the_full_cycle(self):
        response = self.client.post("/api/automation/runs/", {}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["trigger"], "manual")

    def test_owner_cycle_waits_for_an_existing_collection(self):
        AutomationRun.objects.create(source=AutomationSource.objects.get(code=PJE_SOURCE_ORDER[1]))
        response = self.client.post("/api/automation/runs/", {"collector": "cristiano"}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(AutomationRun.objects.count(), 1)

    def test_an_owner_cycle_blocks_other_cycles(self):
        enqueue_run(AutomationSource.objects.get(code=PJE_SOURCE_ORDER[0]), "collector", collector="murilo")
        with self.assertRaisesMessage(ValueError, "Aguarde a coleta"):
            enqueue_run(AutomationSource.objects.get(code=PJE_SOURCE_ORDER[1]), "manual")


@override_settings(PJE_COLLECTORS=("murilo", "cristiano"))
class CollectorCycleRunnerTests(TestCase):
    def setUp(self):
        AutomationSource.objects.filter(code__in=PJE_SOURCE_ORDER).update(enabled=True)
        credentials = patch("automation.collectors.credential_values", return_value={
            "PJE_CERT_PIN": "murilo-pin", "PJE_TOTP_SECRET": "murilo-otp",
            "PJE_CRISTIANO_CERT_PIN": "cristiano-pin", "PJE_CRISTIANO_TOTP_SECRET": "cristiano-otp",
        })
        credentials.start()
        self.addCleanup(credentials.stop)

    def test_each_owner_runs_all_sources_without_enqueuing_the_other(self):
        for owner in ("murilo", "cristiano"):
            with self.subTest(owner=owner):
                AutomationRun.objects.all().delete()
                first = enqueue_run(AutomationSource.objects.get(code=PJE_SOURCE_ORDER[0]), "collector", collector=owner)
                observed = []

                def capture(code, **kwargs):
                    observed.append(code)
                    return TRT21Collection([], "") if get_source_profile(code).collector == "trt21" else []

                with patch("automation.services.pje.runner.prepare_identity") as prepare, patch(
                    "automation.services.pje.runner.abrir_pje", side_effect=capture,
                ):
                    for _ in PJE_SOURCE_ORDER:
                        run = claim_next_run()
                        self.assertIsNotNone(run)
                        self.assertEqual((run.collector, run.trigger, run.cycle_id), (owner, "collector", first.cycle_id))
                        executar_coleta(run)
                self.assertIsNone(claim_next_run())
                self.assertEqual(observed, list(PJE_SOURCE_ORDER))
                self.assertEqual([call.args[0] for call in prepare.call_args_list], [owner] * len(PJE_SOURCE_ORDER))
                self.assertFalse(AutomationRun.objects.exclude(collector=owner).exists())

    def test_credential_rejection_stops_the_owner_cycle(self):
        run = enqueue_run(AutomationSource.objects.get(code=PJE_SOURCE_ORDER[0]), "collector", collector="murilo")
        with patch("automation.services.pje.runner.prepare_identity"), patch(
            "automation.services.pje.runner.abrir_pje", side_effect=CredentialError("PIN rejeitado"),
        ), self.assertLogs("automation", "ERROR"), self.assertRaises(CredentialError):
            executar_coleta(run)
        run.refresh_from_db()
        self.assertTrue(run.credential_failure)
        self.assertIsNone(claim_next_run())
        self.assertEqual(AutomationRun.objects.count(), 1)

    def test_source_error_continues_for_the_selected_owner(self):
        run = enqueue_run(AutomationSource.objects.get(code=PJE_SOURCE_ORDER[0]), "collector", collector="cristiano")
        with patch("automation.services.pje.runner.prepare_identity"), patch(
            "automation.services.pje.runner.abrir_pje", side_effect=RuntimeError("Fonte indisponível"),
        ), self.assertLogs("automation", "ERROR"), self.assertRaises(RuntimeError):
            executar_coleta(run)
        following = claim_next_run()
        self.assertEqual((following.collector, following.trigger, following.source.code), ("cristiano", "collector", PJE_SOURCE_ORDER[1]))


@override_settings(PJE_COLLECTORS=("murilo", "cristiano"))
class CollectorCycleHistoryTests(TestCase):
    def setUp(self):
        self.first = AutomationSource.objects.get(code=PJE_SOURCE_ORDER[0])
        self.second = AutomationSource.objects.get(code=PJE_SOURCE_ORDER[1])
        self.murilo = AutomationRun.objects.create(source=self.first, status="success", finalizada_em=timezone.now())
        self.failed = AutomationRun.objects.create(
            source=self.first, collector="cristiano", status="failed", cycle_id=self.murilo.cycle_id,
        )

    def steps(self):
        return {(step.get("collector"), step["code"]): step for step in collection_pipeline_payload()["steps"]}

    def test_new_owner_cycle_preserves_other_owner_and_its_source_rerun(self):
        previous = AutomationRun.objects.create(source=self.second, trigger="rerun", status="success")
        own = enqueue_run(self.first, "collector", collector="cristiano")
        steps = self.steps()
        self.assertEqual(steps[("murilo", self.first.code)]["run_id"], self.murilo.pk)
        self.assertEqual(steps[("murilo", self.first.code)]["status"], "success")
        self.assertEqual(steps[("murilo", self.second.code)]["run_id"], previous.pk)
        self.assertEqual(steps[("cristiano", self.first.code)]["run_id"], own.pk)
        self.assertEqual(collection_pipeline_payload()["collector_scope"], "cristiano")
        self.assertEqual(collection_pipeline_payload()["current_collector"], "cristiano")

    def test_owner_cycle_resets_only_its_own_previous_source_reruns(self):
        AutomationRun.objects.create(source=self.second, collector="cristiano", trigger="rerun", status="failed")
        enqueue_run(self.first, "collector", collector="cristiano")
        second = self.steps()[("cristiano", self.second.code)]
        self.assertEqual(second["status"], "pending")
        self.assertIsNone(second["run_id"])

    def test_source_rerun_after_owner_cycle_keeps_the_other_owner_history(self):
        own = AutomationRun.objects.create(source=self.first, collector="cristiano", trigger="collector", status="failed")
        rerun = enqueue_run(self.first, "rerun", collector="cristiano")
        steps = self.steps()
        self.assertEqual(steps[("murilo", self.first.code)]["run_id"], self.murilo.pk)
        self.assertEqual(steps[("cristiano", self.first.code)]["run_id"], rerun.pk)
        self.assertNotEqual(own.pk, rerun.pk)

    def test_new_full_cycle_starts_both_owners_afresh(self):
        AutomationRun.objects.create(source=self.first, collector="cristiano", trigger="collector", status="success")
        new = enqueue_run(self.first, "manual")
        steps = self.steps()
        self.assertEqual(steps[("murilo", self.first.code)]["run_id"], new.pk)
        self.assertEqual(steps[("cristiano", self.first.code)]["status"], "pending")
        self.assertIsNone(steps[("cristiano", self.first.code)]["run_id"])

    def test_consecutive_individual_cycles_keep_each_owners_latest_results(self):
        cristiano = AutomationRun.objects.create(source=self.first, collector="cristiano", trigger="collector", status="success")
        murilo = AutomationRun.objects.create(source=self.first, collector="murilo", trigger="collector", status="success")
        steps = self.steps()
        self.assertEqual(steps[("murilo", self.first.code)]["run_id"], murilo.pk)
        self.assertEqual(steps[("cristiano", self.first.code)]["run_id"], cristiano.pk)

    def test_without_previous_history_the_other_owner_is_not_shown_as_queued(self):
        AutomationRun.objects.all().delete()
        enqueue_run(self.first, "collector", collector="cristiano")
        steps = self.steps()
        self.assertEqual(steps[("cristiano", self.first.code)]["status"], "pending")
        self.assertEqual(steps[("murilo", self.first.code)]["status"], "skipped")
