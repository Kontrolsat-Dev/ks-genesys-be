# app/repositories/audit/write/audit_log_write_repo.py
"""
Repositório de escrita para audit logs.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogWriteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        event_type: str,
        entity_type: str | None = None,
        entity_id: int | None = None,
        actor_id: str | None = None,
        actor_name: str | None = None,
        description: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Cria um novo registo de audit log.
        """
        log = AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=description,
            details_json=json.dumps(details) if details else None,
        )
        self.db.add(log)
        return log
