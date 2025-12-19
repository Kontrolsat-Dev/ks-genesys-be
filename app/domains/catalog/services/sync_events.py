# app/domains/catalog/services/sync_events.py
from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_active_offer import ProductActiveOffer
from app.repositories.catalog.write.catalog_update_stream_write_repo import (
    CatalogUpdateStreamWriteRepository,
)


def _snapshot_active_offer(ao: ProductActiveOffer | None) -> dict[str, Any]:
    """
    Normaliza a oferta ativa para um dict estável, focado nos campos
    relevantes para o PrestaShop.
    """
    if ao is None:
        return {
            "id_supplier": None,
            "id_supplier_item": None,
            "unit_price_sent": None,
            "stock_sent": 0,
        }

    return {
        "id_supplier": ao.id_supplier,
        "id_supplier_item": ao.id_supplier_item,
        "unit_price_sent": float(ao.unit_price_sent) if ao.unit_price_sent is not None else None,
        "stock_sent": int(ao.stock_sent or 0),
    }


def emit_product_state_event(
    db: Session,
    *,
    product: Product,
    active_offer: ProductActiveOffer | None,
    reason: str,
    prev_active_snapshot: Mapping[str, Any] | None = None,
) -> None:
    """
    Enfileira um evento de `product_state_changed` **apenas** se o estado
    efetivo da oferta comunicada tiver mudado (fornecedor, preço enviado, stock).

    - Se não houver id_ecommerce -> não faz nada.
    - Se o snapshot anterior == snapshot atual -> não faz nada.
    - Caso contrário -> enfileira no CatalogUpdateStream com prioridade
      baseada em transição de stock.
    """
    # Só faz sentido emitir para produtos ligados ao PrestaShop
    if not product.id_ecommerce or product.id_ecommerce <= 0:
        return

    current = _snapshot_active_offer(active_offer)

    # --- short-circuit: nada mudou, nada a emitir ---
    if prev_active_snapshot is not None:
        keys = ("id_supplier", "id_supplier_item", "unit_price_sent", "stock_sent")
        prev_norm = {k: prev_active_snapshot.get(k) for k in keys}
        curr_norm = {k: current.get(k) for k in keys}

        if prev_norm == curr_norm:
            # Exatamente o que estás a ver nos teus exemplos:
            # 1) e 2) têm supplier, preço enviado e stock iguais → não enfileiramos.
            return

    # --- prioridade com base em transição de stock e preço ---
    old_stock = None
    old_price = None
    if prev_active_snapshot is not None:
        old_stock = prev_active_snapshot.get("stock_sent")
        old_price = prev_active_snapshot.get("unit_price_sent")

    new_stock = current.get("stock_sent")
    new_price = current.get("unit_price_sent")

    priority = 5  # default

    try:
        old_stock_i = int(old_stock) if old_stock is not None else None
        new_stock_i = int(new_stock) if new_stock is not None else None
    except (TypeError, ValueError):
        old_stock_i = None
        new_stock_i = None

    # Prioridades (maior = mais urgente):
    # 10 = saída de stock (produto ficou sem stock)
    # 9 = reentrada de stock (produto voltou a ter stock)
    # 8 = alteração de preço (com stock inalterado)
    # 5 = default (outras alterações)

    if old_stock_i is not None and new_stock_i is not None:
        if old_stock_i > 0 and new_stock_i == 0:
            # ficou sem stock - PRIORIDADE MÁXIMA
            priority = 10
        elif old_stock_i <= 0 and new_stock_i > 0:
            # voltou a ter stock - prioridade alta
            priority = 9
        elif old_price != new_price and old_price is not None and new_price is not None:
            # preço alterou mas stock não teve transição crítica
            priority = 8

    repo = CatalogUpdateStreamWriteRepository(db)
    repo.enqueue_product_state_change(
        product=product,
        active_offer=active_offer,
        reason=reason,
        priority=priority,
    )
