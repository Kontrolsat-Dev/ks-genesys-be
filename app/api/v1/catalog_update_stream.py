# app/api/v1/catalog_update_stream.py
from __future__ import annotations


from fastapi import APIRouter, Depends, Query

from app.infra.uow import UoW
from app.core.deps import get_uow, require_access_token
from app.schemas.catalog_update_stream import (
    CatalogUpdateBatchOut,
    CatalogUpdateAckIn,
    CatalogUpdateStreamListOut,
)
from app.domains.catalog.usecases.catalog_update_stream import list_events as uc_list_events
from app.domains.catalog.usecases.catalog_update_stream.get_pending_events import (
    execute as uc_get_pending,
)
from app.domains.catalog.usecases.catalog_update_stream.ack_events import (
    execute as uc_ack_events,
)


router = APIRouter(
    prefix="/catalog/update-stream",
    tags=["catalog-update-stream"],
    dependencies=[Depends(require_access_token)],
)


@router.get(
    "/pending",
    response_model=CatalogUpdateBatchOut,
    summary="Obter batch de eventos pendentes",
)
def get_pending_events(
    limit: int = Query(50, ge=1, le=500),
    min_priority: int | None = Query(None, ge=1),
    uow: UoW = Depends(get_uow),
) -> CatalogUpdateBatchOut:
    """
    Obtém um batch de eventos pendentes para processamento.
    Os eventos retornados são marcados como 'processing' para evitar duplicação.
    Usar /ack para confirmar processamento com sucesso ou falha.
    """
    result = uc_get_pending(
        uow,
        limit=limit,
        min_priority=min_priority,
    )

    return CatalogUpdateBatchOut(
        items=result,
        total=len(result),
    )


@router.post(
    "/ack",
    summary="Confirmar processamento de eventos",
)
def ack_events(
    payload: CatalogUpdateAckIn,
    uow: UoW = Depends(get_uow),
) -> dict:
    """
    Confirma o processamento de um ou mais eventos.
    Status pode ser 'done' (sucesso) ou 'failed' (erro).
    Eventos falhados podem incluir mensagem de erro para diagnóstico.
    """
    return uc_ack_events(
        uow,
        ids=payload.ids,
        status=payload.status,
        error=payload.error,
    )


@router.get(
    "",
    response_model=CatalogUpdateStreamListOut,
    summary="Listar eventos do stream",
    dependencies=[Depends(require_access_token)],
)
def list_catalog_update_events(
    status: str | None = Query(
        default=None,
        description="Filtrar por status (pending, processing, done, failed)",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uow: UoW = Depends(get_uow),
):
    """
    Lista todos os eventos do catalog update stream com paginação.
    Permite filtrar por status para monitorizar o processamento.
    """
    return uc_list_events.execute(
        uow,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get(
    "/errors",
    response_model=CatalogUpdateStreamListOut,
    summary="Listar eventos com erro",
    dependencies=[Depends(require_access_token)],
)
def list_catalog_update_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uow: UoW = Depends(get_uow),
):
    """
    Lista apenas os eventos que falharam durante o processamento.
    Atalho conveniente para diagnosticar problemas de sincronização.
    """
    return uc_list_events.execute(
        uow,
        page=page,
        page_size=page_size,
        status="failed",
    )
