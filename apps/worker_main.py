# apps/worker_main.py

from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import UTC, datetime, timedelta

from app.background.job_handlers import (
    JOB_KIND_SUPPLIER_INGEST,
    JOB_KIND_PRODUCT_EOL_CHECK,
    JOB_KIND_PRODUCT_AUTO_IMPORT,
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

    # Job kinds handled by this worker
    handled_kinds = [
        JOB_KIND_SUPPLIER_INGEST,
        JOB_KIND_PRODUCT_EOL_CHECK,
        JOB_KIND_PRODUCT_AUTO_IMPORT,
    ]

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

                # Obter stale timeouts da configuração
                from app.domains.config.services.config_service import config_service

                if job_kind == JOB_KIND_SUPPLIER_INGEST:
                    default_stale = config_service.get_int(
                        "stale_job_timeout_supplier_ingest", default=3600
                    )
                else:
                    default_stale = config_service.get_int("stale_job_timeout_default", default=600)

                stale_after_seconds = getattr(cfg, "stale_after_seconds", None) or default_stale
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

            # 2b) Cleanup: marcar FeedRuns 'running' há muito tempo como error
            from app.repositories.procurement.write.feed_run_write_repo import (
                FeedRunWriteRepository,
            )

            run_w = FeedRunWriteRepository(db)
            stale_feed_timeout = config_service.get_int(
                "stale_feed_run_timeout_minutes", default=120
            )
            stale_runs = run_w.mark_stale_running_as_error(stale_after_minutes=stale_feed_timeout)
            if stale_runs:
                logger.warning(
                    "Marked %d stale FeedRun(s) as error (>2h running)",
                    stale_runs,
                )
                uow.commit()

            # 3) Scheduler: garantir jobs para suppliers (supplier_ingest)
            if JOB_KIND_SUPPLIER_INGEST in configs:
                created = schedule_supplier_ingest_jobs(uow, now=now)
                if created:
                    logger.info("Scheduled %d supplier_ingest jobs", created)
                uow.commit()

            # 3b) Scheduler: garantir job diário de EOL check
            if JOB_KIND_PRODUCT_EOL_CHECK in configs:
                eol_scheduled = _schedule_daily_eol_check(uow, now=now)
                if eol_scheduled:
                    logger.info("Scheduled daily product_eol_check job")
                uow.commit()

            # 3c) Scheduler: auto-import de produtos novos (cada 15 minutos)
            if JOB_KIND_PRODUCT_AUTO_IMPORT in configs:
                auto_import_scheduled = _schedule_auto_import_job(uow, now=now)
                if auto_import_scheduled:
                    logger.info("Scheduled product_auto_import job")
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

                # Processamento sequencial dentro deste worker
                for job in jobs:
                    try:
                        await dispatch_job(job.job_kind, job.payload_json or "{}", uow)

                        finished_at = _utcnow()
                        job_w.mark_done(job.id_job, finished_at=finished_at)

                        # Lógica específica para supplier_ingest:
                        # agendar próxima run + atualizar ingest_next_run_at
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
                        # commit por job -> transações pequenas
                        uow.commit()

                    except Exception as err:  # noqa: BLE001
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
    import json

    from app.background.job_handlers import JOB_KIND_SUPPLIER_INGEST
    from app.repositories.worker.write.worker_job_write_repo import (
        WorkerJobWriteRepository,
    )

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

    # ⚠️ se o supplier foi desativado para ingest, não encadear novo job
    if not supplier.ingest_enabled:
        supplier.ingest_next_run_at = None  # “não há próxima run agendada”
        db.flush()
        logger.info(
            "Supplier %s com ingest_enabled=False – não agendo novo supplier_ingest",
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

    supplier.ingest_next_run_at = next_time
    db.flush()


def _schedule_daily_eol_check(uow: UoW, *, now: datetime) -> bool:
    """
    Agenda um job de EOL check para correr 1x por dia (às 03:00 UTC).
    Se já passou das 03:00 e não há job para hoje, agenda para execução imediata.
    Retorna True se um novo job foi criado.
    """
    from app.repositories.worker.write.worker_job_write_repo import (
        WorkerJobWriteRepository,
    )

    db = uow.db
    job_w = WorkerJobWriteRepository(db)

    job_key = "product_eol_check:daily"

    # Verificar se já existe um job pendente ou running
    existing = job_w.get_pending_or_running_by_key(job_key)
    if existing:
        return False

    # Verificar se já correu hoje (done)
    today_ran = job_w.has_done_today(job_key, today=now.date())
    if today_ran:
        return False

    # Se já passou das 03:00 UTC e não correu hoje, agendar para AGORA
    # Caso contrário, agendar para as 03:00 de hoje
    if now.hour >= 3:
        next_run = now  # Executar imediatamente
    else:
        next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)

    job_w.enqueue_job(
        job_kind=JOB_KIND_PRODUCT_EOL_CHECK,
        job_key=job_key,
        payload={},
        not_before=next_run,
    )

    return True


def _schedule_auto_import_job(uow: UoW, *, now: datetime) -> bool:
    """
    Agenda um job de auto-import para correr a cada 4 horas.
    Apenas cria novo job se não existir um pendente/running e não tiver corrido
    nas últimas 4 horas.
    Retorna True se um novo job foi criado.
    """
    from app.background.job_handlers import JOB_KIND_PRODUCT_AUTO_IMPORT
    from app.repositories.worker.write.worker_job_write_repo import (
        WorkerJobWriteRepository,
    )

    db = uow.db
    job_w = WorkerJobWriteRepository(db)

    job_key = "product_auto_import:periodic"

    from app.domains.config.services.config_service import config_service

    interval_hours = config_service.get_int("auto_import_interval_hours", default=4)

    # Verificar se já existe um job pendente ou running
    existing = job_w.get_pending_or_running_by_key(job_key)
    if existing:
        return False

    # Verificar se já correu nas últimas 4 horas
    last_done = job_w.get_last_done_by_key(job_key)
    if last_done and last_done.finished_at:
        next_run_at = last_done.finished_at + timedelta(hours=interval_hours)
        if now < next_run_at:
            # Ainda não passou tempo suficiente, não agendar
            return False

    # Agendar para execução imediata
    job_w.enqueue_job(
        job_kind=JOB_KIND_PRODUCT_AUTO_IMPORT,
        job_key=job_key,
        payload={"limit": 100},  # Processar até 100 produtos por execução
        not_before=now,
    )

    return True


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
