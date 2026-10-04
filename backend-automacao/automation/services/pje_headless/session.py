"""Gerenciador de Sessão HTTP e Conexões para PJe Headless (Rota B).

Fornece cliente HTTP resiliente (baseado em HTTPX) com:
- Jar de cookies persistente para manter JSESSIONID;
- Gerenciamento de tokens JWT (PDPJ / Keycloak);
- Cabeçalhos padronizados de navegador moderno para evasão de WAF;
- Middleware de detecção de expiração de sessão (401/302) e auto-renovação;
- Suporte a proxies corporativos/residenciais.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

import httpx

logger = logging.getLogger("pje.headless.session")

DEFAULT_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Linux"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


class PJeHttpSession:
    """Cliente HTTP com gerenciamento de estado de autenticação e sessão."""

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        proxy_url: str | None = None,
        on_session_expired: Callable[[], bool] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.proxy_url = proxy_url or os.environ.get("PJE_PROXY_URL")
        self.on_session_expired = on_session_expired
        self._jwt_token: str | None = None

        self._client = httpx.Client(
            headers=dict(DEFAULT_BROWSER_HEADERS),
            timeout=self.timeout,
            follow_redirects=True,
            proxy=self.proxy_url,
        )

    @property
    def client(self) -> httpx.Client:
        return self._client

    @property
    def cookies(self) -> httpx.Cookies:
        return self._client.cookies

    @property
    def jwt_token(self) -> str | None:
        return self._jwt_token

    def set_jwt_token(self, token: str) -> None:
        """Define o token JWT de autorização (padrão PDPJ/Keycloak)."""
        self._jwt_token = token
        self._client.headers["Authorization"] = f"Bearer {token}"

    def clear_session(self) -> None:
        """Limpa cookies e tokens da sessão."""
        self._client.cookies.clear()
        self._jwt_token = None
        self._client.headers.pop("Authorization", None)

    def request(
        self,
        method: str,
        url: str,
        retry_on_401: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        """Executa uma requisição HTTP com verificação e renovação transparente de sessão."""
        target_url = url if url.startswith(("http://", "https://")) else f"{self.base_url}/{url.lstrip('/')}"

        response = self._client.request(method, target_url, **kwargs)

        # Detecta expiração de sessão (401, 403 não autorizado ou redirect para login)
        is_unauthorized = response.status_code in (401, 403)
        redirected_to_login = "/login" in str(response.url).lower() and not ("/login" in target_url.lower())

        if (is_unauthorized or redirected_to_login) and retry_on_401 and self.on_session_expired:
            logger.info("Sessão PJe expirada detectada. Disparando renovação automática...")
            renewed = self.on_session_expired()
            if renewed:
                logger.info("Sessão PJe renovada com sucesso. Repetindo requisição original...")
                return self._client.request(method, target_url, **kwargs)
            logger.error("Falha ao renovar sessão PJe.")

        return response

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PJeHttpSession:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
