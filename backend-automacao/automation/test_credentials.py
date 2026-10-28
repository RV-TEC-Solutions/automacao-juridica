import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from automation.collectors import CredentialError, credentials_for
from automation.models import AutomationRun, AutomationSource
from automation.services.pje.browser import preencher_pin_pjeoffice_atspi, verificar_identidade_autenticada


class CredentialFileTests(SimpleTestCase):
    def test_file_is_the_only_source_even_with_stale_environment(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('PJE_CERT_PIN=file-pin\nPJE_TOTP_SECRET=file-otp\nPJE_CRISTIANO_CERT_PIN=own-pin\nPJE_CRISTIANO_TOTP_SECRET=own-otp\n')
            with override_settings(PJE_CREDENTIALS_FILE=path), patch.dict(os.environ, {'PJE_CERT_PIN': 'stale'}):
                self.assertEqual(credentials_for('murilo')['PJE_CERT_PIN'], 'file-pin')
                self.assertEqual(credentials_for('cristiano')['PJE_CERT_PIN'], 'own-pin')
                path.write_text('PJE_CERT_PIN=file-pin\nPJE_TOTP_SECRET=file-otp\n')
                with self.assertRaises(CredentialError):
                    credentials_for('cristiano')

    def test_explicit_rejection_survives_pin_helper_boundary(self):
        with patch.dict(os.environ, {'PJE_CERT_PIN': 'test'}), patch(
            'automation.services.pje.browser.subprocess.run', return_value=MagicMock(returncode=3)
        ):
            with self.assertRaises(CredentialError):
                preencher_pin_pjeoffice_atspi()

    def test_mismatched_authenticated_account_is_rejected(self):
        page = MagicMock()
        page.locator.return_value.first.get_attribute.return_value = 'MURILO MARIZ DE FARIA NETO / Advogado'
        with patch.dict(os.environ, {'PJE_CURRENT_COLLECTOR': 'cristiano'}):
            with self.assertRaises(CredentialError):
                verificar_identidade_autenticada(page)
        page.locator.return_value.first.get_attribute.return_value = 'CRISTIANO LUIZ / Advogado'
        with patch.dict(os.environ, {'PJE_CURRENT_COLLECTOR': 'cristiano'}):
            verificar_identidade_autenticada(page)


@override_settings(PJE_COLLECTORS=('murilo', 'cristiano'))
class CollectorStatusTests(TestCase):
    def test_settings_distinguish_configuration_from_authentication_without_secrets(self):
        client = APIClient()
        client.force_authenticate(get_user_model().objects.create_user('credential-status'))
        AutomationRun.objects.create(source=AutomationSource.objects.get(code='pje-tjrn'), collector='cristiano', status='failed', credential_failure=True, mensagem_erro='PIN rejeitado')
        with patch('automation.collectors.credential_values', return_value={
            'PJE_CERT_PIN': 'private-pin', 'PJE_TOTP_SECRET': 'private-otp',
            'PJE_CRISTIANO_CERT_PIN': 'private-own-pin', 'PJE_CRISTIANO_TOTP_SECRET': 'private-own-otp',
        }):
            response = client.get('/api/settings/')
        self.assertEqual(response.status_code, 200)
        states = {item['code']: item for item in response.data['collectors']}
        self.assertEqual(states['murilo']['state'], 'idle')
        self.assertEqual(states['cristiano']['state'], 'blocked')
        self.assertIsNone(states['cristiano']['last_success_at'])
        self.assertNotIn('private-', str(response.data))
