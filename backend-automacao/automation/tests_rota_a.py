"""Testes automatizados da Rota A: Motor Criptográfico A1 e Servidor Mock PJeOffice."""

import base64
import json
import os
import urllib.request
from unittest import TestCase
from unittest.mock import patch

from automation.services.pjeoffice.crypto import A1CryptoEngine, A1CryptoError
from automation.services.pjeoffice.mock_server import PJeOfficeMockServer
from automation.services.pjeoffice.physical_token import (
    TokenFisicoError,
    is_a1_configured,
    validar_token_fisico,
)


class TestA1CryptoEngine(TestCase):
    """Testa o carregamento e operações criptográficas do A1 em memória."""

    def setUp(self):
        self.engine, self.pfx_bytes, self.pwd = A1CryptoEngine.create_ephemeral_test_engine(
            common_name="ADVOGADO TESTE:12345678900",
            oab="5691/RN",
        )

    def test_cert_info_extracted_correctly(self):
        info = self.engine.cert_info
        self.assertEqual(info.common_name, "ADVOGADO TESTE:12345678900")
        self.assertEqual(info.cpf, "12345678900")
        self.assertFalse(info.is_expired)
        self.assertGreater(info.days_until_expiration, 0)

    def test_load_from_bytes(self):
        loaded_engine = A1CryptoEngine.from_bytes(self.pfx_bytes, self.pwd)
        self.assertEqual(loaded_engine.cert_info.common_name, "ADVOGADO TESTE:12345678900")

    def test_load_wrong_password_raises_error(self):
        with self.assertRaises(A1CryptoError):
            A1CryptoEngine.from_bytes(self.pfx_bytes, "senha_errada")

    def test_load_from_env_base64(self):
        b64_pfx = base64.b64encode(self.pfx_bytes).decode("ascii")
        with patch.dict(os.environ, {
            "PJE_CERT_A1_BASE64": b64_pfx,
            "PJE_CERT_A1_PASSWORD": self.pwd,
        }):
            engine = A1CryptoEngine.from_env()
            self.assertEqual(engine.cert_info.cpf, "12345678900")

    def test_sign_pkcs7_detached(self):
        desafio = "TEST-NONCE-PJE-CHALLENGE-998877"
        assinatura_b64 = self.engine.sign_pkcs7_detached(desafio)
        self.assertIsInstance(assinatura_b64, str)
        self.assertGreater(len(assinatura_b64), 500)

        # A assinatura deve ser decodificável em Base64 para bytes DER
        der_bytes = base64.b64decode(assinatura_b64)
        self.assertTrue(len(der_bytes) > 200)

    def test_get_certificate_der_and_chain(self):
        cert_b64 = self.engine.get_certificate_der_base64()
        chain = self.engine.get_certificate_chain_der_base64()
        self.assertIsInstance(cert_b64, str)
        self.assertIsInstance(chain, list)
        self.assertGreaterEqual(len(chain), 1)


class TestPJeOfficeMockServer(TestCase):
    """Testa o servidor HTTP mock do PJeOffice na porta de testes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine, cls.pfx_bytes, cls.pwd = A1CryptoEngine.create_ephemeral_test_engine()
        cls.test_port = 8891
        cls.server = PJeOfficeMockServer(host="127.0.0.1", port=cls.test_port, engine=cls.engine)
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        super().tearDownClass()

    def test_mock_version_get(self):
        url = f"http://127.0.0.1:{self.test_port}/pjeOffice/"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "OK")
            self.assertEqual(data.get("servidor"), "pjeOffice")
            self.assertIn("Access-Control-Allow-Origin", resp.headers)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Private-Network"), "true")

    def test_mock_cors_options(self):
        url = f"http://127.0.0.1:{self.test_port}/pjeOffice/"
        req = urllib.request.Request(url, method="OPTIONS")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Private-Network"), "true")

    def test_mock_health(self):
        url = f"http://127.0.0.1:{self.test_port}/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "UP")
            self.assertTrue(data.get("certificate_loaded"))

    def test_mock_sign_post(self):
        url = f"http://127.0.0.1:{self.test_port}/pjeOffice/"
        payload = json.dumps({"desafio": "CHALLENGE-PJE-456", "servidor": "https://pje1g.tjrn.jus.br"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("sucesso"))
            self.assertIn("assinatura", data)
            self.assertIn("certificado", data)
            self.assertEqual(data.get("token"), "CHALLENGE-PJE-456")


class TestValidarTokenFisicoA1(TestCase):
    """Testa a função unificada de validação quando configurada em modo A1."""

    def setUp(self):
        self.engine, self.pfx_bytes, self.pwd = A1CryptoEngine.create_ephemeral_test_engine()
        self.b64_pfx = base64.b64encode(self.pfx_bytes).decode("ascii")

    def test_is_a1_configured(self):
        with patch.dict(os.environ, {"PJE_CERT_A1_BASE64": self.b64_pfx}):
            self.assertTrue(is_a1_configured())

        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_a1_configured())

    def test_validar_token_fisico_com_a1_valido(self):
        with patch.dict(os.environ, {
            "PJE_CERT_A1_BASE64": self.b64_pfx,
            "PJE_CERT_A1_PASSWORD": self.pwd,
        }):
            # Não deve levantar exceção mesmo sem token A3 espetado
            validar_token_fisico()
