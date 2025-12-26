# app/domains/audit/usecases/get_event_types.py
from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.audit.read.audit_log_read_repo import AuditLogReadRepository


def execute(uow: UoW) -> list[str]:
    """
    Retorna lista de event_types.
    """
    repo = AuditLogReadRepository(uow.db)
    return repo.get_event_types()
