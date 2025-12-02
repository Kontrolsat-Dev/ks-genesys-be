# app/domains/worker/usecases/list_worker_jobs.py
from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.worker.read.worker_job_read_repo import WorkerJobReadRepository
from app.schemas.worker_jobs import WorkerJobListOut, WorkerJobOut


def execute(
    uow: UoW,
    *,
    job_kind: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    db = uow.db
    repo = WorkerJobReadRepository(db)

    rows, total = repo.list_jobs(
        job_kind=job_kind,
        status=status,
        page=page,
        page_size=page_size,
    )

    items = [
        WorkerJobOut(
            id_job=j.id_job,
            job_kind=j.job_kind,
            job_key=j.job_key,
            status=j.status,
            priority=j.priority,
            attempts=j.attempts,
            last_error=j.last_error,
            not_before=j.not_before,
            locked_by=j.locked_by,
            locked_at=j.locked_at,
            started_at=j.started_at,
            finished_at=j.finished_at,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in rows
    ]

    return WorkerJobListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
