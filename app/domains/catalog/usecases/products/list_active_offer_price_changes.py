# app/domains/catalog/usecases/products/list_active_offer_price_changes.py
# Lista alterações de preços em ofertas ativas (produtos importados no PrestaShop)

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from app.core.normalize import to_decimal
from app.infra.uow import UoW
from app.schemas.products import ProductPriceChangeOut, ProductPriceChangeListOut

Direction = Literal["up", "down", "both"]


def execute(
    uow: UoW,
    *,
    direction: Direction,
    days: int,
    min_abs_delta: float | None,
    min_pct_delta: float | None,
    page: int,
    page_size: int,
) -> ProductPriceChangeListOut:
    """
    Lista produtos importados (com id_ecommerce) cujo preço ativo mudou recentemente.
    Útil para análise de variações de preço em produtos que já estão na loja.
    """
    # 1) active_offers + info de produto (nome, marca, categoria, margem)
    rows = uow.active_offers.list_with_product_info()
    if not rows:
        return ProductPriceChangeListOut(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
        )

    now = datetime.utcnow()
    since = now - timedelta(days=days)

    min_abs_dec = Decimal(
        str(min_abs_delta)) if min_abs_delta is not None else None
    min_pct_dec = Decimal(
        str(min_pct_delta)) if min_pct_delta is not None else None

    changes: list[ProductPriceChangeOut] = []

    for row in rows:
        id_product = row.get("id_product")
        id_supplier = row.get("id_supplier")
        if not id_product or not id_supplier:
            continue

        # 2) Eventos só para este (produto, fornecedor)
        events = uow.product_events.list_events_for_product_supplier(
            id_product=id_product,
            id_supplier=id_supplier,
            since=since,
            limit=200,
        )
        if not events:
            continue

        # Só queremos eventos com preço e razão init/change
        filtered = [
            e
            for e in events
            if e.get("price") is not None and (e.get("reason") or "").lower() in {"init", "change"}
        ]
        if len(filtered) < 2:
            continue

        new_evt = filtered[0]
        old_evt = None
        for e in filtered[1:]:
            if e["price"] != new_evt["price"]:
                old_evt = e
                break
        if old_evt is None:
            continue

        new_cost = to_decimal(new_evt["price"])
        old_cost = to_decimal(old_evt["price"])

        margin = to_decimal(row.get("margin"))
        factor = Decimal("1") + (margin / Decimal("100"))

        new_price = (new_cost * factor).quantize(Decimal("0.01"))
        old_price = (old_cost * factor).quantize(Decimal("0.01"))

        delta_abs = new_price - old_price
        if delta_abs == 0:
            continue

        if old_price != 0:
            delta_pct = (delta_abs / old_price * Decimal("100")
                         ).quantize(Decimal("0.01"))
        else:
            delta_pct = Decimal("0.00")

        dir_str: Literal["up", "down"] = "up" if delta_abs > 0 else "down"

        # Filtro por direção
        if direction == "up" and dir_str != "up":
            continue
        if direction == "down" and dir_str != "down":
            continue

        # Thresholds
        if min_abs_dec is not None and abs(delta_abs) < min_abs_dec:
            continue
        if min_pct_dec is not None and abs(delta_pct) < min_pct_dec:
            continue

        changes.append(
            ProductPriceChangeOut(
                id_product=id_product,
                name=row.get("name") or "",
                brand_name=row.get("brand_name") or "",
                category_name=row.get("category_name") or "",
                current_price=new_price,
                previous_price=old_price,
                delta_abs=delta_abs,
                delta_pct=delta_pct,
                direction=dir_str,
                updated_at=new_evt["created_at"],
            )
        )

    # 3) Ordenar por maior variação percentual (absoluto), depois € absoluto
    changes.sort(
        key=lambda c: (abs(c.delta_pct), abs(c.delta_abs)),
        reverse=True,
    )

    total = len(changes)
    if total == 0:
        return ProductPriceChangeListOut(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
        )

    start = (page - 1) * page_size
    end = start + page_size
    page_items = changes[start:end]

    return ProductPriceChangeListOut(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )
