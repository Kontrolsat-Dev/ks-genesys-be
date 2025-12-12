# app/api/v1/runs.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, BackgroundTasks

from app.core.deps import get_uow, require_access_token
from app.domains.procurement.usecases.runs.ingest_supplier import execute as uc_ingest
from app.domains.procurement.usecases.runs.list_runs import execute as uc_list_runs
from app.infra.session import SessionLocal
from app.infra.uow import UoW
from app.schemas.runs import FeedRunListOut

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(require_access_token)])

UowDep = Annotated[UoW, Depends(get_uow)]


@router.get("", response_model=FeedRunListOut)
def get_runs(
    uow: UowDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return uc_list_runs(uow, page=page, page_size=page_size)


@router.post("/supplier/{id_supplier}/ingest")
async def ingest_supplier(
    id_supplier: int,
    uow: UowDep,
    limit: int | None = Query(default=None, ge=1, le=1_000_000),
):
    return await uc_ingest(uow, id_supplier=id_supplier, limit=limit)


@router.post("/supplier/{id_supplier}/ingest/background")
async def ingest_supplier_background(
    id_supplier: int,
    background_tasks: BackgroundTasks,
    limit: int | None = Query(default=None, ge=1, le=1_000_000),
):
    async def _run_ingest(id_supp: int, lim: int | None):
        # Create fresh session/UoW for background execution
        with SessionLocal() as db:
            uow_bg = UoW(db)
            await uc_ingest(uow_bg, id_supplier=id_supp, limit=lim)

    background_tasks.add_task(_run_ingest, id_supplier, limit)
    return {"ok": True, "message": "Ingest script scheduled in background"}
