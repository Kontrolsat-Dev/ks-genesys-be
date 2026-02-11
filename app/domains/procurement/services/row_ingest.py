# app/domains/procurement/services/row_ingest.py
from __future__ import annotations

import logging
from sqlalchemy.exc import IntegrityError
from typing import Any

from app.core.errors import InvalidArgument
from app.core.normalize import (
    normalize_images,
    normalize_simple,
    to_int,
    to_decimal_str,
    normalize_category,
)
from app.domains.mapping.services.engine import IngestEngine
from app.infra.uow import UoW

log = logging.getLogger(__name__)

CANON_PRODUCT_KEYS = {
    "gtin",
    "mpn",
    "partnumber",
    "name",
    "description",
    "image_url",
    "image_urls",
    "category",
    "weight",
    "brand",
}
CANON_OFFER_KEYS = {"price", "stock", "sku"}


def _split_payload(mapped: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Separa o resultado do mapper em:
    - product_payload (campos canónicos de produto)
    - offer_payload   (preço/stock/sku + chaves técnicas)
    - meta_payload    (resto dos campos, não-canónicos)
    """
    out_product = {
        "gtin": (mapped.get("gtin") or "") or None,
        "partnumber": (mapped.get("mpn") or mapped.get("partnumber") or "") or None,
        "name": mapped.get("name"),
        "description": mapped.get("description"),
        "image_url": mapped.get("image_url"),
        "weight_str": mapped.get("weight"),
    }

    # Preço: normalizar para decimal string “limpa” (39,99 € → "39.99")
    raw_price = mapped.get("price")
    price_str = to_decimal_str(raw_price) or "" if raw_price is not None else ""

    # Stock: aguentar porcarias tipo "10+", " 5 ", "N/A" → 10, 5, 0
    raw_stock = mapped.get("stock")
    stock_int = to_int(raw_stock)
    if stock_int is None:
        stock_int = 0

    out_offer = {
        "price": price_str,
        "stock": stock_int,
        "sku": (mapped.get("sku") or mapped.get("partnumber") or mapped.get("gtin") or "").strip(),
        "gtin": out_product["gtin"],
        "partnumber": out_product["partnumber"],
    }

    used = set(CANON_PRODUCT_KEYS) | set(CANON_OFFER_KEYS)
    meta = {k: v for k, v in mapped.items() if k not in used and v not in (None, "", [])}
    return out_product, out_offer, meta


def process_row(
    uow: UoW,
    *,
    raw_row: dict[str, Any],
    row_index: int,
    id_run: int,
    id_supplier: int,
    feed,
    engine: IngestEngine,
    supplier_margin: float,
) -> tuple[int, int, int, int | None]:
    """
    Processa uma linha do feed.

    Retorna: (ok_inc, bad_inc, changed_inc, product_id_or_none)
    """
    # 1) Mapping
    mapped, err = engine.map_row(raw_row)
    if not mapped:
        log.warning("[run=%s] row#%s invalid (mapper): %s", id_run, row_index, err)
        return 0, 1, 0, None

    mapped = normalize_images(mapped)
    product_payload, offer_payload, meta_payload = _split_payload(mapped)

    gtin = product_payload.get("gtin") or None
    pn = product_payload.get("partnumber") or None

    raw_brand_name = mapped.get("brand") or None
    raw_category_name = mapped.get("category") or None

    brand_name = normalize_simple(raw_brand_name) if raw_brand_name else None
    category_name = normalize_category(raw_category_name) if raw_category_name else None

    # Resolve IDs de marca e categoria de forma orquestrada
    id_brand = None
    if brand_name:
        id_brand = uow.brands_w.get_or_create(brand_name).id

    id_category = None
    if category_name:
        id_category = uow.categories_w.get_or_create(category_name, id_supplier=id_supplier).id

    changed = 0

    # 2) Produto canónico
    try:
        p = uow.products_w.get_or_create(
            gtin=gtin,
            partnumber=pn,
            id_brand=id_brand,
            default_margin=supplier_margin,
        )
    except InvalidArgument:
        log.warning("[run=%s] row#%s skipped (no product key)", id_run, row_index)
        return 0, 1, 0, None
    except IntegrityError as ie:  # noqa: PERF203
        # race/unique — tenta recuperar
        uow.db.rollback()
        p = uow.products.get_by_gtin(gtin) if gtin else None
        if not p and (id_brand and pn):
            try:
                p = uow.products_w.get_or_create(
                    gtin=None,
                    partnumber=pn,
                    id_brand=id_brand,
                    default_margin=supplier_margin,
                )
            except Exception:  # noqa: BLE001
                p = None

        if not p:
            log.warning(
                "[run=%s] row#%s skipped after IntegrityError: %s",
                id_run,
                row_index,
                ie,
            )
            return 0, 1, 0, None

    # 3) Preencher campos canónicos vazios + brand/category
    uow.products_w.fill_canonicals_if_empty(
        p.id,
        name=product_payload.get("name"),
        description=product_payload.get("description"),
        image_url=product_payload.get("image_url"),
        weight_str=product_payload.get("weight_str"),
        partnumber=pn,
        gtin=gtin,
    )

    # Preencher brand/category se ainda não tiver (orquestração explícita)
    if id_brand and not p.id_brand:
        p.id_brand = id_brand
    if id_category and not p.id_category:
        p.id_category = id_category

    # 4) Meta não-canónica
    for k, v in meta_payload.items():
        if v in (None, "", []):
            continue
        inserted, _conflict = uow.products_w.add_meta_if_missing(
            p.id,
            name=str(k),
            value=str(v),
        )
        if inserted:
            changed += 1

    # 5) Upsert da oferta do fornecedor
    price = offer_payload["price"]
    stock = offer_payload["stock"]
    sku = offer_payload["sku"] or (pn or gtin or f"row-{row_index}")

    _item, created, changed_item, old_price, old_stock = uow.supplier_items_w.upsert(
        id_feed=feed.id,
        id_product=p.id,
        sku=sku,
        price=price,
        stock=stock,
        gtin=gtin,
        partnumber=pn,
        id_feed_run=id_run,
    )

    # 5.1) Se o produto estava EOL e agora este supplier tem stock > 0, reverter EOL
    if stock > 0 and p.is_eol:
        p.is_eol = False
        log.info(
            "[run=%s] product_id=%s revived_from_eol_by_supplier=%s stock=%s",
            id_run,
            p.id,
            id_supplier,
            stock,
        )

    # 6) Evento por criação/alteração da oferta do supplier
    changed += uow.product_events_w.record_from_item_change(
        id_product=p.id,
        id_supplier=id_supplier,
        gtin=gtin,
        new_price=price,
        new_stock=stock,
        created=created,
        changed=changed_item,
        id_feed_run=id_run,
    )

    return 1, 0, changed, p.id
