# app/domains/worker/services/job_handlers.py
from __future__ import annotations

import json
from typing import Any
from collections.abc import Awaitable, Callable

from app.infra.uow import UoW
from app.domains.procurement.usecases.runs.ingest_supplier import (
    execute as uc_ingest_supplier,
)

JOB_KIND_SUPPLIER_INGEST = "supplier_ingest"

JobHandler = Callable[[UoW, dict[str, Any]], Awaitable[None]]


async def handle_supplier_ingest(uow: UoW, payload: dict[str, Any]) -> None:
    id_supplier = payload.get("id_supplier")
    if not id_supplier:
        raise ValueError("supplier_ingest job without id_supplier")

    await uc_ingest_supplier(uow, id_supplier=id_supplier, limit=None)


JOB_HANDLERS: dict[str, JobHandler] = {
    JOB_KIND_SUPPLIER_INGEST: handle_supplier_ingest,
}


async def dispatch_job(kind: str, payload_json: str, uow: UoW) -> None:
    handler = JOB_HANDLERS.get(kind)
    if not handler:
        raise ValueError(f"No job handler registered for kind={kind}")
    payload = json.loads(payload_json or "{}")
    await handler(uow, payload)
