from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import NotFound

from app.domains.catalog.services.mappers import (
    map_product_row_to_out,
    map_offer_row_to_out,
    map_active_offer_from_pao_to_out,
)
from app.infra.uow import UoW
from .series import aggregate_daily_points
from app.domains.catalog.services.best_offer_service import find_best_offer_from_schemas
from app.domains.catalog.services.price_service import PriceService
from app.schemas.products import (
    ProductOut,
    ProductMetaOut,
    OfferOut,
    ProductEventOut,
    ProductDetailOut,
    ProductStatsOut,
    SeriesPointOut,
    PriceBreakdown,
)


@dataclass(frozen=True)
class DetailOptions:
    expand_meta: bool = True
    expand_offers: bool = True
    expand_events: bool = True
    events_days: int | None = 90
    events_limit: int | None = 2000
    aggregate_daily: bool = True


def get_product_detail(uow: UoW, *, id_product: int, opts: DetailOptions) -> ProductDetailOut:
    # 1) produto + nomes agregados
    row = uow.products.get_product_with_names(id_product)
    if not row:
        raise NotFound(f"Product {id_product} not found")

    p: ProductOut = map_product_row_to_out(row)

    # 2) meta
    meta_list: list[ProductMetaOut] = []
    if opts.expand_meta:
        meta_rows = uow.product_meta.list_for_product(p.id)
        meta_list = [
            ProductMetaOut(
                name=m.name,
                value=m.value,
                created_at=m.created_at,
            )
            for m in meta_rows
        ]

    # 3) ofertas
    offers: list[OfferOut] = []
    offers_in_stock = 0
    suppliers_set: set[int] = set()
    if opts.expand_offers:
        offers_raw = uow.supplier_items.list_offers_for_product(p.id, only_in_stock=False)
        for o in offers_raw:
            offer: OfferOut = map_offer_row_to_out(o)
            offers.append(offer)
            if (offer.stock or 0) > 0:
                offers_in_stock += 1
            if o.get("id_supplier"):
                suppliers_set.add(int(o["id_supplier"]))

    # 3.1) best_offer = melhor oferta COM STOCK (menor preço - já com desconto)
    best = find_best_offer_from_schemas(offers, require_stock=True)

    # 3.2) active_offer = oferta ativa/comunicada (ProductActiveOffer)
    active_offer: OfferOut | None = None
    if p.id_ecommerce and p.id_ecommerce > 0:
        pao = uow.active_offers.get_by_product(p.id)
        if pao and pao.id_supplier is not None:
            active_offer = map_active_offer_from_pao_to_out(pao)

    # 3.3) Calcular Price Breakdown usando a melhor oferta disponível
    # Se houver active_offer, usamos essa (já foi calculada e enviada).
    # Se não, usamos a best_offer para simular quanto ficaria.
    price_breakdown = None
    reference_offer = active_offer or best

    if reference_offer and reference_offer.price:
        try:
            # 1. Fetch Category (necessário para margem e taxas default)
            cat_obj = None
            if p.id_category:
                cat_obj = uow.categories.get(p.id_category)

            # 2. Obter supplier (opcional, para isenção PT)
            # Para visualização rápida, podemos ignorar e assumir "pior caso" (com taxa)
            # ou tentar obter se reference_offer tiver id_supplier.
            # Vamos ignorar para performance de leitura.

            # 3. Resolução Centralizada
            params = PriceService.resolve_pricing_params(product=p, category=cat_obj, supplier=None)

            # 4. Calcular Breakdown
            cost = float(reference_offer.price)
            pb_dict = PriceService.calculate_price_breakdown(
                cost=cost,
                margin=params["margin"],
                ecotax=params["ecotax"],
                extra_fees=params["extra_fees"],
            )
            price_breakdown = PriceBreakdown(**pb_dict)

        except Exception:
            # Se falhar calculo (ex: dados sujos), segue sem breakdown
            pass

    # 4) eventos + séries
    events_out: list[ProductEventOut] | None = None
    series_daily: list[SeriesPointOut] | None = None
    first_seen = None
    last_seen = None
    last_change_at = None

    if opts.expand_events:
        evs = uow.product_events.list_events_for_product(
            p.id, days=opts.events_days, limit=opts.events_limit
        )
        if evs:
            events_out = [
                ProductEventOut(
                    created_at=e["created_at"],
                    reason=e["reason"],
                    price=e.get("price"),
                    stock=e.get("stock"),
                    id_supplier=e.get("id_supplier"),
                    supplier_name=e.get("supplier_name"),
                    id_feed_run=e.get("id_feed_run"),
                )
                for e in evs
            ]

            first_seen = evs[0]["created_at"]
            last_seen = evs[-1]["created_at"]
            for e in reversed(evs):
                if (e.get("reason") or "").lower() != "init":
                    last_change_at = e["created_at"]
                    break
            if opts.aggregate_daily:
                series_daily = aggregate_daily_points(events_out)

    stats = ProductStatsOut(
        first_seen=first_seen or p.created_at,
        last_seen=last_seen or p.updated_at or p.created_at,
        suppliers_count=len(suppliers_set),
        offers_in_stock=offers_in_stock,
        last_change_at=last_change_at,
    )

    return ProductDetailOut(
        product=p,
        meta=meta_list,
        offers=offers,
        best_offer=best,
        active_offer=active_offer,
        stats=stats,
        events=events_out,
        series_daily=series_daily,
        price_breakdown=price_breakdown,
    )
