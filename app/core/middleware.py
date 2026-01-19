# app/core/middleware.py
"""
HTTP middleware para logging de requests e error handling.
"""

import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import AppError
from app.core.logging import set_request_id

log = logging.getLogger(__name__)

# Threshold for slow request warning (ms)
SLOW_REQUEST_MS = 2000


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
        set_request_id(rid)
        t0 = time.perf_counter()

        method = request.method
        path = request.url.path

        try:
            log.info("-> %s %s", method, path)

            try:
                response = await call_next(request)
            except AppError as e:
                dt = (time.perf_counter() - t0) * 1000
                payload = {"code": e.code, "detail": e.detail}
                response = JSONResponse(status_code=e.http_status, content=payload)
                response.headers["X-Request-ID"] = rid

                log.warning(
                    "<- %s %s -> %s [%s] %.0fms",
                    method,
                    path,
                    e.http_status,
                    e.code,
                    dt,
                )
                return response

            # Success logging
            dt = (time.perf_counter() - t0) * 1000
            response.headers["X-Request-ID"] = rid

            # Log level based on status and duration
            status = response.status_code
            if status >= 500:
                log.error("<- %s %s -> %s %.0fms", method, path, status, dt)
            elif status >= 400:
                log.warning("<- %s %s -> %s %.0fms", method, path, status, dt)
            elif dt > SLOW_REQUEST_MS:
                log.warning("<- %s %s -> %s %.0fms [SLOW]", method, path, status, dt)
            else:
                log.info("<- %s %s -> %s %.0fms", method, path, status, dt)

            return response

        finally:
            set_request_id(None)
