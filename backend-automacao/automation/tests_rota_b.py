"""Testes automatizados da Rota B: Emulação HTTP Criptográfica Sem Navegador."""

import base64
import json
import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import httpx

from automation.services.pje_headless import (
    A1CryptoEngine,
    A1CryptoError,
    DocumentoPeticionamento,
    ExpedienteDTO,
    ManifestacaoProcessual,
    PJeApiClient,
    PJeAuthClient,
    PJeHttpSession,
    PJePeticionamentoClient,
)


class TestA1CryptoEngineHeadless(TestCase):
    """Testa o motor criptográfico A1 para a Rota B."""

    def setUp(self):
        self.engine, self.pfx_bytes, self.pwd = A1CryptoEngine.create_ephemeral_test_engine(
            common_name="ADVOGADO ROTA B:98765432100",
            oab="5691/RN",
        )

    def test_cert_info(self):
        info = self.engine.cert_info
        self.assertEqual(info.common_name, "ADVOGADO ROTA B:98765432100")
        self.assertEqual(info.cpf, "98765432100")
        self.assertFalse(info.is_expired)

    def test_sign_challenge_pkcs7_detached(self):
        desafio = "TEST-NONCE-ROTA-B-123"
        assinatura_b64 = self.engine.sign_pkcs7_detached(desafio)
        self.assertIsInstance(assinatura_b64, str)
        # Assinatura DER em Base64 deve ter tamanho consistente
        self.assertGreater(len(assinatura_b64), 500)

    def test_sign_document_cades(self):
        conteudo_pdf = b"%PDF-1.4 Fake test PDF content for peticionamento"
        assinatura_der = self.engine.sign_document_cades(conteudo_pdf)
        self.assertIsInstance(assinatura_der, bytes)
        self.assertGreater(len(assinatura_der), 200)


class TestPJeAuthClient(TestCase):
    """Testa o fluxo de autenticação Challenge-Response sem navegador."""

    def setUp(self):
        self.engine, _, _ = A1CryptoEngine.create_ephemeral_test_engine()
        self.session = PJeHttpSession(base_url="https://pje.teste.jus.br")
        self.auth_client = PJeAuthClient(session=self.session, crypto_engine=self.engine)

    def tearDown(self):
        self.session.close()

    @patch.object(httpx.Client, "request")
    def test_obter_desafio_json(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "desafio": "CHALLENGE_NONCE_ABC",
            "uuid": "session-uuid-123",
        }
        mock_request.return_value = mock_resp

        dados = self.auth_client.obter_desafio("/pje/login/cert")
        self.assertEqual(dados["desafio"], "CHALLENGE_NONCE_ABC")
        self.assertEqual(dados["uuid"], "session-uuid-123")

    @patch.object(httpx.Client, "request")
    def test_validar_assinatura(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Set-Cookie": "JSESSIONID=FAKE_SESSION_123"}
        mock_resp.json.return_value = {
            "access_token": "JWT_HEADER.PAYLOAD.SIGNATURE",
            "status": "AUTENTICADO",
        }
        mock_request.return_value = mock_resp

        resultado = self.auth_client.validar_assinatura(
            endpoint_valida="/pje/login/cert/valida",
            desafio="CHALLENGE_NONCE_ABC",
            assinatura_b64="FAKE_SIG_B64",
            uuid_sessao="session-uuid-123",
        )
        self.assertEqual(resultado["status_code"], 200)
        self.assertEqual(self.session.jwt_token, "JWT_HEADER.PAYLOAD.SIGNATURE")

    @patch.object(httpx.Client, "request")
    def test_submeter_totp(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "OK"
        mock_resp.json.return_value = {"status": "SUCESSO"}
        mock_request.return_value = mock_resp

        sucesso = self.auth_client.submeter_totp(
            endpoint_totp="/pje/login/totp",
            segredo_totp="JBSWY3DPEHPK3PXP",
        )
        self.assertTrue(sucesso)


class TestPJeApiClient(TestCase):
    """Testa o cliente de consumo REST do PJe."""

    def setUp(self):
        self.session = PJeHttpSession(base_url="https://pje.teste.jus.br")
        self.api_client = PJeApiClient(session=self.session)

    def tearDown(self):
        self.session.close()

    @patch.object(httpx.Client, "request")
    def test_obter_expedientes_painel(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "id": 102030,
                "numeroProcesso": "0801234-56.2026.8.20.5001",
                "tipoComunicacao": "Intimação",
                "destinatario": "EMPRESA ALFA LTDA",
                "dataDisponibilizacao": "2026-10-04T10:00:00",
                "prazoDias": 15,
                "dataLimite": "2026-10-25",
                "orgaoJulgador": "1ª Vara Cível de Natal",
                "teor": "Fica intimado para manifestação.",
                "segredoJustica": False,
            }
        ]
        mock_request.return_value = mock_resp

        expedientes = self.api_client.obter_expedientes_painel()
        self.assertEqual(len(expedientes), 1)
        exp = expedientes[0]
        self.assertIsInstance(exp, ExpedienteDTO)
        self.assertEqual(exp.id_expediente, "102030")
        self.assertEqual(exp.numero_processo, "0801234-56.2026.8.20.5001")
        self.assertEqual(exp.prazo_dias, 15)


class TestPJePeticionamentoClient(TestCase):
    """Testa o peticionamento eletrônico sem navegador."""

    def setUp(self):
        self.engine, _, _ = A1CryptoEngine.create_ephemeral_test_engine()
        self.session = PJeHttpSession(base_url="https://pje.teste.jus.br")
        self.peticionamento = PJePeticionamentoClient(session=self.session, crypto_engine=self.engine)

    def tearDown(self):
        self.session.close()

    @patch.object(httpx.Client, "request")
    def test_upload_e_protocolo_manifestacao(self, mock_request):
        # 1. Resposta de upload do arquivo
        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 200
        mock_upload_resp.json.return_value = {"idUpload": "upload-uuid-9988"}

        # 2. Resposta de protocolo da manifestação
        mock_protocolo_resp = MagicMock()
        mock_protocolo_resp.status_code = 200
        mock_protocolo_resp.json.return_value = {
            "recibo": "REC-2026-0001",
            "status": "PROTOCOLADO",
            "dataHora": "2026-10-04T15:30:00",
        }

        mock_request.side_effect = [mock_upload_resp, mock_protocolo_resp]

        doc_principal = DocumentoPeticionamento(
            titulo="Contestação",
            tipo_documento_id=38,
            conteudo_pdf=b"%PDF-1.4 Fake PDF principal",
        )
        manifestacao = ManifestacaoProcessual(
            id_processo=1284750,
            tipo_manifestacao="CONTESTACAO",
            documento_principal=doc_principal,
            anexos=[],
            segredo_justica=False,
        )

        retorno = self.peticionamento.protocolar_manifestacao(manifestacao)
        self.assertEqual(retorno.get("recibo"), "REC-2026-0001")
        self.assertEqual(retorno.get("status"), "PROTOCOLADO")
