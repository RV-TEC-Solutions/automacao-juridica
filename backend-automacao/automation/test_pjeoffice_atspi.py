"""Exercita a seleção de controles sem acessar o desktop nem enviar PINs."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch


class PJeOfficeAtspiTests(TestCase):
    def setUp(self):
        self.api = SimpleNamespace(
            ROLE_DIALOG=1, ROLE_FRAME=2, ROLE_WINDOW=3,
            ROLE_PASSWORD_TEXT=4, STATE_SHOWING=5, STATE_VISIBLE=6,
            STATE_EDITABLE=7, STATE_SENSITIVE=8,
            Registry=Mock(),
        )
        path = Path(__file__).parent / "services" / "pjeoffice" / "atspi.py"
        spec = importlib.util.spec_from_file_location("atspi_under_test", path)
        self.helper = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"pyatspi": self.api}):
            spec.loader.exec_module(self.helper)

    def node(self, name, role, children=(), visible=True):
        node = Mock(name=name)
        node.name = name
        node.getRole.return_value = role
        node.getRoleName.return_value = str(role)
        node.getState.return_value.contains.return_value = visible
        # Mock não implementa os métodos especiais de iteração.
        node.__iter__ = lambda _: iter(children)
        return node

    def test_application_name_accepts_version_changes(self):
        app = self.node("PJeOffice Pro - 3.0", 0)
        self.api.Registry.getDesktop.return_value = [app]
        self.assertIs(self.helper.localizar_aplicacao(), app)

    def test_missing_application_reports_empty_desktop(self):
        self.api.Registry.getDesktop.return_value = []
        with self.assertRaisesRegex(RuntimeError, r"Aplicações visíveis: \[\]"):
            self.helper.localizar_aplicacao()

    def test_pin_window_accepts_java_window_roles(self):
        for role in (self.api.ROLE_DIALOG, self.api.ROLE_FRAME, self.api.ROLE_WINDOW):
            with self.subTest(role=role):
                dialog = self.node(" Informe a senha ", role)
                app = self.node("PJeOffice", 0, [dialog])
                self.assertIs(self.helper.localizar_janela(app), dialog)

    def test_missing_pin_reports_other_visible_windows(self):
        dialog = self.node("Autorizar site", self.api.ROLE_DIALOG)
        hidden = self.node("Informe a senha", self.api.ROLE_DIALOG, visible=False)
        app = self.node("PJeOffice", 0, [dialog, hidden])
        with self.assertRaisesRegex(RuntimeError, "Autorizar site"):
            self.helper.localizar_janela(app)
        dialog.queryEditableText.assert_not_called()

    def test_duplicate_pin_windows_are_rejected(self):
        windows = [self.node("Informe a senha", self.api.ROLE_DIALOG) for _ in range(2)]
        with self.assertRaisesRegex(RuntimeError, "ambígua ou ausente"):
            self.helper.localizar_janela(self.node("PJeOffice", 0, windows))

    def test_only_password_fields_are_eligible(self):
        ordinary = self.node("Outro campo", 99)
        password = self.node("", self.api.ROLE_PASSWORD_TEXT)
        dialog = self.node("Informe a senha", self.api.ROLE_DIALOG, [ordinary, password])
        self.assertIs(self.helper.localizar_campo_pin(dialog), password)

    def test_rejection_is_detected_without_reading_password_contents(self):
        password = self.node('senha incorreta', self.api.ROLE_PASSWORD_TEXT)
        error = self.node('Senha incorreta', 99)
        app = self.node('PJeOffice', 0, [password, error])
        self.api.Registry.getDesktop.return_value = [app]
        with self.assertRaises(self.helper.PinRejectedError):
            self.helper.verificar_rejeicao_pin()
        password.queryText.assert_not_called()

    def test_confirm_failure_never_resubmits_pin(self):
        with patch.dict('os.environ', {'PJE_CERT_PIN': 'test-pin'}), patch.object(
            self.helper, 'verificar_rejeicao_pin'
        ), patch.object(self.helper, 'localizar_aplicacao'), patch.object(
            self.helper, 'localizar_janela'
        ), patch.object(self.helper, 'localizar_campo_pin') as field, patch.object(
            self.helper, 'localizar_botao_confirmar'
        ), patch.object(self.helper, 'acionar', side_effect=RuntimeError('action failed')) as submit:
            with self.assertRaisesRegex(RuntimeError, 'action failed'):
                self.helper.preencher_pin()
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(field.return_value.queryEditableText.return_value.setTextContents.call_count, 1)
