# app/schemas/worker_jobs.py

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class WorkerJobOut(BaseModel):
    id_job: int
    job_kind: str
    job_key: str
    status: str
    priority: int
    attempts: int
    last_error: str | None = None

    not_before: datetime | None = None
    locked_by: str | None = None
    locked_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkerJobListOut(BaseModel):
    items: list[WorkerJobOut]
    total: int
    page: int
    page_size: int
