"""Autenticação Challenge-Response Headless para PJe (Rota B).

Executa o ciclo completo de autenticação criptográfica sem navegador:
1. Obtenção do desafio (nonce / token) do tribunal;
2. Assinatura PKCS#7 Detached (SHA-256) em memória com o Certificado A1;
3. Submissão da resposta, certificado e cadeia de ACs ICP-Brasil;
4. Resolução de TOTP / MFA (2FA) quando exigido pelo tribunal;
5. Obtenção do cookie JSESSIONID e/ou JWT access_token.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import pyotp

from .crypto import A1CryptoEngine, A1CryptoError
from .session import PJeHttpSession

logger = logging.getLogger("pje.headless.auth")


class PJeAuthError(RuntimeError):
    """Exceção levantada para falhas no fluxo de autenticação headless."""


class PJeAuthClient:
    """Orquestrador do protocolo Challenge-Response do PJe."""

    def __init__(self, session: PJeHttpSession, crypto_engine: A1CryptoEngine | None = None):
        self.session = session
        self.engine = crypto_engine or A1CryptoEngine.from_env()

    def gerar_codigo_totp(self, segredo: str) -> str:
        """Gera código TOTP sincronizado com margem de segurança contra drift de relógio."""
        totp = pyotp.TOTP(segredo)
        restante = totp.interval - (time.time() % totp.interval)
        if restante < 5:
            time.sleep(restante)
        return totp.now()

    def obter_desafio(self, endpoint_desafio: str) -> dict[str, Any]:
        """Passo 1: Requisita o desafio (nonce/token) ao servidor do PJe."""
        logger.info("Adquirindo desafio criptográfico em: %s", endpoint_desafio)
        resp = self.session.get(endpoint_desafio, retry_on_401=False)

        if resp.status_code >= 400:
            raise PJeAuthError(f"Erro ao obter desafio do tribunal ({resp.status_code}): {resp.text[:200]}")

        # Suporte a respostas JSON e HTML (Seam / Keycloak)
        try:
            dados = resp.json()
            desafio = dados.get("desafio") or dados.get("nonce") or dados.get("token") or dados.get("hash")
            uuid_sessao = dados.get("uuid") or dados.get("state") or dados.get("id")
            if desafio:
                return {"desafio": desafio, "uuid": uuid_sessao, "raw": dados}
        except Exception:
            pass

        # Parse em HTML para PJe 1.x legado (JBoss Seam / inputs hidden)
        html = resp.text
        match_desafio = re.search(r'name=["\'](?:desafio|token|nonce)["\']\s+value=["\']([^"\']+)["\']', html, re.I)
        match_uuid = re.search(r'name=["\'](?:uuid|state|javax\.faces\.ViewState)["\']\s+value=["\']([^"\']+)["\']', html, re.I)

        desafio = match_desafio.group(1) if match_desafio else ""
        uuid_sessao = match_uuid.group(1) if match_uuid else ""

        if not desafio:
            # Caso o endpoint devolva o texto puro do nonce
            if len(resp.text.strip()) in range(16, 256):
                return {"desafio": resp.text.strip(), "uuid": uuid_sessao, "raw": resp.text}
            raise PJeAuthError(f"Não foi possível extrair o desafio criptográfico da resposta de {endpoint_desafio}.")

        return {"desafio": desafio, "uuid": uuid_sessao, "raw": html}

    def assinar_desafio(self, desafio_texto: str) -> str:
        """Passo 2: Assina o texto do desafio com a chave privada A1 em memória."""
        logger.info("Assinando desafio criptográfico com A1 (PKCS#7 Detached SHA-256)...")
        return self.engine.sign_pkcs7_detached(desafio_texto)

    def validar_assinatura(
        self,
        endpoint_valida: str,
        desafio: str,
        assinatura_b64: str,
        uuid_sessao: str | None = None,
    ) -> dict[str, Any]:
        """Passo 3: Submete a resposta assinada, certificado e dados ao PJe."""
        logger.info("Submetendo assinatura digital ao endpoint de validação: %s", endpoint_valida)

        payload = {
            "desafio": desafio,
            "assinatura": assinatura_b64,
            "certificado": self.engine.get_certificate_der_base64(),
            "cadeia": self.engine.get_certificate_chain_der_base64(),
        }
        if uuid_sessao:
            payload["uuid"] = uuid_sessao
            payload["state"] = uuid_sessao

        resp = self.session.post(endpoint_valida, json=payload, retry_on_401=False)

        if resp.status_code >= 400:
            raise PJeAuthError(f"PJe rejeitou a validação da assinatura digital ({resp.status_code}): {resp.text[:300]}")

        # Extração de JWT ou indicador de sucesso
        resultado: dict[str, Any] = {"status_code": resp.status_code, "headers": dict(resp.headers)}
        try:
            dados = resp.json()
            resultado["data"] = dados
            if "access_token" in dados:
                self.session.set_jwt_token(dados["access_token"])
        except Exception:
            resultado["text"] = resp.text

        return resultado

    def submeter_totp(self, endpoint_totp: str, segredo_totp: str, payload_base: dict[str, Any] | None = None) -> bool:
        """Passo 4: Submete o código de segundo fator (TOTP/2FA) ao tribunal."""
        codigo = self.gerar_codigo_totp(segredo_totp)
        logger.info("Submetendo segundo fator TOTP (%s) para: %s", codigo[:2] + "****", endpoint_totp)

        dados = payload_base.copy() if payload_base else {}
        dados["codigoOtp"] = codigo
        dados["codigo"] = codigo

        resp = self.session.post(endpoint_totp, json=dados, retry_on_401=False)
        if resp.status_code >= 400 or "inválido" in resp.text.lower():
            raise PJeAuthError(f"Falha ao validar segundo fator TOTP: {resp.text[:200]}")

        try:
            body = resp.json()
            if "access_token" in body:
                self.session.set_jwt_token(body["access_token"])
        except Exception:
            pass

        return True

    def autenticar_fluxo_completo(
        self,
        endpoint_desafio: str,
        endpoint_valida: str,
        endpoint_totp: str | None = None,
        segredo_totp: str | None = None,
    ) -> bool:
        """Executa a cadeia completa de autenticação Challenge-Response."""
        # 1. Adquire desafio
        info_desafio = self.obter_desafio(endpoint_desafio)
        desafio = info_desafio["desafio"]
        uuid_sessao = info_desafio.get("uuid")

        # 2. Assina
        assinatura_b64 = self.assinar_desafio(desafio)

        # 3. Valida assinatura
        res_valida = self.validar_assinatura(endpoint_valida, desafio, assinatura_b64, uuid_sessao)

        # 4. TOTP se configurado e exigido
        segredo = segredo_totp or os.environ.get("PJE_TOTP_SECRET")
        if endpoint_totp and segredo:
            self.submeter_totp(endpoint_totp, segredo)

        logger.info("Autenticação headless PJe concluída com sucesso!")
        return True
