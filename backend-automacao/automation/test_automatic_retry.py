from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from automation.models import AutomationRun, AutomationSource
from automation.pipeline import collection_pipeline_payload
from automation.queue import claim_next_run, enqueue_due_retry, expire_pending_retries
from automation.services.pje.runner import _enqueue_next_source


@override_settings(PJE_COLLECTORS=("murilo", "cristiano"))
class AutomaticRetryTests(TestCase):
    def setUp(self):
        self.due = datetime(2026, 8, 25, 6, tzinfo=ZoneInfo("America/Fortaleza"))
        self.now = self.due + timedelta(hours=4)
        self.first = AutomationSource.objects.get(code="pje-tjrn")
        self.second = AutomationSource.objects.get(code="pje2g-tjrn")
        self.djen = AutomationSource.objects.get(code="djen")
        AutomationSource.objects.filter(pk__in=[self.first.pk, self.second.pk, self.djen.pk]).update(enabled=True)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.djen.refresh_from_db()

    def failed(self, source=None, **kwargs):
        values = dict(source=source or self.first, trigger="scheduled", status="failed",
                      scheduled_for=self.due, finalizada_em=self.now - timedelta(hours=2))
        values.update(kwargs)
        return AutomationRun.objects.create(**values)

    def test_waits_two_hours_and_retries_only_the_failed_source_and_owner(self):
        failure = self.failed(collector="cristiano", finalizada_em=self.now - timedelta(hours=2) + timedelta(seconds=1))
        self.assertIsNone(enqueue_due_retry(self.now))
        retry = enqueue_due_retry(self.now + timedelta(seconds=1))
        self.assertEqual((retry.source, retry.collector, retry.cycle_id, retry.trigger),
                         (failure.source, "cristiano", failure.cycle_id, "retry"))
        with patch("automation.services.pje.runner.enqueue_run") as enqueue:
            _enqueue_next_source(retry)
            enqueue.assert_not_called()
        self.assertIsNone(enqueue_due_retry(self.now + timedelta(hours=3)))

    def test_sequential_fair_retries_and_repeat_interval(self):
        first = self.failed()
        self.failed(self.djen)
        retry = enqueue_due_retry(self.now)
        self.assertEqual(retry.source, self.first)
        self.assertIsNone(enqueue_due_retry(self.now))
        retry.status = "failed"
        retry.finalizada_em = self.now
        retry.save(update_fields=("status", "finalizada_em"))
        djen = enqueue_due_retry(self.now)
        self.assertEqual(djen.source, self.djen)
        djen.status = "success"
        djen.save(update_fields=("status",))
        self.assertIsNone(enqueue_due_retry(self.now + timedelta(hours=1)))
        retry2 = enqueue_due_retry(self.now + timedelta(hours=2))
        self.assertEqual((retry2.source, retry2.cycle_id), (self.first, first.cycle_id))

    def test_success_and_other_owner_preserved_in_pipeline(self):
        success = AutomationRun.objects.create(source=self.second, trigger="scheduled", status="success", scheduled_for=self.due)
        failure = self.failed(cycle_id=success.cycle_id, collector="cristiano")
        retry = enqueue_due_retry(self.now)
        retry.status = "success"
        retry.finalizada_em = self.now
        retry.save(update_fields=("status", "finalizada_em"))
        payload = collection_pipeline_payload()
        steps = {(step.get("collector"), step["code"]): step for step in payload["steps"]}
        self.assertEqual(steps[("murilo", self.second.code)]["run_id"], success.pk)
        self.assertEqual(steps[("cristiano", self.first.code)]["run_id"], retry.pk)
        self.assertEqual(payload["status"], "success")
        self.assertTrue(AutomationRun.objects.filter(pk=failure.pk, status="failed").exists())

    def test_blocked_credentials_do_not_retry_but_other_owner_and_djen_can(self):
        failure = self.failed(credential_failure=True)
        self.failed(self.second, cycle_id=failure.cycle_id)
        self.failed(self.first, collector="cristiano", cycle_id=failure.cycle_id)
        retry = enqueue_due_retry(self.now)
        self.assertEqual(retry.collector, "cristiano")
        retry.status = "success"
        retry.save(update_fields=("status",))
        self.failed(self.djen)
        self.assertEqual(enqueue_due_retry(self.now).source, self.djen)

    def test_manual_success_discard_disabled_cancel_and_expired_window(self):
        failure = self.failed()
        manual = AutomationRun.objects.create(source=self.first, collector="murilo", trigger="rerun", status="success")
        self.assertIsNone(enqueue_due_retry(self.now))
        manual.delete()
        self.first.enabled = False
        self.first.save(update_fields=("enabled",))
        self.assertIsNone(enqueue_due_retry(self.now))
        self.first.enabled = True
        self.first.save(update_fields=("enabled",))
        failure.descartada_em = self.now
        failure.save(update_fields=("descartada_em",))
        self.assertIsNone(enqueue_due_retry(self.now))
        failure.descartada_em = None
        failure.status = "cancelled"
        failure.save(update_fields=("descartada_em", "status"))
        self.assertIsNone(enqueue_due_retry(self.now))
        failure.status = "failed"
        failure.save(update_fields=("status",))
        self.assertIsNone(enqueue_due_retry(self.due + timedelta(days=1)))

    def test_overnight_window_and_running_worker(self):
        self.failed(finalizada_em=self.due + timedelta(hours=20))
        running = AutomationRun.objects.create(source=self.second, status="running")
        self.assertIsNone(enqueue_due_retry(self.due + timedelta(hours=23)))
        self.assertIsNone(claim_next_run())
        running.status = "success"
        running.save(update_fields=("status",))
        self.assertIsNotNone(enqueue_due_retry(self.due + timedelta(hours=23)))

    def test_pending_retry_expires_at_next_cycle_or_on_disabled_source(self):
        failure = self.failed()
        retry = enqueue_due_retry(self.now)
        self.assertEqual(expire_pending_retries(self.due + timedelta(days=1)), 1)
        retry.refresh_from_db()
        self.assertEqual(retry.status, "cancelled")
        self.assertIsNone(enqueue_due_retry(self.due + timedelta(days=1)))
        failure.scheduled_for = self.due + timedelta(days=1)
        failure.finalizada_em = failure.scheduled_for + timedelta(hours=1)
        failure.save(update_fields=("scheduled_for", "finalizada_em"))
        retry = enqueue_due_retry(failure.scheduled_for + timedelta(hours=3))
        self.first.enabled = False
        self.first.save(update_fields=("enabled",))
        self.assertEqual(expire_pending_retries(failure.scheduled_for + timedelta(hours=3)), 1)
        retry.refresh_from_db()
        self.assertEqual(retry.status, "cancelled")
