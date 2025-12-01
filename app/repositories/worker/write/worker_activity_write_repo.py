# app/repositories/worker/write/worker_activity_write_repo.py

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.worker_activity_config import WorkerActivityConfig


class WorkerActivityWriteRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create_default(
        self,
        job_kind: str,
        *,
        default_max_concurrency: int = 1,
    ) -> WorkerActivityConfig:
        stmt = select(WorkerActivityConfig).where(
            WorkerActivityConfig.job_kind == job_kind,
        )
        cfg = self._db.execute(stmt).scalar_one_or_none()
        if cfg:
            return cfg

        cfg = WorkerActivityConfig(
            job_kind=job_kind,
            enabled=True,
            max_concurrency=default_max_concurrency,
        )
        self._db.add(cfg)
        self._db.flush()
        return cfg
