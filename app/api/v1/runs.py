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


@router.get(
    "",
    response_model=FeedRunListOut,
    summary="Listar execuções de ingest",
)
def get_runs(
    uow: UowDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """
    Lista o histórico de execuções de ingest de feeds.
    Inclui data, duração, estado e estatísticas de cada execução.
    """
    return uc_list_runs(uow, page=page, page_size=page_size)


@router.post(
    "/supplier/{id_supplier}/ingest",
    summary="Executar ingest de fornecedor (síncrono)",
)
async def ingest_supplier(
    id_supplier: int,
    uow: UowDep,
    limit: int | None = Query(default=None, ge=1, le=1_000_000),
):
    """
    Executa o processo de ingest de um fornecedor de forma síncrona.
    Faz download do feed, processa os dados e atualiza a base de dados.
    Bloqueia até conclusão - usar /background para execução assíncrona.
    """
    return await uc_ingest(uow, id_supplier=id_supplier, limit=limit)


@router.post(
    "/supplier/{id_supplier}/ingest/background",
    summary="Executar ingest de fornecedor (assíncrono)",
)
async def ingest_supplier_background(
    id_supplier: int,
    background_tasks: BackgroundTasks,
    limit: int | None = Query(default=None, ge=1, le=1_000_000),
):
    """
    Agenda o processo de ingest de um fornecedor para execução em background.
    Retorna imediatamente enquanto o processo corre em segundo plano.
    Verificar progresso através do endpoint /runs.
    """

    async def _run_ingest(id_supp: int, lim: int | None):
        # Create fresh session/UoW for background execution
        with SessionLocal() as db:
            uow_bg = UoW(db)
            await uc_ingest(uow_bg, id_supplier=id_supp, limit=lim)

    background_tasks.add_task(_run_ingest, id_supplier, limit)
    return {"ok": True, "message": "Ingest script scheduled in background"}
