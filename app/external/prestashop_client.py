from __future__ import annotations
import logging
import time
from typing import Any

import certifi
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, Timeout, ConnectionError as ConnErr

from app.core.config import settings

log = logging.getLogger("gsm.external.prestashop_client")


def _mask_email(email: str) -> str:
    try:
        local, _, domain = email.partition("@")
        if not domain:
            return email[:2] + "…" if email else ""
        return (local[:2] + "…" if local else "") + "@" + domain
    except Exception:
        return "masked"


def _len_bytes(b: bytes | None) -> int:
    return len(b or b"")


class PrestashopClient:
    """
    Stateless HTTP client for Prestashop auth via r_genesys module.
    - No credential hardcoding.
    - POST with light retry only for transient network/server errors.
    - Safe logging (never logs password or secret keys).
    """

    def __init__(self) -> None:
        self.validate_url: str | None = getattr(settings, "PS_AUTH_VALIDATE_URL", None)
        self.categories_url: str | None = getattr(settings, "PS_CATEGORIES_URL", None)
        self.brands_url: str | None = getattr(settings, "PS_BRANDS_URL", None)
        self.products_url: str | None = getattr(settings, "PS_PRODUCTS_URL", None)
        self.header_name: str | None = getattr(settings, "PS_AUTH_VALIDATE_HEADER", None)
        self.genesys_key: str | None = getattr(settings, "PS_GENESYS_KEY", None)

        if not self.validate_url or not self.header_name or not self.genesys_key:
            raise ValueError(
                "Prestashop auth configuration is missing: "
                "PS_AUTH_VALIDATE_URL / PS_AUTH_VALIDATE_HEADER / PS_GENESYS_KEY"
            )

        # separate (connect, read) timeouts
        self.timeout: tuple[float, float] = (
            float(getattr(settings, "PS_AUTH_CONNECT_TIMEOUT_S", 5)),
            float(getattr(settings, "PS_AUTH_READ_TIMEOUT_S", 10)),
        )
        verify_env = str(
            getattr(settings, "PS_AUTH_VERIFY_SSL", getattr(settings, "PS_VERIFY_SSL", "true"))
        ).lower()
        self.verify = certifi.where() if verify_env != "false" else False
        self.user_agent = getattr(settings, "PS_USER_AGENT", "genesys/2.0")

        # retry knobs
        self.retry_attempts = int(getattr(settings, "PS_AUTH_RETRY_ATTEMPTS", 2))
        self.retry_backoff = float(getattr(settings, "PS_AUTH_RETRY_BACKOFF_S", 0.4))

    def login(self, email: str, password: str) -> dict[str, Any]:
        if not email or not password:
            raise ValueError("email and password are required")

        headers = {
            self.header_name: self.genesys_key,  # value not logged
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Connection": "close",  # stateless: close TCP after response
        }

        payload = {"email": email, "password": password}
        url = self.validate_url

        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts + 1):
            start = time.perf_counter()
            try:
                log.debug(
                    "ps.auth POST start attempt=%d url=%s email=%s",
                    attempt + 1,
                    url,
                    _mask_email(email),
                )

                resp = requests.post(
                    url, json=payload, headers=headers, timeout=self.timeout, verify=self.verify
                )
                dur_ms = (time.perf_counter() - start) * 1000.0

                sc = resp.status_code
                ctype = resp.headers.get("Content-Type")
                clen = _len_bytes(resp.content)

                log.info(
                    "ps.auth POST done status=%s dur=%.1fms ctype=%s len=%d attempt=%d",
                    sc,
                    dur_ms,
                    ctype,
                    clen,
                    attempt + 1,
                )

                if 200 <= sc < 300:
                    # parse json strictly
                    try:
                        data = resp.json() if resp.content else {}
                    except Exception as parse_err:
                        log.warning(
                            "ps.auth json_parse_error dur=%.1fms len=%d attempt=%d",
                            dur_ms,
                            clen,
                            attempt + 1,
                        )
                        raise RuntimeError("upstream_invalid_json") from parse_err

                    user = data.get("user") if isinstance(data.get("user"), dict) else {}
                    uid = user.get("id") or data.get("id") or data.get("user_id")
                    if not uid:
                        log.warning(
                            "ps.auth missing_user dur=%.1fms attempt=%d", dur_ms, attempt + 1
                        )
                        raise RuntimeError("auth_failed:missing_user")

                    email_out = user.get("email") or data.get("email") or email
                    name = user.get("name") or data.get("name") or "Guest"
                    role = user.get("role") or data.get("role") or "user"
                    return {"id": uid, "email": email_out, "name": name, "role": role}

                if sc in (401, 403):
                    log.warning(
                        "ps.auth unauthorized status=%s dur=%.1fms attempt=%d",
                        sc,
                        dur_ms,
                        attempt + 1,
                    )
                    raise RuntimeError(f"auth_failed:{sc}")

                if 500 <= sc < 600:
                    log.warning(
                        "ps.auth upstream_5xx status=%s dur=%.1fms attempt=%d will_retry=%s",
                        sc,
                        dur_ms,
                        attempt + 1,
                        attempt < self.retry_attempts,
                    )
                    raise RuntimeError(f"upstream_5xx:{sc}")

                # 4xx (except 401/403), 429, etc.
                log.warning(
                    "ps.auth upstream_http status=%s dur=%.1fms attempt=%d", sc, dur_ms, attempt + 1
                )
                raise RuntimeError(f"upstream_http:{sc}")

            except (ConnectTimeout, ReadTimeout, Timeout, ConnErr) as e:
                last_exc = e
                dur_ms = (time.perf_counter() - start) * 1000.0
                will_retry = attempt < self.retry_attempts
                log.warning(
                    "ps.auth network_error=%s dur=%.1fms attempt=%d will_retry=%s",
                    e.__class__.__name__,
                    dur_ms,
                    attempt + 1,
                    will_retry,
                )
                if will_retry:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise RuntimeError("upstream_timeout") from e

            except RuntimeError as e:
                last_exc = e
                # only retry on 5xx marker
                if str(e).startswith("upstream_5xx:") and attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise

        # safeguard
        raise last_exc or RuntimeError("upstream_unknown")

    def get_categories(self) -> dict[str, Any]:
        """
        categorias do Prestashop via r_genesys.

        - Usa o mesmo header de validação (self.header_name + self.genesys_key)
        - Usa GET em vez de POST
        - Aplica o mesmo esquema de retry
        - Devolve o envelope completo (root_category_id, language_id, shop_id, categories)
        """
        url = self.categories_url

        headers = {
            self.header_name: self.genesys_key,  # value not logged
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Connection": "close",  # stateless: close TCP after response
        }

        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts + 1):
            start = time.perf_counter()
            try:
                log.debug(
                    "ps.categories GET start attempt=%d url=%s",
                    attempt + 1,
                    url,
                )

                resp = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify,
                )
                dur_ms = (time.perf_counter() - start) * 1000.0

                sc = resp.status_code
                ctype = resp.headers.get("Content-Type")
                clen = _len_bytes(resp.content)

                log.info(
                    "ps.categories GET done status=%s dur=%.1fms ctype=%s len=%d attempt=%d",
                    sc,
                    dur_ms,
                    ctype,
                    clen,
                    attempt + 1,
                )

                if 200 <= sc < 300:
                    # parse json rigidamente
                    try:
                        data = resp.json() if resp.content else []
                    except Exception as parse_err:
                        log.warning(
                            "ps.categories json_parse_error dur=%.1fms len=%d attempt=%d",
                            dur_ms,
                            clen,
                            attempt + 1,
                        )
                        raise RuntimeError("upstream_invalid_json") from parse_err

                    # Validar estrutura esperada
                    if not isinstance(data, dict):
                        log.warning(
                            "ps.categories invalid_payload_type type=%s",
                            type(data).__name__,
                        )
                        raise RuntimeError("invalid_categories_payload")

                    # Devolve o envelope completo para validação pelo schema
                    return data

                if sc in (401, 403):
                    log.warning(
                        "ps.categories unauthorized status=%s dur=%.1fms attempt=%d",
                        sc,
                        dur_ms,
                        attempt + 1,
                    )
                    raise RuntimeError(f"auth_failed:{sc}")

                if 500 <= sc < 600:
                    log.warning(
                        "ps.categories upstream_5xx status=%s dur=%.1fms attempt=%d will_retry=%s",
                        sc,
                        dur_ms,
                        attempt + 1,
                        attempt < self.retry_attempts,
                    )
                    raise RuntimeError(f"upstream_5xx:{sc}")

                log.warning(
                    "ps.categories upstream_http status=%s dur=%.1fms attempt=%d",
                    sc,
                    dur_ms,
                    attempt + 1,
                )
                raise RuntimeError(f"upstream_http:{sc}")

            except (ConnectTimeout, ReadTimeout, Timeout, ConnErr) as e:
                last_exc = e
                dur_ms = (time.perf_counter() - start) * 1000.0
                will_retry = attempt < self.retry_attempts
                log.warning(
                    "ps.categories network_error=%s dur=%.1fms attempt=%d will_retry=%s",
                    e.__class__.__name__,
                    dur_ms,
                    attempt + 1,
                    will_retry,
                )
                if will_retry:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise RuntimeError("upstream_timeout") from e

            except RuntimeError as e:
                last_exc = e
                if str(e).startswith("upstream_5xx:") and attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise

        raise last_exc or RuntimeError("upstream_unknown")

    def get_brands(self) -> dict[str, Any]:
        """
        categorias do Prestashop via r_genesys.

        - Usa o mesmo header de validação (self.header_name + self.genesys_key)
        - Usa GET em vez de POST
        - Aplica o mesmo esquema de retry
        - Devolve o envelope completo (root_category_id, language_id, shop_id, categories)
        """
        url = self.brands_url

        headers = {
            self.header_name: self.genesys_key,  # value not logged
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Connection": "close",  # stateless: close TCP after response
        }

        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts + 1):
            start = time.perf_counter()
            try:
                log.debug(
                    "ps.brands GET start attempt=%d url=%s",
                    attempt + 1,
                    url,
                )

                resp = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify,
                )
                dur_ms = (time.perf_counter() - start) * 1000.0

                sc = resp.status_code
                ctype = resp.headers.get("Content-Type")
                clen = _len_bytes(resp.content)

                log.info(
                    "ps.brands GET done status=%s dur=%.1fms ctype=%s len=%d attempt=%d",
                    sc,
                    dur_ms,
                    ctype,
                    clen,
                    attempt + 1,
                )

                if 200 <= sc < 300:
                    # parse json rigidamente
                    try:
                        data = resp.json() if resp.content else []
                    except Exception as parse_err:
                        log.warning(
                            "ps.categories json_parse_error dur=%.1fms len=%d attempt=%d",
                            dur_ms,
                            clen,
                            attempt + 1,
                        )
                        raise RuntimeError("upstream_invalid_json") from parse_err

                    # Validar estrutura esperada
                    if not isinstance(data, dict):
                        log.warning(
                            "ps.categories invalid_payload_type type=%s",
                            type(data).__name__,
                        )
                        raise RuntimeError("invalid_categories_payload")

                    # Devolve o envelope completo para validação pelo schema
                    return data

                if sc in (401, 403):
                    log.warning(
                        "ps.brands unauthorized status=%s dur=%.1fms attempt=%d",
                        sc,
                        dur_ms,
                        attempt + 1,
                    )
                    raise RuntimeError(f"auth_failed:{sc}")

                if 500 <= sc < 600:
                    log.warning(
                        "ps.brands upstream_5xx status=%s dur=%.1fms attempt=%d will_retry=%s",
                        sc,
                        dur_ms,
                        attempt + 1,
                        attempt < self.retry_attempts,
                    )
                    raise RuntimeError(f"upstream_5xx:{sc}")

                log.warning(
                    "ps.brands upstream_http status=%s dur=%.1fms attempt=%d",
                    sc,
                    dur_ms,
                    attempt + 1,
                )
                raise RuntimeError(f"upstream_http:{sc}")

            except (ConnectTimeout, ReadTimeout, Timeout, ConnErr) as e:
                last_exc = e
                dur_ms = (time.perf_counter() - start) * 1000.0
                will_retry = attempt < self.retry_attempts
                log.warning(
                    "ps.brands network_error=%s dur=%.1fms attempt=%d will_retry=%s",
                    e.__class__.__name__,
                    dur_ms,
                    attempt + 1,
                    will_retry,
                )
                if will_retry:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise RuntimeError("upstream_timeout") from e

            except RuntimeError as e:
                last_exc = e
                if str(e).startswith("upstream_5xx:") and attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise

        raise last_exc or RuntimeError("upstream_unknown")

    def create_product(self, product_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a product in PrestaShop via r_genesys module.

        Expected product_data fields:
        - name: str
        - description: str | None
        - id_category: int (PS category ID)
        - price: str (e.g., "29.99")
        - gtin: str | None
        - partnumber: str | None
        - image_url: str | None
        - weight: str | None
        - id_brand: int | None (PS brand ID)
        """
        if not self.products_url:
            raise ValueError("PS_PRODUCTS_URL not configured")

        url = self.products_url
        headers = {
            self.header_name: self.genesys_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }

        log.info(
            "ps.create_product POST url=%s name=%s",
            url,
            product_data.get("name", "?")[:50],
        )

        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts + 1):
            t0 = time.perf_counter()
            try:
                resp = requests.post(
                    url,
                    json=product_data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify,
                )
                dur_ms = (time.perf_counter() - t0) * 1000
                sc = resp.status_code
                ctype = resp.headers.get("Content-Type", "")
                clen = _len_bytes(resp.content)

                log.info(
                    "ps.create_product POST done status=%s dur=%.1fms ctype=%s len=%d attempt=%d",
                    sc,
                    dur_ms,
                    ctype,
                    clen,
                    attempt + 1,
                )

                if 200 <= sc < 300:
                    try:
                        data = resp.json() if resp.content else {}
                    except Exception as parse_err:
                        log.warning(
                            "ps.create_product json_parse_error dur=%.1fms len=%d attempt=%d",
                            dur_ms,
                            clen,
                            attempt + 1,
                        )
                        raise RuntimeError("upstream_invalid_json") from parse_err

                    product_id = data.get("id_product") or data.get("id") or data.get("product_id")
                    if not product_id:
                        log.warning(
                            "ps.create_product missing_id dur=%.1fms attempt=%d",
                            dur_ms,
                            attempt + 1,
                        )
                        raise RuntimeError("create_product_failed:missing_id")

                    return {
                        "id_product": product_id,
                        "success": True,
                        **data,
                    }

                if sc in (400, 422):
                    # Validation error - don't retry
                    try:
                        err_data = resp.json()
                    except Exception:
                        err_data = {"error": resp.text[:500]}
                    log.warning(
                        "ps.create_product validation_error status=%s dur=%.1fms data=%s",
                        sc,
                        dur_ms,
                        err_data,
                    )
                    raise RuntimeError(f"validation_error:{err_data.get('error', 'unknown')}")

                if sc in (401, 403):
                    log.warning(
                        "ps.create_product unauthorized status=%s dur=%.1fms attempt=%d",
                        sc,
                        dur_ms,
                        attempt + 1,
                    )
                    raise RuntimeError("unauthorized")

                if 500 <= sc < 600:
                    log.warning(
                        "ps.create_product 5xx status=%s dur=%.1fms attempt=%d",
                        sc,
                        dur_ms,
                        attempt + 1,
                    )
                    last_exc = RuntimeError(f"upstream_5xx:{sc}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_backoff * (2**attempt))
                        continue
                    raise last_exc

                # Other status codes
                log.warning(
                    "ps.create_product unexpected_status=%s dur=%.1fms attempt=%d",
                    sc,
                    dur_ms,
                    attempt + 1,
                )
                raise RuntimeError(f"upstream_unexpected:{sc}")

            except (ConnectTimeout, ReadTimeout, Timeout) as e:
                dur_ms = (time.perf_counter() - t0) * 1000
                log.warning(
                    "ps.create_product timeout dur=%.1fms attempt=%d err=%s",
                    dur_ms,
                    attempt + 1,
                    type(e).__name__,
                )
                last_exc = e
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise RuntimeError("upstream_timeout") from e

            except ConnErr as e:
                dur_ms = (time.perf_counter() - t0) * 1000
                log.warning(
                    "ps.create_product conn_error dur=%.1fms attempt=%d err=%s",
                    dur_ms,
                    attempt + 1,
                    str(e)[:100],
                )
                last_exc = e
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise RuntimeError("upstream_connection_error") from e

            except RuntimeError as e:
                last_exc = e
                if str(e).startswith("upstream_5xx:") and attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise

        raise last_exc or RuntimeError("upstream_unknown")
