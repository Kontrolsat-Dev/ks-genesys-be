# app/infra/bootstrap.py
import logging

log = logging.getLogger("gsm.bootstrap")


def ensure_recurring_jobs(session_factory) -> dict[str, int]:
    """
    Garante que jobs recorrentes existem:
    - supplier_ingest para cada supplier com ingest_enabled=True
    - product_eol_check diário

    Deve ser chamado no startup da API.
    Retorna contagem de jobs criados.
    """
    from app.infra.uow import UoW
    from app.infra.base import utcnow
    from app.domains.worker.usecases.schedule_supplier_ingest_jobs import (
        schedule_supplier_ingest_jobs,
    )
    from app.repositories.worker.write.worker_job_write_repo import (
        WorkerJobWriteRepository,
    )
    from app.background.job_handlers import JOB_KIND_PRODUCT_EOL_CHECK

    result = {"supplier_ingest": 0, "product_eol_check": 0}

    with session_factory() as db:
        uow = UoW(db)
        now = utcnow()

        # 1) Suppliers órfãos (ingest_enabled=True sem job pending/running)
        created = schedule_supplier_ingest_jobs(uow, now=now)
        result["supplier_ingest"] = created
        if created:
            log.info("Bootstrap: created %d supplier_ingest jobs", created)

        # 2) EOL check diário
        job_w = WorkerJobWriteRepository(db)
        job_key = "product_eol_check:daily"

        existing = job_w.get_pending_or_running_by_key(job_key)
        if not existing:
            today_ran = job_w.has_done_today(job_key, today=now.date())
            if not today_ran:
                # Agendar para execução imediata se já passou das 03:00, senão às 03:00
                if now.hour >= 3:
                    next_run = now
                else:
                    next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)

                job_w.enqueue_job(
                    job_kind=JOB_KIND_PRODUCT_EOL_CHECK,
                    job_key=job_key,
                    payload={},
                    not_before=next_run,
                )
                result["product_eol_check"] = 1
                log.info("Bootstrap: scheduled daily EOL check job")

        uow.commit()

    return result
