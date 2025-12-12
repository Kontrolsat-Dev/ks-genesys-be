# app/repositories/procurement/write/feed_run_write_repo.py
from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.infra.base import utcnow
from app.models.feed_run import FeedRun


class FeedRunWriteRepository:
    def __init__(self, db: Session):
        self.db = db

    # helper interno para evitar dependência cruzada do read repo
    def _get_required(self, id_run: int) -> FeedRun:
        run = self.db.get(FeedRun, id_run)
        if not run:
            raise NotFound("Run not found")
        return run

    def start(self, *, id_feed: int) -> FeedRun:
        """
        Cria uma nova FeedRun com status 'running' e faz flush imediato
        para garantir que o id existe na BD antes de inserir supplier_items.
        """
        run = FeedRun(id_feed=id_feed, status="running")
        self.db.add(run)
        # IMPORTANTE: flush aqui para garantir que o row em feed_runs existe
        self.db.flush()
        return run

    def finalize_ok(
        self,
        id_run: int,
        *,
        rows_total: int,
        rows_changed: int,
        rows_failed: int,
        rows_unseen: int,
        partial: bool,
    ) -> None:
        run = self._get_required(id_run)

        run.status = "partial" if partial else "ok"
        run.rows_total = rows_total
        run.rows_changed = rows_changed
        run.rows_failed = rows_failed
        run.rows_unseen = rows_unseen
        run.finished_at = utcnow()
        # Calculate duration
        if run.started_at and run.finished_at:
            delta = run.finished_at - run.started_at
            run.duration_ms = int(delta.total_seconds() * 1000)

        self.db.flush()

    def finalize_http_error(
        self,
        id_run: int,
        *,
        http_status: int,
        error_msg: str,
    ) -> None:
        run = self._get_required(id_run)
        run.status = "error"
        run.http_status = http_status
        run.error_msg = (error_msg or "")[:500]
        run.finished_at = utcnow()
        self.db.flush()

    def finalize_error(self, id_run: int, *, error_msg: str) -> None:
        run = self._get_required(id_run)
        run.status = "error"
        run.error_msg = (error_msg or "")[:500]
        run.finished_at = utcnow()
        self.db.flush()

    def mark_stale_running_as_error(self, *, stale_after_minutes: int = 120) -> int:
        """
        Marca FeedRuns que estão 'running' há mais de X minutos como 'error'.
        Usado como cleanup para runs que ficaram órfãs (worker crashou, etc).
        Retorna o número de runs marcadas como error.
        """
        cutoff = utcnow() - timedelta(minutes=stale_after_minutes)

        stmt = select(FeedRun).where(FeedRun.status == "running").where(FeedRun.started_at < cutoff)

        stale_runs = self.db.scalars(stmt).all()
        count = 0

        for run in stale_runs:
            run.status = "error"
            run.error_msg = f"Stale: running for more than {stale_after_minutes} minutes"
            run.finished_at = utcnow()
            count += 1

        if count:
            self.db.flush()

        return count
