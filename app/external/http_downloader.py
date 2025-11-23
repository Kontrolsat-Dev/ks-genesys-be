from __future__ import annotations

import httpx
from typing import Any

from app.core.config import settings


class HttpDownloader:
    """
    Cliente HTTP simples para download de feeds.
    Suporta auth_kind básico (basic, bearer, api_key/header, oauth_password).
    """

    def __init__(self, timeout_s: int | None = None) -> None:
        self.timeout_s = int(timeout_s or getattr(settings, "FEED_DOWNLOAD_TIMEOUT", 30))

    async def _get_oauth_password_token(
        self,
        auth: dict[str, Any],
        timeout: int,
    ) -> tuple[str | None, str | None]:
        """
        Faz o fluxo oauth_password:
          - Lê token_url (obrigatório)
          - Lê token_method (opcional, default POST; pode ser "GET")
          - Envia o resto dos campos como parâmetros (GET) ou form (POST)
          - Espera um JSON com access_token ou token
        """
        token_url = auth.get("token_url") or auth.get("url") or auth.get("endpoint")
        if not token_url:
            return None, "oauth_password: token_url not provided"

        method = str(auth.get("token_method") or "POST").upper()

        # Enviamos todos os campos excepto estes
        payload: dict[str, Any] = {}
        for k, v in auth.items():
            if k in {"token_url", "token_method", "access_token", "token"}:
                continue
            if v is None:
                continue
            payload[str(k)] = v

        try:
            async with httpx.AsyncClient(timeout=timeout) as cli:
                if method == "GET":
                    resp = await cli.get(token_url, params=payload)
                else:
                    # POST com x-www-form-urlencoded (mais próximo do padrão OAuth)
                    resp = await cli.post(
                        token_url,
                        data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
        except Exception as e:
            return None, f"oauth_password token request failed: {e}"

        try:
            text_for_err = resp.text[:400]
        except Exception:
            text_for_err = None

        if resp.status_code >= 400:
            return None, f"oauth_password token request failed ({resp.status_code}): {text_for_err}"

        try:
            data = resp.json()
        except Exception:
            return None, f"oauth_password token response is not JSON: {text_for_err}"

        token = data.get("access_token") or data.get("token")
        if not token:
            return None, "oauth_password token response missing 'access_token'"

        return str(token), None

    async def fetch(
        self,
        *,
        url: str,
        method: str = "GET",
        headers: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth_kind: str | None = None,
        auth: dict[str, Any] | None = None,
        json_body: Any = None,
        timeout_s: int | None = None,
    ) -> tuple[int, str | None, bytes, str | None]:
        """
        Executa o pedido HTTP e devolve (status_code, content_type, raw_bytes, error_text).

        Em caso de exceção de rede, devolve status_code 599 e error_text com a mensagem.
        """
        timeout = int(timeout_s or self.timeout_s)

        # headers defensivos
        h: dict[str, str] = {}
        if headers:
            for k, v in headers.items():
                if v is None:
                    continue
                h[str(k)] = str(v)

        httpx_auth = None
        ak = (auth_kind or "").lower()
        bearer_token: str | None = None

        if ak == "basic" and isinstance(auth, dict):
            user = auth.get("username") or auth.get("user")
            pwd = auth.get("password") or auth.get("pass")
            if user is not None and pwd is not None:
                httpx_auth = httpx.BasicAuth(str(user), str(pwd))

        elif ak == "bearer" and isinstance(auth, dict):
            bearer_token = auth.get("token") or auth.get("access_token")
            if bearer_token:
                h.setdefault("Authorization", f"Bearer {bearer_token}")

        elif ak in {"header", "apikey", "api_key"} and isinstance(auth, dict):
            # Ex.: {"header":"X-API-Key","value":"..."} ou {"name":"X-Token","value":"..."}
            key = auth.get("header") or auth.get("name")
            val = auth.get("value") or auth.get("token")
            if key and val:
                h.setdefault(str(key), str(val))

        elif ak == "oauth_password" and isinstance(auth, dict):
            # 1) Se já tivermos access_token no auth, usamos direto
            bearer_token = auth.get("access_token") or auth.get("token")
            if not bearer_token:
                # 2) Caso contrário, vamos buscar ao token_url (GET ou POST, configurável)
                bearer_token, err = await self._get_oauth_password_token(auth, timeout)
                if not bearer_token:
                    return 599, None, b"", err or "oauth_password token request failed"
                auth["access_token"] = bearer_token

        h.setdefault("Authorization", f"Bearer {bearer_token}")

        # user-agent mínimo
        h.setdefault("Accept", "application/json,text/csv;q=0.9,*/*;q=0.1")
        h.setdefault("User-Agent", getattr(settings, "PS_USER_AGENT", "genesys/2.0"))

        try:
            async with httpx.AsyncClient(timeout=timeout) as cli:
                resp = await cli.request(
                    method=method or "GET",
                    url=url,
                    headers=h,
                    params=params,
                    json=json_body,
                    auth=httpx_auth,
                )
                ct = resp.headers.get("content-type")
                err_text = None
                if resp.status_code >= 400:
                    # usamos texto simples; preview depois faz decode melhor se precisar
                    try:
                        err_text = resp.text[:4096]
                    except Exception:
                        err_text = None
                return resp.status_code, ct, resp.content, err_text
        except Exception as e:  # erros de rede
            return 599, None, b"", str(e)
