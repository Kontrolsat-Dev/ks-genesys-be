# app/infra/bootstrap.py
import logging
from sqlalchemy import text

log = logging.getLogger("gsm.bootstrap")


def ensure_brand_category_ci(engine):
    """
    Garante índices case-insensitive.
    - Cria SEMPRE índices normais (não-unique) para performance.
    - Só cria UNIQUE se não houver duplicados; caso haja, loga e segue.
    - Usa AUTOCOMMIT para não deixar a transaction abortada.
    """
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # índices normais (seguros)
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_brands_name_ci ON brands (lower(btrim(name)));"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_categories_name_ci ON categories (lower(btrim(name)));"
        )

        # helper para verificar duplicados
        def has_dupes(table: str) -> bool:
            sql = f"""
                SELECT 1
                FROM {table}
                GROUP BY lower(btrim(name))
                HAVING COUNT(*) > 1
                LIMIT 1
            """
            return conn.execute(text(sql)).first() is not None

        # tentar UNIQUE só se não houver duplicados
        if not has_dupes("brands"):
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_brands_name_ci ON brands (lower(btrim(name)));"
            )
        else:
            log.warning("UNIQUE brands SKIPPED: duplicates exist (clean first).")

        if not has_dupes("categories"):
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_name_ci ON categories (lower(btrim(name)));"
            )
        else:
            log.warning("UNIQUE categories SKIPPED: duplicates exist (clean first).")


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
