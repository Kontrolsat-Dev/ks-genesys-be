# app/domains/procurement/usecases/runs/list_runs.py
from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.procurement.read.feed_run_read_repo import FeedRunReadRepository
from app.schemas.runs import FeedRunListOut


def _map_run_to_out(run) -> dict:
    """Map FeedRun ORM to FeedRunOut schema dict."""
    return {
        "id": run.id,
        "id_feed": run.id_feed,
        "supplier_id": run.feed.id_supplier if run.feed else None,
        "supplier_name": run.feed.supplier.name if run.feed and run.feed.supplier else None,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "rows_total": run.rows_total,
        "rows_changed": run.rows_changed,
        "rows_failed": run.rows_failed,
        "rows_unseen": run.rows_unseen,
        "http_status": run.http_status,
        "duration_ms": run.duration_ms,
        "error_msg": run.error_msg,
    }


def execute(uow: UoW, page: int = 1, page_size: int = 50) -> FeedRunListOut:
    run_r = FeedRunReadRepository(uow.db)
    runs, total = run_r.list(page=page, page_size=page_size)

    items = [_map_run_to_out(run) for run in runs]

    return FeedRunListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
