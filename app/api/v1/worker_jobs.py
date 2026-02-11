# app/api/v1/worker_jobs.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from typing import Any
from app.core.deps import get_uow, require_access_token
from app.infra.uow import UoW
from app.schemas.worker_jobs import WorkerJobListOut
from app.domains.worker.usecases.query.list_worker_jobs import (
    execute as uc_list_worker_jobs,
)
from app.domains.worker.usecases.command.schedule_supplier_ingest_jobs import (
    execute as uc_schedule_supplier_ingest_jobs,
)

router = APIRouter(
    prefix="/worker/jobs",
    tags=["worker-jobs"],
    dependencies=[Depends(require_access_token)],
)

UowDep = Annotated[UoW, Depends(get_uow)]


@router.get(
    "",
    response_model=WorkerJobListOut,
    summary="Listar jobs do worker",
)
def list_worker_jobs(
    uow: UowDep,
    job_kind: str | None = Query(
        default=None,
        description="Filtrar por tipo de job (ex: supplier_ingest)",
    ),
    status: str | None = Query(
        default=None,
        description="Filtrar por status (pending, running, done, failed)",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> WorkerJobListOut:
    """
    Lista os jobs do worker com paginação e filtros opcionais.
    Permite monitorizar o estado das tarefas em background.
    """
    return uc_list_worker_jobs(
        uow,
        job_kind=job_kind,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/errors",
    response_model=WorkerJobListOut,
    summary="Listar jobs com erro",
)
def list_worker_jobs_errors(
    uow: UowDep,
    job_kind: str | None = Query(
        default=None,
        description="Filtrar por tipo de job (ex: supplier_ingest)",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> WorkerJobListOut:
    """
    Lista apenas os jobs que falharam permanentemente.
    Atalho conveniente para diagnosticar problemas em tarefas de background.
    """
    return uc_list_worker_jobs(
        uow,
        job_kind=job_kind,
        status="failed",
        page=page,
        page_size=page_size,
    )


@router.post(
    "/supplier-ingests/schedule",
    summary="Agendar jobs de ingest para fornecedores",
)
def schedule_supplier_ingests(uow: UowDep) -> dict[str, Any]:
    """
    Cria jobs de ingest para todos os fornecedores com ingest_enabled=True.
    Apenas cria jobs se não existir já um job pending ou running para esse fornecedor.
    Útil para forçar re-agendamento manual em caso de problemas.
    """
    return uc_schedule_supplier_ingest_jobs(uow)
