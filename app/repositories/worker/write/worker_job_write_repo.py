# app/repositories/worker/write/worker_job_write_repo.py

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models.worker_job import WorkerJob


class WorkerJobWriteRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def enqueue_job(
        self,
        *,
        job_kind: str,
        payload: dict[str, Any] | None = None,
        job_key: str | None = None,
        not_before: datetime | None = None,
        priority: int = 100,
    ) -> WorkerJob:
        job = WorkerJob(
            job_kind=job_kind,
            job_key=job_key,
            status="pending",
            priority=priority,
            not_before=not_before,
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
        self._db.add(job)
        # flush para ter id_job disponível já nesta transação
        self._db.flush()
        return job

    def claim_pending_jobs(
        self,
        *,
        job_kind: str,
        now: datetime,
        limit: int,
        worker_id: str,
    ) -> list[WorkerJob]:
        """
        Marca um grupo de jobs 'pending' como 'running' e devolve-os.

        NOTA: nesta primeira versão não estamos a usar SKIP LOCKED nem múltiplos processos,
        mas a assinatura já está preparada para isso.
        """

        if limit <= 0:
            return []

        stmt = (
            select(WorkerJob)
            .where(WorkerJob.job_kind == job_kind)
            .where(WorkerJob.status == "pending")
            .where(WorkerJob.not_before.is_(None) | (WorkerJob.not_before <= now))
            .order_by(WorkerJob.priority.asc(), WorkerJob.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=False)
        )
        jobs = list(self._db.execute(stmt).scalars().all())
        for job in jobs:
            job.status = "running"
            job.locked_by = worker_id
            job.locked_at = now
            job.started_at = now
        # flush é suficiente, commit fica à responsabilidade do UoW
        self._db.flush()
        return jobs

    def mark_done(self, id_job: int, *, finished_at: datetime) -> None:
        stmt = (
            update(WorkerJob)
            .where(WorkerJob.id_job == id_job)
            .values(
                status="done",
                finished_at=finished_at,
                updated_at=finished_at,
            )
        )
        res = self._db.execute(stmt)
        if res.rowcount == 0:
            raise NotFound(f"Worker job {id_job} not found")

    def mark_failed(
        self,
        id_job: int,
        *,
        finished_at: datetime,
        error_message: str,
        max_attempts: int,
        backoff_seconds: int,
    ) -> None:
        job = self._db.get(WorkerJob, id_job)
        if not job:
            raise NotFound(f"Worker job {id_job} not found")

        job.attempts += 1
        job.last_error = (error_message or "")[:2000]  # corta para não explodir
        job.finished_at = finished_at
        job.updated_at = finished_at

        if job.attempts >= max_attempts:
            job.status = "failed"
        else:
            # volta a pending com backoff
            job.status = "pending"
            job.not_before = finished_at.replace(microsecond=0) + timedelta(
                seconds=backoff_seconds,
            )
            job.started_at = None
            job.locked_at = None
            job.locked_by = None

        self._db.flush()

    def mark_stale_running_jobs_as_failed(
        self,
        *,
        job_kind: str,
        now: datetime,
        stale_after: timedelta,
        max_attempts: int,
        backoff_seconds: int,
    ) -> int:
        """
        Considera jobs 'running' há demasiado tempo como erro (stale) e aplica
        a mesma lógica de falha normal: incrementa attempts e, se ainda não
        bateu no max_attempts, volta a colocar em pending com backoff.
        """
        cutoff = now - stale_after

        stmt = (
            select(WorkerJob.id_job)
            .where(WorkerJob.job_kind == job_kind)
            .where(WorkerJob.status == "running")
            .where(WorkerJob.locked_at.is_not(None))
            .where(WorkerJob.locked_at < cutoff)
        )

        ids = [row[0] for row in self._db.execute(stmt).all()]

        for id_job in ids:
            self.mark_failed(
                id_job,
                finished_at=now,
                error_message="Stale running job watchdog: exceeded max runtime",
                max_attempts=max_attempts,
                backoff_seconds=backoff_seconds,
            )

        # mark_failed já faz flush
        return len(ids)

    def get_pending_or_running_by_key(self, job_key: str) -> WorkerJob | None:
        """
        Verifica se já existe um job pending ou running com a job_key dada.
        Usado para evitar criar jobs duplicados.
        """
        stmt = (
            select(WorkerJob)
            .where(WorkerJob.job_key == job_key)
            .where(WorkerJob.status.in_(["pending", "running"]))
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def has_done_today(self, job_key: str, *, today: datetime.date) -> bool:
        """
        Verifica se já existe um job done com a job_key dada que correu hoje.
        Usado para evitar correr o mesmo job várias vezes no mesmo dia.
        """
        from datetime import datetime, time

        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)

        stmt = (
            select(WorkerJob)
            .where(WorkerJob.job_key == job_key)
            .where(WorkerJob.status == "done")
            .where(WorkerJob.finished_at >= start_of_day)
            .where(WorkerJob.finished_at <= end_of_day)
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none() is not None
