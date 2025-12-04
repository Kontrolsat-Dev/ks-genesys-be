# app/domains/catalog/usecases/products/list_catalog_price_changes.py
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import select

from app.infra.uow import UoW
from app.models.product import Product as P
from app.models.brand import Brand as B
from app.models.category import Category as C
from app.models.supplier import Supplier as S
from app.models.product_supplier_event import ProductSupplierEvent as PSE
from app.schemas.products import ProductPriceChangeOut, ProductPriceChangeListOut
from app.core.normalize import to_decimal

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
    db = uow.db  # type: ignore[attr-defined]

    now = datetime.utcnow()
    since = now - timedelta(days=days)

    min_abs_dec = Decimal(str(min_abs_delta)) if min_abs_delta is not None else None
    min_pct_dec = Decimal(str(min_pct_delta)) if min_pct_delta is not None else None

    # 1) Buscar TODOS os eventos relevantes numa só query
    stmt = (
        select(
            PSE.id_product,
            PSE.id_supplier,
            PSE.created_at,
            PSE.reason,
            PSE.price,
            S.name.label("supplier_name"),
            P.name.label("product_name"),
            P.margin,
            P.id_ecommerce,
            B.name.label("brand_name"),
            C.name.label("category_name"),
        )
        .join(P, P.id == PSE.id_product)
        .join(S, S.id == PSE.id_supplier, isouter=True)
        .join(B, B.id == P.id_brand, isouter=True)
        .join(C, C.id == P.id_category, isouter=True)
        .where(PSE.price.is_not(None))
        .where(PSE.created_at >= since)
        # só produtos NÃO importados (id_ecommerce nulo ou <= 0)
        .where((P.id_ecommerce.is_(None)) | (P.id_ecommerce <= 0))
        .where(PSE.reason.in_(("init", "change")))
        .order_by(
            PSE.id_product,
            PSE.id_supplier,
            PSE.created_at.desc(),
            PSE.id.desc(),
        )
    )

    rows = [dict(r._mapping) for r in db.execute(stmt).all()]
    if not rows:
        return ProductPriceChangeListOut(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
        )

    # 2) Agrupar por (produto, fornecedor) e encontrar a ÚLTIMA alteração de preço
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (int(r["id_product"]), int(r["id_supplier"]))
        grouped[key].append(r)

    changes: list[ProductPriceChangeOut] = []

    for (id_product, id_supplier), evs in grouped.items():
        # Já vêm ordenados desc, mas garantimos
        evs.sort(key=lambda e: e["created_at"], reverse=True)

        new_evt = evs[0]
        old_evt: dict[str, Any] | None = None

        # procurar o evento anterior com preço diferente
        for e in evs[1:]:
            if e["price"] != new_evt["price"]:
                old_evt = e
                break

        if old_evt is None:
            continue

        new_cost = to_decimal(new_evt["price"])
        old_cost = to_decimal(old_evt["price"])

        margin = to_decimal(new_evt.get("margin"))
        factor = Decimal("1") + (margin / Decimal("100"))

        new_price = (new_cost * factor).quantize(Decimal("0.01"))
        old_price = (old_cost * factor).quantize(Decimal("0.01"))

        delta_abs = new_price - old_price
        if delta_abs == 0:
            continue

        if old_price != 0:
            delta_pct = (delta_abs / old_price * Decimal("100")).quantize(Decimal("0.01"))
        else:
            delta_pct = Decimal("0.00")

        dir_str: Literal["up", "down"] = "up" if delta_abs > 0 else "down"

        # filtro direção
        if direction == "up" and dir_str != "up":
            continue
        if direction == "down" and dir_str != "down":
            continue

        # thresholds
        if min_abs_dec is not None and abs(delta_abs) < min_abs_dec:
            continue
        if min_pct_dec is not None and abs(delta_pct) < min_pct_dec:
            continue

        changes.append(
            ProductPriceChangeOut(
                id_product=id_product,
                name=new_evt["product_name"] or "",
                brand_name=new_evt.get("brand_name") or "",
                category_name=new_evt.get("category_name") or "",
                current_price=new_price,
                previous_price=old_price,
                delta_abs=delta_abs,
                delta_pct=delta_pct,
                direction=dir_str,
                updated_at=new_evt["created_at"],
                id_supplier=id_supplier,
                supplier_name=new_evt.get("supplier_name"),
            )
        )

    # 3) Ordenar por maior variação (pct, depois €) e paginar
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
