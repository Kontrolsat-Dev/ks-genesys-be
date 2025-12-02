# app/repositories/worker/read/worker_job_read_repo.py

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models.worker_job import WorkerJob


class WorkerJobReadRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, id_job: int) -> WorkerJob:
        job = self._db.get(WorkerJob, id_job)
        if not job:
            raise NotFound(f"Worker job {id_job} not found")
        return job

    def list_recent(
        self,
        *,
        job_kind: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[WorkerJob]:
        stmt = select(WorkerJob).order_by(WorkerJob.created_at.desc()).limit(limit)
        if job_kind:
            stmt = stmt.where(WorkerJob.job_kind == job_kind)
        if status:
            stmt = stmt.where(WorkerJob.status == status)
        return list(self._db.execute(stmt).scalars().all())

    def has_active_job_for_key(
        self,
        *,
        job_kind: str,
        job_key: str,
        active_statuses: Sequence[str] = ("pending", "running"),
    ) -> bool:
        stmt = (
            select(WorkerJob.id_job)
            .where(WorkerJob.job_kind == job_kind)
            .where(WorkerJob.job_key == job_key)
            .where(WorkerJob.status.in_(list(active_statuses)))
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none() is not None

    def list_jobs(
        self,
        *,
        job_kind: str,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[WorkerJob], int]:
        """
        Lista jobs com filtros por job_kind/status, ordenados por created_at desc,
        devolvendo (rows, total).
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 1

        base_stmt = select(WorkerJob)
        if job_kind:
            base_stmt = base_stmt.where(WorkerJob.job_kind == job_kind)
        if status:
            base_stmt = base_stmt.where(WorkerJob.status == status)

        base_stmt = base_stmt.order_by(WorkerJob.created_at.desc())
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = int(self._db.execute(count_stmt).scalar_one() or 0)

        rows = (
            self._db.execute(base_stmt.limit(page_size).offset((page - 1) * page_size))
            .scalars()
            .all()
        )
        return rows, total
