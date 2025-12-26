# app/domains/audit/usecases/get_log.py
from __future__ import annotations

from app.models.audit_log import AuditLog
from app.infra.uow import UoW
from app.repositories.audit.read.audit_log_read_repo import AuditLogReadRepo


def execute(uow: UoW, log_id: int) -> AuditLog | None:
    """
    Obtém um audit log por ID.
    """
    repo = AuditLogReadRepo(uow.db)
    return repo.get_by_id(log_id)
