# app/models/worker_activity_config.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.base import Base, utcnow


class WorkerActivityConfig(Base):
    __tablename__ = "worker_activity_config"

    id_activity: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Kind de job a que esta config se aplica, ex.: "supplier_ingest"
    job_kind: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Número máximo de jobs deste tipo em paralelo POR PROCESSO (por agora vamos usar só como limite de batch)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Retries básicos
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    backoff_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # Com que frequência o worker deve ir à BD procurar jobs deste tipo
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

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

    def __repr__(self) -> str:
        return f"<WorkerActivityConfig kind={self.job_kind} enabled={self.enabled} max_conc={self.max_concurrency}>"
