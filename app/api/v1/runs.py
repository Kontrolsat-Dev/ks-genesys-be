# app/api/v1/runs.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_uow, require_access_token
from app.domains.procurement.usecases.runs.ingest_supplier import execute as uc_ingest
from app.infra.uow import UoW

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(require_access_token)])
UowDep = Annotated[UoW, Depends(get_uow)]


@router.post("/supplier/{id_supplier}/ingest")
async def ingest_supplier(
    id_supplier: int,
    uow: UowDep,
    limit: int | None = Query(default=None, ge=1, le=1_000_000),
):
    return await uc_ingest(uow, id_supplier=id_supplier, limit=limit)
