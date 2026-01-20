# app/external/sage_client.py
# Operações para SAGE

from __future__ import annotations
import logging
import time
from typing import Any, Literal

import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, Timeout, ConnectionError as ConnErr

from app.core.config import settings

log = logging.getLogger(__name__)


def _len_bytes(b: bytes | None) -> int:
    return len(b or b"")


class SageClient:
    def __init__(self):
        # Creds
        self.access_client: str | None = settings.SAGE_ACCESS_CLIENT
        self.access_secret: str | None = settings.SAGE_ACCESS_CLIENT
        self.user_agent: str | None = settings.SAGE_USER_AGENT

        self.sage_base_url: str | None = settings.SAGE_BASE_URL

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

    def get_suppliers(self):
        """Obter lista de fornecedores"""
        ...

    def post_ne(self):
        """Criar nota de encomenda"""
        ...
