from __future__ import annotations

import logging
from typing import Any
from collections.abc import Iterable
from app.infra.uow import UoW
from app.domains.catalog.services.active_offer import (
    recalculate_active_offer_for_product,
)
from app.domains.catalog.services.sync_events import emit_product_state_event

log = logging.getLogger(__name__)


def sync_active_offer_for_products(
    uow: UoW,
    *,
    affected_products: Iterable[int],
    reason: str = "ingest_supplier",
) -> None:
    """
    Recalcula ProductActiveOffer e emite eventos de estado para os produtos afetados.
    """
    unique_ids: set[int] = {int(pid) for pid in affected_products if pid}

    for id_product in unique_ids:
        product = uow.products.get(id_product)
        if not product:
            continue

        # snapshot da oferta ativa ANTES do recálculo
        prev_active_snapshot: dict[str, Any] | None = None
        if product.active_offer is not None:
            ao = product.active_offer
            prev_active_snapshot = {
                "id_supplier": ao.id_supplier,
                "id_supplier_item": ao.id_supplier_item,
                "unit_price_sent": float(ao.unit_price_sent)
                if ao.unit_price_sent is not None
                else None,
                "stock_sent": int(ao.stock_sent or 0),
            }

        # se o produto não está ligado ao PrestaShop, não há nada para emitir
        if not product.id_ecommerce or product.id_ecommerce <= 0:
            continue

        # recalcula ProductActiveOffer com base nas SupplierItem atuais
        new_active = recalculate_active_offer_for_product(
            uow,
            id_product=id_product,
        )

        # emite evento apenas se o snapshot efetivo mudou
        emit_product_state_event(
            uow,
            product=product,
            active_offer=new_active,
            reason=reason,
            prev_active_snapshot=prev_active_snapshot,
        )
