"""Servidor Mock do PJeOffice em Python.

Emula a API local do PJeOffice (porta 8800) emulando as respostas HTTP
esperadas pelas aplicações web do PJe (PDPJ, Keycloak, TJRN, TRT21, etc.).
Elimina a necessidade do aplicativo desktop Java (PJeOffice Pro), interface
gráfica (Xvfb) e preenchimento de PIN via AT-SPI.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .crypto import A1CryptoEngine, A1CryptoError

logger = logging.getLogger("pjeoffice.mock")

DEFAULT_MOCK_PORT = 8800
DEFAULT_MOCK_HOST = "127.0.0.1"


class PJeOfficeMockHandler(BaseHTTPRequestHandler):
    """Handler HTTP compatível com o protocolo do PJeOffice."""

    engine: A1CryptoEngine | None = None

    def _send_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Origin, Accept")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _send_json_response(self, status_code: int, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        """Responde às checagens de CORS Preflight do Chromium."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Atende pings de liveness do PJe e rotas de status."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query = parse_qs(parsed_url.query)

        if path in ("", "/pjeOffice", "/pjeoffice", "/pjeOffice/versao", "/versao"):
            self._send_json_response(200, {
                "versao": "2.5.16u",
                "status": "OK",
                "servidor": "pjeOffice",
                "plataforma": "linux",
                "modo": "a1-mock-engine",
            })
            return

        if path == "/health":
            cert_loaded = self.engine is not None
            info = self.engine.cert_info if self.engine else None
            self._send_json_response(200, {
                "status": "UP",
                "certificate_loaded": cert_loaded,
                "certificate_cn": info.common_name if info else None,
                "days_until_expiration": info.days_until_expiration if info else None,
            })
            return

        # Alguns tribunais enviam requisição com parâmetro 'r' no GET
        if "r" in query or "desafio" in query:
            desafio = query.get("r", query.get("desafio", [""]))[0]
            self._processar_assinatura(desafio)
            return

        self._send_json_response(200, {
            "status": "OK",
            "mensagem": "PJeOffice Mock ativo",
        })

    def do_POST(self) -> None:
        """Processa requisições de assinatura do PJe."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except json.JSONDecodeError:
            body = {}

        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        if path == "/admin/reload":
            try:
                PJeOfficeMockHandler.engine = A1CryptoEngine.from_env()
                self._send_json_response(200, {
                    "sucesso": True,
                    "mensagem": "Certificado A1 recarregado com sucesso",
                    "cn": PJeOfficeMockHandler.engine.cert_info.common_name,
                })
            except Exception as exc:
                self._send_json_response(500, {"sucesso": False, "erro": str(exc)})
            return

        # Extração de dados a assinar segundo diferentes versões do PJe
        desafio = (
            body.get("dados")
            or body.get("desafio")
            or body.get("token")
            or body.get("mensagem")
            or body.get("hash")
            or body.get("challenge")
            or ""
        )

        if not desafio and isinstance(body.get("tarefa"), dict):
            desafio = body["tarefa"].get("dados") or body["tarefa"].get("desafio") or ""

        self._processar_assinatura(desafio, body)

    def _processar_assinatura(self, desafio: str, original_payload: dict[str, Any] | None = None) -> None:
        if not self.engine:
            self._send_json_response(503, {
                "sucesso": False,
                "erro": "Certificado A1 não carregado no PJeOffice Mock Server.",
            })
            return

        try:
            # Assina com o par de chaves A1 na memória (PKCS#7 Detached)
            assinatura_b64 = self.engine.sign_pkcs7_detached(desafio)
            cert_b64 = self.engine.get_certificate_der_base64()
            cadeia = self.engine.get_certificate_chain_der_base64()

            resposta: dict[str, Any] = {
                "sucesso": True,
                "codigo": 200,
                "mensagem": "Assinatura realizada com sucesso via A1 Engine",
                "versao": "2.5.16u",
                "certificado": cert_b64,
                "cadeia": cadeia,
                "assinatura": assinatura_b64,
                "resultado": assinatura_b64,
                "token": desafio,
            }

            # Caso a requisição tenha enviado um identificador de requisição (ID/UUID)
            if original_payload and "id" in original_payload:
                resposta["id"] = original_payload["id"]

            self._send_json_response(200, resposta)
        except Exception as exc:
            logger.exception("Erro ao assinar desafio no PJeOffice Mock: %s", exc)
            self._send_json_response(500, {
                "sucesso": False,
                "erro": f"Falha na assinatura criptográfica: {exc}",
            })

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


class PJeOfficeMockServer:
    """Gerenciador do ciclo de vida do servidor Mock do PJeOffice."""

    def __init__(self, host: str = DEFAULT_MOCK_HOST, port: int = DEFAULT_MOCK_PORT, engine: A1CryptoEngine | None = None):
        self.host = host
        self.port = port
        self.engine = engine
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.engine:
            try:
                self.engine = A1CryptoEngine.from_env()
            except A1CryptoError as err:
                logger.warning("Mock PJeOffice iniciado sem certificado A1 configurado: %s", err)

        PJeOfficeMockHandler.engine = self.engine
        self._server = ThreadingHTTPServer((self.host, self.port), PJeOfficeMockHandler)
        self._server.daemon_threads = True

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="PJeOfficeMockServerThread",
            daemon=True,
        )
        self._thread.start()
        logger.info("PJeOffice Mock Server rodando em http://%s:%d", self.host, self.port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("PJeOffice Mock Server finalizado.")

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._thread is not None and self._thread.is_alive()


_global_mock_server: PJeOfficeMockServer | None = None


def ensure_pjeoffice_mock_running(host: str = DEFAULT_MOCK_HOST, port: int = DEFAULT_MOCK_PORT, engine: A1CryptoEngine | None = None) -> PJeOfficeMockServer:
    """Garante que uma instância global do Mock PJeOffice está ativa no processo."""
    global _global_mock_server
    if _global_mock_server is None or not _global_mock_server.is_running:
        _global_mock_server = PJeOfficeMockServer(host=host, port=port, engine=engine)
        _global_mock_server.start()
    return _global_mock_server


def stop_pjeoffice_mock() -> None:
    """Para a instância global do Mock PJeOffice."""
    global _global_mock_server
    if _global_mock_server is not None:
        _global_mock_server.stop()
        _global_mock_server = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    engine = None
    try:
        engine = A1CryptoEngine.from_env()
        print(f"Certificado A1 carregado: {engine.cert_info.common_name}")
    except Exception as exc:
        print(f"Aviso: Iniciando sem certificado A1 configurado no ambiente ({exc})")

    server = PJeOfficeMockServer(engine=engine)
    server.start()
    print("PJeOffice Mock Server ativo. Pressione Ctrl+C para encerrar.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("Servidor encerrado.")
