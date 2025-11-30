# app/models/worker_job.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.base import Base, utcnow


class WorkerJob(Base):
    __tablename__ = "worker_jobs"

    id_job: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Tipo de job, ex.: "supplier_ingest", "prestashop_import_category"
    job_kind: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    # Chave lógica opcional para dedupe, ex.: "supplier_ingest:7"
    job_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # "pending" | "running" | "done" | "failed" | "cancelled"
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="pending")

    # Menor = mais prioritário
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Não correr antes deste timestamp (pode ser NULL => imediatamente elegível)
    not_before: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Payload arbitrário em JSON (string)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # debug only
        return f"<WorkerJob id={self.id_job} kind={self.job_kind} status={self.status}>"
