# app/models/audit_log.py
"""
Modelo para registar ações importantes do sistema (audit trail).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.base import Base, utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Tipo de evento: product_import, category_mapping, price_change, etc.
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Tipo de entidade afetada: product, category, config, etc.
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # ID da entidade afetada (se aplicável)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Quem executou a ação (ID do utilizador ou "system")
    actor_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Nome do utilizador para display
    actor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Descrição legível do que aconteceu
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Detalhes adicionais em JSON (dados antes/depois, IDs extras, etc.)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )

    __table_args__ = (
        # Índice composto para queries por tipo + data
        Index("ix_audit_logs_type_created", "event_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} type={self.event_type} entity={self.entity_type}:{self.entity_id}>"
