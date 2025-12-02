# app/domains/catalog/usecases/catalog_update_stream/get_pending_events.py
from __future__ import annotations

import json

from app.infra.uow import UoW
from app.repositories.catalog.read.catalog_update_stream_read_repo import (
    CatalogUpdateStreamReadRepository,
)
from app.repositories.catalog.write.catalog_update_stream_write_repo import (
    CatalogUpdateStreamWriteRepository,
)
from app.schemas.catalog_update_stream import (
    CatalogUpdateEventOut,
    CatalogUpdatePayload,
)


def execute(
    uow: UoW,
    *,
    limit: int,
    min_priority: int | None,
) -> list[CatalogUpdateEventOut]:
    """
    Usecase:
    - lê um batch de eventos `pending` (sem alterar estado) via read repo
    - marca-os como `processing` via write repo
    - devolve lista de CatalogUpdateEventOut
    """
    db = uow.db

    read_repo = CatalogUpdateStreamReadRepository(db)
    write_repo = CatalogUpdateStreamWriteRepository(db)

    events = read_repo.list_pending_for_claim(limit=limit, min_priority=min_priority)

    if not events:
        # Nada para processar, não precisamos de commit
        return []

    ids = [evt.id for evt in events]
    write_repo.mark_batch_processing(ids=ids)

    items_out: list[CatalogUpdateEventOut] = []

    for evt in events:
        try:
            payload_dict = json.loads(evt.payload or "{}")
        except Exception:
            payload_dict = {}

        items_out.append(
            CatalogUpdateEventOut(
                id=evt.id,
                id_product=evt.id_product,
                id_ecommerce=evt.id_ecommerce,
                priority=evt.priority,
                event_type=evt.event_type,
                created_at=evt.created_at,
                payload=CatalogUpdatePayload.model_validate(payload_dict or {}),
            )
        )

    uow.commit()

    return items_out
