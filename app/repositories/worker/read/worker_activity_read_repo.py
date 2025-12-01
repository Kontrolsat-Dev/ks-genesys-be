# app/repositories/worker/read/worker_activity_read_repo.py

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models.worker_activity_config import WorkerActivityConfig


class WorkerActivityReadRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_kind(self, job_kind: str) -> WorkerActivityConfig:
        stmt = select(WorkerActivityConfig).where(
            WorkerActivityConfig.job_kind == job_kind,
        )
        cfg = self._db.execute(stmt).scalar_one_or_none()
        if not cfg:
            raise NotFound(f"WorkerActivityConfig for kind={job_kind} not found")
        return cfg

    def list_all(self) -> list[WorkerActivityConfig]:
        stmt = select(WorkerActivityConfig).order_by(
            WorkerActivityConfig.job_kind.asc(),
        )
        return list(self._db.execute(stmt).scalars().all())

    def list_enabled(self) -> list[WorkerActivityConfig]:
        stmt = (
            select(WorkerActivityConfig)
            .where(WorkerActivityConfig.enabled.is_(True))
            .order_by(WorkerActivityConfig.job_kind.asc())
        )
        return list(self._db.execute(stmt).scalars().all())
