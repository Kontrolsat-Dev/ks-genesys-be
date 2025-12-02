# app/domains/catalog/usecases/catalog_update_stream/ack_events.py
from __future__ import annotations

from typing import Any

from app.infra.uow import UoW
from app.repositories.catalog.write.catalog_update_stream_write_repo import (
    CatalogUpdateStreamWriteRepository,
)


def execute(
    uow: UoW,
    *,
    ids: list[int],
    status: str,
    error: str | None,
) -> dict[str, Any]:
    db = uow.db
    repo = CatalogUpdateStreamWriteRepository(db)
    updated = repo.ack_batch(ids=ids, status=status, error=error)
    uow.commit()
    return {"updated": updated}
