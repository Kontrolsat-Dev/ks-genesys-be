# app/domains/procurement/services/row_ingest.py
from __future__ import annotations

import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Any

from app.core.errors import InvalidArgument
from app.core.normalize import (
    normalize_images,
    normalize_simple,
    to_int,
    to_decimal_str,
    normalize_category,
)
from app.domains.mapping.engine import IngestEngine
from app.repositories.catalog.write.product_write_repo import ProductWriteRepository
from app.repositories.procurement.write.product_event_write_repo import (
    ProductEventWriteRepository,
)
from app.repositories.procurement.write.supplier_item_write_repo import (
    SupplierItemWriteRepository,
)

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
    db: Session,
    *,
    raw_row: dict[str, Any],
    row_index: int,
    id_run: int,
    id_supplier: int,
    feed,
    engine: IngestEngine,
    prod_w: ProductWriteRepository,
    item_w: SupplierItemWriteRepository,
    ev_w: ProductEventWriteRepository,
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

    changed = 0

    # 2) Produto canónico
    try:
        p = prod_w.get_or_create(
            gtin=gtin,
            partnumber=pn,
            brand_name=brand_name,
            default_margin=supplier_margin,
        )
    except InvalidArgument:
        log.warning("[run=%s] row#%s skipped (no product key)", id_run, row_index)
        return 0, 1, 0, None
    except IntegrityError as ie:  # noqa: PERF203
        # race/unique — tenta recuperar
        db.rollback()
        p = prod_w.get_by_gtin(gtin) if gtin else None
        if not p and (brand_name and pn):
            try:
                p = prod_w.get_or_create(
                    gtin=None,
                    partnumber=pn,
                    brand_name=brand_name,
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
    prod_w.fill_canonicals_if_empty(
        p.id,
        name=product_payload.get("name"),
        description=product_payload.get("description"),
        image_url=product_payload.get("image_url"),
        weight_str=product_payload.get("weight_str"),
        partnumber=pn,
        gtin=gtin,
    )
    prod_w.fill_brand_category_if_empty(
        p.id,
        brand_name=brand_name,
        category_name=category_name,
        id_supplier=id_supplier,
    )

    # 4) Meta não-canónica
    for k, v in meta_payload.items():
        if v in (None, "", []):
            continue
        inserted, _conflict = prod_w.add_meta_if_missing(
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

    _item, created, changed_item, old_price, old_stock = item_w.upsert(
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
    changed += ev_w.record_from_item_change(
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
