# app/domains/catalog/usecases/catalog_update_stream/ack_events.py
"""
Confirma o processamento de eventos de syncronização de catálogo.

Quando status = 'done':
- Atualiza ProductActiveOffer com os valores do payload (o que foi comunicado ao PS)

Quando status = 'failed':
- Guarda erro, NÃO toca em ProductActiveOffer
"""

from __future__ import annotations

import logging
from typing import Any

from app.infra.uow import UoW
from app.repositories.catalog.write.catalog_update_stream_write_repo import (
    CatalogUpdateStreamWriteRepository,
)
from app.repositories.catalog.read.catalog_update_stream_read_repo import (
    CatalogUpdateStreamReadRepository,
)
from app.repositories.catalog.write.product_active_offer_write_repo import (
    ProductActiveOfferWriteRepository,
)
from app.models.catalog_update_stream import CatalogUpdateStream

log = logging.getLogger("gsm.catalog.ack_events")


def _update_active_offer_from_payload(
    pao_repo: ProductActiveOfferWriteRepository,
    event: CatalogUpdateStream,
) -> None:
    """
    Extrai dados do payload do evento e atualiza ProductActiveOffer.

    Esta função é chamada APENAS quando o evento é marcado como 'done',
    garantindo que a oferta ativa reflete o que foi realmente comunicado ao PS.
    """
    import json

    # Payload está guardado como string JSON na BD
    raw_payload = event.payload
    if not raw_payload:
        log.warning(
            "ack_events: event %s has no payload, skipping",
            event.id,
        )
        return

    # Parsear JSON se for stringO
    if isinstance(raw_payload, str):
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            log.error(
                "ack_events: event %s has invalid JSON payload, skipping",
                event.id,
            )
            return
    else:
        payload = raw_payload

    ao = payload.get("active_offer")

    if not ao:
        log.warning(
            "ack_events: event %s has no active_offer in payload, skipping",
            event.id,
        )
        return

    pao_repo.upsert(
        id_product=event.id_product,
        id_supplier=ao.get("id_supplier"),
        id_supplier_item=ao.get("id_supplier_item"),
        unit_cost=ao.get("unit_cost"),
        unit_price_sent=ao.get("unit_price_sent"),
        stock_sent=ao.get("stock_sent"),
    )

    log.info(
        "ack_events: updated ProductActiveOffer for product %s from event %s",
        event.id_product,
        event.id,
    )


def execute(
    uow: UoW,
    *,
    ids: list[int],
    status: str,
    error: str | None,
) -> dict[str, Any]:
    """
    Confirma processamento de eventos.

    - status='done': Atualiza ProductActiveOffer com valores do payload
    - status='failed': Guarda erro, NÃO toca em ProductActiveOffer
    """
    db = uow.db
    write_repo = CatalogUpdateStreamWriteRepository(db)

    # Quando status=done, atualizar ProductActiveOffer com dados do payload
    if status == "done":
        read_repo = CatalogUpdateStreamReadRepository(db)
        pao_repo = ProductActiveOfferWriteRepository(db)

        events = read_repo.get_by_ids(ids)
        for evt in events:
            _update_active_offer_from_payload(pao_repo, evt)

    updated = write_repo.ack_batch(ids=ids, status=status, error=error)
    uow.commit()

    return {"updated": updated}
