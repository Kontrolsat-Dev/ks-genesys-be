# apps/worker_main.py

from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import datetime, timedelta, UTC

from app.background.job_handlers import (
    JOB_KIND_SUPPLIER_INGEST,
    dispatch_job,
)
from app.core.logging import setup_logging
from app.domains.worker.usecases.schedule_supplier_ingest_jobs import (
    schedule_supplier_ingest_jobs,
)
from app.infra.session import SessionLocal
from app.infra.uow import UoW
from app.models.supplier import Supplier
from app.repositories.worker.read.worker_activity_read_repo import (
    WorkerActivityReadRepository,
)
from app.repositories.worker.write.worker_activity_write_repo import (
    WorkerActivityWriteRepository,
)
from app.repositories.worker.write.worker_job_write_repo import (
    WorkerJobWriteRepository,
)

logger = logging.getLogger("gsm.worker")


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def run_worker_loop() -> None:
    setup_logging()

    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    logger.info("Starting worker process %s", worker_id)

    handled_kinds = [JOB_KIND_SUPPLIER_INGEST]

    while True:
        now = _utcnow()
        poll_intervals: list[int] = []

        with SessionLocal() as db:
            uow = UoW(db)

            # 1) Garantir configs mínimas por job_kind
            act_w = WorkerActivityWriteRepository(db)
            for kind in handled_kinds:
                act_w.get_or_create_default(kind, default_max_concurrency=1)

            act_r = WorkerActivityReadRepository(db)
            configs = {cfg.job_kind: cfg for cfg in act_r.list_enabled()}

            poll_intervals = [cfg.poll_interval_seconds for cfg in configs.values()]

            job_w = WorkerJobWriteRepository(db)

            # 2) Watchdog: marcar jobs 'running' demasiado tempo como failed/pending
            total_stale = 0
            for job_kind, cfg in configs.items():
                if job_kind not in handled_kinds:
                    continue

                stale_after_seconds = getattr(cfg, "stale_after_seconds", None) or 600
                backoff_seconds = cfg.backoff_seconds
                max_attempts = cfg.max_attempts

                stale_count = job_w.mark_stale_running_jobs_as_failed(
                    job_kind=job_kind,
                    now=now,
                    stale_after=timedelta(seconds=stale_after_seconds),
                    max_attempts=max_attempts,
                    backoff_seconds=backoff_seconds,
                )

                if stale_count:
                    total_stale += stale_count
                    logger.warning(
                        "Marked %d stale job(s) as failed for kind=%s (watchdog)",
                        stale_count,
                        job_kind,
                    )

            if total_stale:
                # Persistir alterações de status/attempts/not_before
                uow.commit()

            # 3) Scheduler: garantir jobs para suppliers (supplier_ingest)
            if JOB_KIND_SUPPLIER_INGEST in configs:
                created = schedule_supplier_ingest_jobs(uow, now=now)
                if created:
                    logger.info("Scheduled %d supplier_ingest jobs", created)
                uow.commit()

            # 4) Executar jobs para cada kind
            for job_kind, cfg in configs.items():
                if job_kind not in handled_kinds:
                    continue

                max_batch = max(cfg.max_concurrency, 1)

                jobs = job_w.claim_pending_jobs(
                    job_kind=job_kind,
                    now=now,
                    limit=max_batch,
                    worker_id=worker_id,
                )

                if not jobs:
                    continue

                logger.info(
                    "Claimed %d job(s) of kind=%s for processing",
                    len(jobs),
                    job_kind,
                )

                for job in jobs:
                    try:
                        await dispatch_job(job.job_kind, job.payload_json or "{}", uow)

                        finished_at = _utcnow()
                        job_w.mark_done(job.id_job, finished_at=finished_at)

                        if job.job_kind == JOB_KIND_SUPPLIER_INGEST:
                            _schedule_next_for_supplier_after_run(
                                uow,
                                job,
                                finished_at,
                            )

                        logger.info(
                            "Job id=%s kind=%s concluído com sucesso",
                            job.id_job,
                            job.job_kind,
                        )
                        uow.commit()

                    except Exception as err:
                        finished_at = _utcnow()
                        err_msg = str(err)
                        logger.exception(
                            "Erro ao processar job id=%s kind=%s: %s",
                            job.id_job,
                            job.job_kind,
                            err_msg,
                        )

                        job_w.mark_failed(
                            job.id_job,
                            finished_at=finished_at,
                            error_message=err_msg,
                            max_attempts=cfg.max_attempts,
                            backoff_seconds=cfg.backoff_seconds,
                        )
                        uow.commit()

        # 5) Sleep até próximo ciclo
        sleep_secs = min(poll_intervals) if poll_intervals else 5
        await asyncio.sleep(sleep_secs)


def _schedule_next_for_supplier_after_run(
    uow: UoW,
    job,
    finished_at: datetime,
) -> None:
    """
    Depois de uma ingest, agenda a próxima run para este supplier com base no intervalo atual.
    """
    import json

    from app.repositories.worker.write.worker_job_write_repo import (
        WorkerJobWriteRepository,
    )
    from app.background.job_handlers import JOB_KIND_SUPPLIER_INGEST

    payload = json.loads(job.payload_json or "{}")
    id_supplier = payload.get("id_supplier")
    if not id_supplier:
        return

    db = uow.db  # type: ignore[attr-defined]

    supplier = db.get(Supplier, id_supplier)
    if not supplier:
        logger.warning(
            "Supplier %s not found when scheduling next ingest job",
            id_supplier,
        )
        return

    interval = supplier.ingest_interval_minutes or 60
    next_time = finished_at + timedelta(minutes=interval)

    job_key = f"{JOB_KIND_SUPPLIER_INGEST}:{id_supplier}"
    job_w = WorkerJobWriteRepository(db)
    job_w.enqueue_job(
        job_kind=JOB_KIND_SUPPLIER_INGEST,
        job_key=job_key,
        payload={"id_supplier": id_supplier},
        not_before=next_time,
    )

    # visibilidade apenas
    supplier.ingest_next_run_at = next_time
    db.flush()


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
