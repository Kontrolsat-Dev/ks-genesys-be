# app/api/v1/audit.py
"""
API endpoints para audit logs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_access_token, get_uow
from app.infra.uow import UoW
from app.domains.audit.usecases.query import (
    list_logs as uc_list_logs,
    get_log as uc_get_log,
    get_event_types as uc_get_event_types,
)

from app.schemas.audit import AuditLogOut, AuditLogListOut, EventTypesOut

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(require_access_token)],
)

UowDep = Annotated[UoW, Depends(get_uow)]


@router.get("", response_model=AuditLogListOut, summary="Listar audit logs")
def list_audit_logs(
    uow: UowDep,
    event_type: str | None = Query(None, description="Filtrar por tipo de evento"),
    entity_type: str | None = Query(None, description="Filtrar por tipo de entidade"),
    entity_id: int | None = Query(None, description="Filtrar por ID da entidade"),
    from_date: datetime | None = Query(None, description="Data início (ISO)"),
    to_date: datetime | None = Query(None, description="Data fim (ISO)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> AuditLogListOut:
    """
    Lista audit logs com filtros e paginação.
    """
    return uc_list_logs(
        uow,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get("/event-types", response_model=EventTypesOut, summary="Listar tipos de evento")
def list_event_types(uow: UowDep) -> EventTypesOut:
    """
    Retorna lista de event_types distintos para filtros.
    """
    types = uc_get_event_types.execute(uow)
    return EventTypesOut(event_types=types)


@router.get("/{log_id}", response_model=AuditLogOut, summary="Obter audit log por ID")
def get_audit_log(uow: UowDep, log_id: int) -> AuditLogOut:
    """
    Obtém detalhes de um audit log.
    """
    return uc_get_log.execute(uow, log_id)
