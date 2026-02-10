# app/domains/audit/usecases/list_logs.py
"""
UseCase para listar audit logs com filtros e paginação.
"""

from __future__ import annotations

import json
from datetime import datetime

from app.infra.uow import UoW
from app.repositories.audit.read.audit_log_read_repo import AuditLogReadRepository
from app.schemas.audit import AuditLogOut, AuditLogListOut


def execute(
    uow: UoW,
    *,
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor_id: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> AuditLogListOut:
    """
    Lista audit logs com filtros e paginação.

    Returns:
        AuditLogListResponse schema
    """
    repo = AuditLogReadRepository(uow.db)
    items, total = repo.list_logs(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )

    return AuditLogListOut(
        items=[_to_out(log) for log in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def _to_out(log) -> AuditLogOut:
    """Converte modelo AuditLog para schema AuditLogOut."""
    details = None
    if log.details_json:
        try:
            details = json.loads(log.details_json)
        except json.JSONDecodeError:
            details = {"raw": log.details_json}

    return AuditLogOut(
        id=log.id,
        event_type=log.event_type,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        actor_id=log.actor_id,
        actor_name=log.actor_name,
        description=log.description,
        details=details,
        created_at=log.created_at,
    )
