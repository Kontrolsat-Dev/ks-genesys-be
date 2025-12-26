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
from app.domains.audit.usecases import list_logs, get_log, get_event_types
from app.schemas.audit import AuditLogOut, AuditLogListResponse, EventTypesResponse

router = APIRouter(prefix="/audit", tags=["audit"])
UserDep = Annotated[dict, Depends(require_access_token)]
UowDep = Annotated[UoW, Depends(get_uow)]


@router.get("", response_model=AuditLogListResponse, summary="Listar audit logs")
def list_audit_logs(
    _user: UserDep,
    uow: UowDep,
    event_type: str | None = Query(None, description="Filtrar por tipo de evento"),
    entity_type: str | None = Query(None, description="Filtrar por tipo de entidade"),
    entity_id: int | None = Query(None, description="Filtrar por ID da entidade"),
    from_date: datetime | None = Query(None, description="Data início (ISO)"),
    to_date: datetime | None = Query(None, description="Data fim (ISO)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """
    Lista audit logs com filtros e paginação.
    """
    return list_logs.execute(
        uow,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get("/event-types", response_model=EventTypesResponse, summary="Listar tipos de evento")
def list_event_types(_user: UserDep, uow: UowDep):
    """
    Retorna lista de event_types distintos para filtros.
    """
    types = get_event_types.execute(uow)
    return EventTypesResponse(event_types=types)


@router.get("/{log_id}", response_model=AuditLogOut, summary="Obter audit log por ID")
def get_audit_log(_user: UserDep, uow: UowDep, log_id: int):
    """
    Obtém detalhes de um audit log.
    """
    return get_log.execute(uow, log_id)
