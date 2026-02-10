# app/domains/catalog/usecases/products/list_products.py
# Lista produtos do catálogo com paginação, filtros e expansão de ofertas

from __future__ import annotations

from app.domains.catalog.services.mappers import (
    map_product_row_to_list_item,
    map_offer_row_to_out,
    map_active_offer_from_pao_to_out,
)
from app.infra.uow import UoW
from app.schemas.products import OfferOut, ProductListOut, ProductListItemOut


def execute(
    uow: UoW,
    *,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    gtin: str | None = None,
    partnumber: str | None = None,
    id_brand: int | None = None,
    brand: str | None = None,
    id_category: int | None = None,
    category: str | None = None,
    has_stock: bool | None = None,
    id_supplier: int | None = None,
    imported: bool | None = None,
    sort: str = "recent",  # "recent" | "name" | "cheapest" (repo trata disto)
    expand_offers: bool = True,
) -> ProductListOut:
    """
    Lista produtos do catálogo com paginação e filtros avançados.
    Suporta pesquisa por texto, GTIN, marca, categoria, stock e fornecedor.
    """
    # 1) Obter produtos paginados
    rows, total = uow.products.list_products(
        page=page,
        page_size=page_size,
        q=q,
        gtin=gtin,
        partnumber=partnumber,
        id_brand=id_brand,
        brand=brand,
        id_category=id_category,
        category=category,
        has_stock=has_stock,
        id_supplier=id_supplier,
        imported=imported,
        sort=sort,
    )

    ids: list[int] = []
    items_map: dict[int, ProductListItemOut] = {}

    for r in rows:
        ids.append(r.id)
        items_map[r.id] = map_product_row_to_list_item(r)

    # 2) Opcionalmente expandir ofertas via repositório de supplier items
    if expand_offers:
        offers_raw = uow.supplier_items.list_offers_for_product_ids(ids, only_in_stock=False)
        for o in offers_raw:
            offer: OfferOut = map_offer_row_to_out(o)
            items_map[o["id_product"]].offers.append(offer)

    # 3) best_offer = melhor oferta COM STOCK (menor preço - já com desconto aplicado)
    from app.domains.catalog.services.best_offer_service import find_best_offer_from_schemas

    for po in items_map.values():
        po.best_offer = find_best_offer_from_schemas(po.offers, require_stock=True)

    # 4) active_offer = oferta ativa/comunicada (ProductActiveOffer)
    active_map = uow.active_offers.list_for_products(ids)

    for po in items_map.values():
        active: OfferOut | None = None
        pao = active_map.get(po.id)

        if po.id_ecommerce and po.id_ecommerce > 0 and pao and pao.id_supplier is not None:
            active = map_active_offer_from_pao_to_out(pao)

        po.active_offer = active

    return ProductListOut(
        items=[items_map[i] for i in ids],
        total=int(total),
        page=page,
        page_size=page_size,
    )
