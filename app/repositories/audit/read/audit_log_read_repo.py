# app/repositories/audit/read/audit_log_read_repo.py
"""
Repositório de leitura para audit logs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogReadRepo:
    def __init__(self, db: Session):
        self.db = db

    def list_logs(
        self,
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
        Lista audit logs com filtros e paginação.
        Retorna (items, total_count).
        """
        stmt = select(AuditLog)

        if event_type:
            stmt = stmt.where(AuditLog.event_type == event_type)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if from_date:
            stmt = stmt.where(AuditLog.created_at >= from_date)
        if to_date:
            stmt = stmt.where(AuditLog.created_at <= to_date)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        # Paginate (mais recentes primeiro)
        stmt = stmt.order_by(desc(AuditLog.created_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.scalars(stmt).all())
        return items, total

    def get_by_id(self, log_id: int) -> AuditLog | None:
        """
        Obtém um audit log pelo ID.
        """
        return self.db.get(AuditLog, log_id)

    def get_event_types(self) -> list[str]:
        """
        Retorna lista de event_types distintos para filtros.
        """
        stmt = select(AuditLog.event_type).distinct().order_by(AuditLog.event_type)
        return list(self.db.scalars(stmt).all())
