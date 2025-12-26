# app/domains/audit/usecases/get_log.py
"""
UseCase para obter um audit log por ID.
"""

from __future__ import annotations

import json

from app.infra.uow import UoW
from app.core.errors import NotFound
from app.repositories.audit.read.audit_log_read_repo import AuditLogReadRepository
from app.schemas.audit import AuditLogOut


def execute(uow: UoW, log_id: int) -> AuditLogOut:
    """
    Obtém um audit log por ID.

    Returns:
        AuditLogOut schema

    Raises:
        NotFound: Se o log não existir
    """
    repo = AuditLogReadRepository(uow.db)
    log = repo.get_by_id(log_id)

    if not log:
        raise NotFound(f"Audit log {log_id} not found")

    # Converter details_json para dict
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
