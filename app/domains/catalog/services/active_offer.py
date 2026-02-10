# app/domains/catalog/services/active_offer.py
from __future__ import annotations

from dataclasses import dataclass

from app.infra.uow import UoW
from app.domains.catalog.services.price_service import compute_sale_price
from app.models.category import Category
from app.models.supplier import Supplier


@dataclass
class ActiveOfferCandidate:
    id_supplier: int
    id_supplier_item: int | None
    unit_cost: float
    stock: int


def _get(obj, key: str):
    """
    Helper para lidar tanto com dicts como com ORM objects/row mappings.
    """
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def choose_active_offer_candidate(
    uow: UoW,
    *,
    id_product: int,
) -> ActiveOfferCandidate | None:
    """
    Decide a melhor oferta para um produto com base nas SupplierItem.
    """
    if not id_product:
        return None

    offers = uow.supplier_items.list_offers_for_product(id_product, only_in_stock=False)

    best_any: ActiveOfferCandidate | None = None
    best_in_stock: ActiveOfferCandidate | None = None

    for item in offers:
        raw_price = _get(item, "price")
        raw_stock = _get(item, "stock")
        id_supplier = _get(item, "id_supplier")
        raw_id_supplier_item = _get(item, "id_supplier_item") or _get(item, "id")
        supplier_discount = float(_get(item, "supplier_discount") or 0)

        if raw_price is None or raw_stock is None or id_supplier is None:
            continue

        try:
            raw_price_float = float(raw_price)
            stock = int(raw_stock)
            # Aplicar desconto do fornecedor para obter custo efetivo
            unit_cost = raw_price_float * (1 - supplier_discount)
        except (TypeError, ValueError):
            continue

        id_supplier_item = int(raw_id_supplier_item) if raw_id_supplier_item is not None else None

        candidate = ActiveOfferCandidate(
            id_supplier=int(id_supplier),
            id_supplier_item=id_supplier_item,
            unit_cost=unit_cost,
            stock=stock,
        )

        # -------- best_any (independente de stock) --------
        if best_any is None:
            best_any = candidate
        else:
            if candidate.unit_cost < best_any.unit_cost:
                best_any = candidate
            elif candidate.unit_cost == best_any.unit_cost:
                if candidate.stock > best_any.stock or (
                    candidate.stock == best_any.stock
                    and candidate.id_supplier < best_any.id_supplier
                ):
                    best_any = candidate

        # -------- best_in_stock (stock > 0) --------
        if stock > 0:
            if best_in_stock is None:
                best_in_stock = candidate
            else:
                if candidate.unit_cost < best_in_stock.unit_cost:
                    best_in_stock = candidate
                elif candidate.unit_cost == best_in_stock.unit_cost:
                    if candidate.stock > best_in_stock.stock or (
                        candidate.stock == best_in_stock.stock
                        and candidate.id_supplier < best_in_stock.id_supplier
                    ):
                        best_in_stock = candidate

    if best_in_stock is not None:
        return best_in_stock

    return best_any


def recalculate_active_offer_for_product(
    uow: UoW,
    *,
    id_product: int,
):
    """
    Recalcula a oferta ativa de um produto com base nas SupplierItem atuais.
    """
    product = uow.products.get(id_product)
    if not product:
        return None

    best = choose_active_offer_candidate(uow, id_product=id_product)

    # Sem qualquer oferta → limpamos a active_offer
    if best is None:
        entity = uow.active_offers_w.upsert(
            id_product=id_product,
            id_supplier=None,
            id_supplier_item=None,
            unit_cost=None,
            unit_price_sent=None,
            stock_sent=0,
        )
        return entity

    # Há oferta candidata → aplicar margem + taxas
    unit_cost = best.unit_cost
    stock_sent = best.stock
    id_supplier = best.id_supplier
    id_supplier_item = best.id_supplier_item

    # Sessão direta necessária para models não gerenciados pelo UoW
    # (ou poderíamos adicionar suppliers/categories ao UoW)
    supplier = uow.db.get(Supplier, id_supplier) if id_supplier else None
    category = (
        uow.db.get(Category, product.id_category) if getattr(product, "id_category", None) else None
    )

    price_calc = compute_sale_price(
        product=product,
        category=category,
        supplier_country=supplier.country if supplier else None,
        cost=unit_cost,
        supplier_discount=0,  # já aplicado em unit_cost
    )

    unit_price_sent: float | None = price_calc.sale_price if price_calc else None

    entity = uow.active_offers_w.upsert(
        id_product=id_product,
        id_supplier=id_supplier,
        id_supplier_item=id_supplier_item,
        unit_cost=unit_cost,
        unit_price_sent=unit_price_sent,
        stock_sent=stock_sent,
    )

    return entity


def recalculate_active_offers_for_supplier(
    uow: UoW,
    *,
    id_supplier: int,
) -> int:
    """
    Recalcula a active_offer de todos os produtos que têm ofertas deste fornecedor.
    """
    product_ids = uow.supplier_items.list_product_ids_for_supplier(id_supplier)

    updated = 0
    for id_product in product_ids:
        recalculate_active_offer_for_product(uow, id_product=id_product)
        updated += 1

    return updated
