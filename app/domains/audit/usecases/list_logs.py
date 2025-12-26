# app/domains/audit/usecases/list_logs.py
from __future__ import annotations
from datetime import datetime

from app.models.audit_log import AuditLog
from app.infra.uow import UoW
from app.repositories.audit.read.audit_log_read_repo import AuditLogReadRepo


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
) -> tuple[list[AuditLog], int]:
    """
    Lista audit logs com filtros.
    """
    repo = AuditLogReadRepo(uow.db)
    return repo.list_logs(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
