# app/domains/catalog/usecases/catalog_update_stream/list_events.py
# Lista eventos da fila de atualização de catálogo

from __future__ import annotations

from app.infra.uow import UoW
from app.schemas.catalog_update_stream import (
    CatalogUpdateStreamItemOut,
    CatalogUpdateStreamListOut,
)
from app.core.errors import InvalidArgument

ALLOWED_STATUSES: tuple[str, ...] = ("pending", "processing", "done", "failed")


def execute(
    uow: UoW,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
) -> CatalogUpdateStreamListOut:
    """
    Lista eventos da fila de atualização de catálogo com paginação
    e filtro opcional por status.
    """
    if status is not None and status not in ALLOWED_STATUSES:
        raise InvalidArgument(
            "Status deve ser um de: pending, processing, done, failed")

    rows, total = uow.catalog_events.list_events(
        page=page,
        page_size=page_size,
        status=status,
    )

    items = [CatalogUpdateStreamItemOut.model_validate(row) for row in rows]

    return CatalogUpdateStreamListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
