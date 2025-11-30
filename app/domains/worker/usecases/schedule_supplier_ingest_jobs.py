# app/domains/worker/usecases/schedule_supplier_ingest_jobs.py
from __future__ import annotations

from datetime import datetime
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session


from app.infra.uow import UoW
from app.models.supplier import Supplier
from app.repositories.worker.read.worker_job_read_repo import WorkerJobReadRepository
from app.repositories.worker.write.worker_job_write_repo import WorkerJobWriteRepository
from app.background.job_handlers import JOB_KIND_SUPPLIER_INGEST


def _build_job_key_for_supplier(id_supplier: int) -> str:
    return f"{JOB_KIND_SUPPLIER_INGEST}:{id_supplier}"


def schedule_supplier_ingest_jobs(uow: UoW, *, now: datetime) -> int:
    """
    Garante que cada supplier com ingest_enabled tem pelo menos um job pending/running.

    NOTA: ingest_next_run_at aqui é apenas atualizado para refletir o próximo job agendado.
    """
    db: Session = uow.db  # type: ignore[attr-defined]

    job_r = WorkerJobReadRepository(db)
    job_w = WorkerJobWriteRepository(db)

    stmt = select(Supplier.id, Supplier.ingest_interval_minutes).where(Supplier.ingest_enabled)  # noqa: E712
    rows: Sequence[tuple[int, int | None]] = list(db.execute(stmt).all())

    created = 0
    for id_supplier, _ingest_interval in rows:
        job_key = _build_job_key_for_supplier(id_supplier)

        if job_r.has_active_job_for_key(
            job_kind=JOB_KIND_SUPPLIER_INGEST,
            job_key=job_key,
        ):
            continue

        # Sem job ativo => criar um agora (not_before = now)
        job_w.enqueue_job(
            job_kind=JOB_KIND_SUPPLIER_INGEST,
            job_key=job_key,
            payload={"id_supplier": id_supplier},
            not_before=now,
        )
        created += 1

        # Visibilidade: próxima run (neste momento é "agora", a lógica de +intervalo vem depois da execução)
        db.execute(
            Supplier.__table__.update()
            .where(Supplier.id == id_supplier)
            .values(ingest_next_run_at=now)
        )

    return created
