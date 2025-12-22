# app/external/prestashop_client.py
from __future__ import annotations
import logging
import time
from typing import Any, Literal

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
    Stateless HTTP client for Prestashop via r_genesys module.
    - No credential hardcoding.
    - Automatic retry with exponential backoff for transient errors.
    - Safe logging (never logs password or secret keys).
    """

    def __init__(self) -> None:
        self.validate_url: str | None = getattr(settings, "PS_AUTH_VALIDATE_URL", None)
        self.categories_url: str | None = getattr(settings, "PS_CATEGORIES_URL", None)
        self.brands_url: str | None = getattr(settings, "PS_BRANDS_URL", None)
        self.products_url: str | None = getattr(settings, "PS_IMPORT_PRODUCT", None)
        self.header_name: str | None = getattr(settings, "PS_AUTH_VALIDATE_HEADER", None)
        self.genesys_key: str | None = getattr(settings, "PS_GENESYS_KEY", None)

        if not self.validate_url or not self.header_name or not self.genesys_key:
            raise ValueError(
                "Prestashop auth configuration is missing: "
                "PS_AUTH_VALIDATE_URL / PS_AUTH_VALIDATE_HEADER / PS_GENESYS_KEY"
            )

        self.timeout: tuple[float, float] = (
            float(getattr(settings, "PS_AUTH_CONNECT_TIMEOUT_S", 5)),
            float(getattr(settings, "PS_AUTH_READ_TIMEOUT_S", 10)),
        )
        verify_env = str(
            getattr(settings, "PS_AUTH_VERIFY_SSL", getattr(settings, "PS_VERIFY_SSL", "true"))
        ).lower()
        self.verify = certifi.where() if verify_env != "false" else False
        self.user_agent = getattr(settings, "PS_USER_AGENT", "genesys/2.0")

        self.retry_attempts = int(getattr(settings, "PS_AUTH_RETRY_ATTEMPTS", 2))
        self.retry_backoff = float(getattr(settings, "PS_AUTH_RETRY_BACKOFF_S", 0.4))

    def _get_headers(self, content_type: str | None = None) -> dict[str, str]:
        """Build standard headers for PS requests."""
        headers = {
            self.header_name: self.genesys_key,
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Connection": "close",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request(
        self,
        method: Literal["GET", "POST"],
        url: str,
        *,
        operation: str,
        json_payload: dict[str, Any] | None = None,
        allow_empty_response: bool = False,
    ) -> dict[str, Any]:
        """
        Execute HTTP request with retry, logging and error handling.

        Args:
            method: HTTP method (GET or POST)
            url: Target URL
            operation: Name for logging (e.g., "ps.categories")
            json_payload: Optional JSON body for POST requests
            allow_empty_response: If True, return {} for empty responses

        Returns:
            Parsed JSON response as dict

        Raises:
            RuntimeError: On auth failure, upstream errors, or network issues
        """
        headers = self._get_headers(content_type="application/json" if json_payload else None)

        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts + 1):
            start = time.perf_counter()
            try:
                log.debug(
                    "%s %s start attempt=%d url=%s",
                    operation,
                    method,
                    attempt + 1,
                    url,
                )

                if method == "GET":
                    resp = requests.get(
                        url, headers=headers, timeout=self.timeout, verify=self.verify
                    )
                else:
                    resp = requests.post(
                        url,
                        json=json_payload,
                        headers=headers,
                        timeout=self.timeout,
                        verify=self.verify,
                    )

                dur_ms = (time.perf_counter() - start) * 1000.0
                sc = resp.status_code
                ctype = resp.headers.get("Content-Type", "")
                clen = _len_bytes(resp.content)

                log.info(
                    "%s %s done status=%s dur=%.1fms ctype=%s len=%d attempt=%d",
                    operation,
                    method,
                    sc,
                    dur_ms,
                    ctype,
                    clen,
                    attempt + 1,
                )

                # Success (2xx)
                if 200 <= sc < 300:
                    if not resp.content:
                        return {} if allow_empty_response else {}
                    try:
                        return resp.json()
                    except Exception as parse_err:
                        log.warning(
                            "%s json_parse_error dur=%.1fms len=%d attempt=%d",
                            operation,
                            dur_ms,
                            clen,
                            attempt + 1,
                        )
                        raise RuntimeError("upstream_invalid_json") from parse_err

                # Auth errors - don't retry
                if sc in (401, 403):
                    log.warning(
                        "%s unauthorized status=%s dur=%.1fms attempt=%d",
                        operation,
                        sc,
                        dur_ms,
                        attempt + 1,
                    )
                    raise RuntimeError(f"auth_failed:{sc}")

                # Validation errors (400, 422) - don't retry
                if sc in (400, 422):
                    try:
                        err_data = resp.json()
                    except Exception:
                        err_data = {"error": resp.text[:500]}
                    log.warning(
                        "%s validation_error status=%s dur=%.1fms data=%s",
                        operation,
                        sc,
                        dur_ms,
                        err_data,
                    )
                    raise RuntimeError(f"validation_error:{err_data.get('error', 'unknown')}")

                # Server errors (5xx) - retry
                if 500 <= sc < 600:
                    log.warning(
                        "%s upstream_5xx status=%s dur=%.1fms attempt=%d will_retry=%s",
                        operation,
                        sc,
                        dur_ms,
                        attempt + 1,
                        attempt < self.retry_attempts,
                    )
                    last_exc = RuntimeError(f"upstream_5xx:{sc}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_backoff * (2**attempt))
                        continue
                    raise last_exc

                # Other status codes
                log.warning(
                    "%s upstream_http status=%s dur=%.1fms attempt=%d",
                    operation,
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
                    "%s network_error=%s dur=%.1fms attempt=%d will_retry=%s",
                    operation,
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
                # Only retry on 5xx marker
                if str(e).startswith("upstream_5xx:") and attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff * (2**attempt))
                    continue
                raise

        raise last_exc or RuntimeError("upstream_unknown")

    # ========== Public Methods ==========

    def login(self, email: str, password: str) -> dict[str, Any]:
        """
        Authenticate user via PrestaShop.
        Returns user info dict with id, email, name, role.
        """
        if not email or not password:
            raise ValueError("email and password are required")

        log.debug("ps.auth login email=%s", _mask_email(email))

        data = self._request(
            "POST",
            self.validate_url,
            operation="ps.auth",
            json_payload={"email": email, "password": password},
        )

        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        uid = user.get("id") or data.get("id") or data.get("user_id")
        if not uid:
            log.warning("ps.auth missing_user in response")
            raise RuntimeError("auth_failed:missing_user")

        return {
            "id": uid,
            "email": user.get("email") or data.get("email") or email,
            "name": user.get("name") or data.get("name") or "Guest",
            "role": user.get("role") or data.get("role") or "user",
        }

    def get_categories(self) -> dict[str, Any]:
        """
        Get PrestaShop categories tree via r_genesys module.
        Returns envelope with root_category_id, language_id, shop_id, categories.
        """
        data = self._request(
            "GET",
            self.categories_url,
            operation="ps.categories",
        )

        if not isinstance(data, dict):
            log.warning("ps.categories invalid_payload_type type=%s", type(data).__name__)
            raise RuntimeError("invalid_categories_payload")

        return data

    def get_brands(self) -> dict[str, Any]:
        """
        Get PrestaShop brands list via r_genesys module.
        Returns envelope with language_id and brands array.
        """
        data = self._request(
            "GET",
            self.brands_url,
            operation="ps.brands",
        )

        if not isinstance(data, dict):
            log.warning("ps.brands invalid_payload_type type=%s", type(data).__name__)
            raise RuntimeError("invalid_brands_payload")

        return data

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
        - brand_name: str | None (brand name to create/match in PS)

        Returns dict with id_product and success status.
        """
        if not self.products_url:
            raise ValueError("PS_IMPORT_PRODUCT not configured")

        log.info(
            "ps.create_product name=%s",
            product_data.get("name", "?")[:50],
        )

        data = self._request(
            "POST",
            self.products_url,
            operation="ps.create_product",
            json_payload=product_data,
        )

        product_id = data.get("id_product") or data.get("id") or data.get("product_id")
        if not product_id:
            log.warning("ps.create_product missing_id in response")
            raise RuntimeError("create_product_failed:missing_id")

        return {
            "id_product": product_id,
            "success": True,
            **data,
        }
