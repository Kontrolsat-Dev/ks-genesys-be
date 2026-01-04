from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models.product_active_offer import ProductActiveOffer
from app.schemas.products import ProductOut, ProductListItemOut, OfferOut


def map_product_row_to_out(row: Any) -> ProductOut:
    """
    Converte um row vindo dos READ repos (SQLAlchemy row/ORM) num ProductOut base.

    Usamos getattr com default=None para ser tolerante a diferenças entre
    queries (ex.: list vs detail).
    """
    return ProductOut(
        id=row.id,
        gtin=getattr(row, "gtin", None),
        id_ecommerce=getattr(row, "id_ecommerce", None),
        id_brand=getattr(row, "id_brand", None),
        brand_name=getattr(row, "brand_name", None),
        id_category=getattr(row, "id_category", None),
        category_name=getattr(row, "category_name", None),
        partnumber=getattr(row, "partnumber", None),
        name=getattr(row, "name", None),
        margin=getattr(row, "margin", None),
        description=getattr(row, "description", None),
        image_url=getattr(row, "image_url", None),
        weight_str=getattr(row, "weight_str", None),
        created_at=getattr(row, "created_at", None),
        updated_at=getattr(row, "updated_at", None),
    )


def map_product_row_to_list_item(row: Any) -> ProductListItemOut:
    """
    Versão para listagens: parte do ProductOut base e embrulha num ProductListItemOut.
    """
    base = map_product_row_to_out(row)
    # model_dump garante que se no futuro adicionares campos, isto continua consistente
    return ProductListItemOut(**base.model_dump())


def map_offer_row_to_out(src: Mapping[str, Any]) -> OfferOut:
    """
    Converte o dict/row devolvido pelos SupplierItem READ repos num OfferOut.
    O preço retornado já tem o desconto do fornecedor aplicado.
    """
    # Aplicar desconto ao preço
    raw_price = src.get("price")
    discount = float(src.get("supplier_discount") or 0)
    effective_price: str | None = None
    if raw_price is not None:
        try:
            effective_price = str(round(float(raw_price) * (1 - discount), 2))
        except (ValueError, TypeError):
            effective_price = raw_price

    return OfferOut(
        id_supplier=src["id_supplier"],
        supplier_name=src.get("supplier_name"),
        supplier_image=src.get("supplier_image"),
        id_feed=src["id_feed"],
        sku=src["sku"],
        price=effective_price,
        stock=src.get("stock"),
        id_last_seen_run=src.get("id_last_seen_run"),
        updated_at=src.get("updated_at"),
    )


def map_active_offer_from_pao_to_out(pao: ProductActiveOffer) -> OfferOut:
    """Converte um ProductActiveOffer (snapshot enviado para o PrestaShop)
    num OfferOut coerente com o resto da API.

    - price vem de unit_price_sent
    - stock vem de stock_sent
    - supplier_name/image vêm do Supplier relacionado (se carregado)
    - id_feed/sku/id_last_seen_run/updated_at vêm do SupplierItem relacionado, quando existir.
    """
    supplier = getattr(pao, "supplier", None)
    supplier_item = getattr(pao, "supplier_item", None)

    # preço enviado ao PrestaShop, em formato string (compatível com OfferOut.price)
    price_str: str | None = None
    if getattr(pao, "unit_price_sent", None) is not None:
        try:
            price_str = str(pao.unit_price_sent)
        except Exception:
            price_str = None

    # stock enviado ao PrestaShop
    stock_val = getattr(pao, "stock_sent", None)
    stock_int: int | None
    try:
        stock_int = int(stock_val) if stock_val is not None else None
    except (TypeError, ValueError):
        stock_int = None

    # Metadados vindos do SupplierItem (podem não existir se o registo tiver sido apagado)
    if supplier_item is not None:
        id_feed = supplier_item.id_feed
        sku = supplier_item.sku
        id_last_seen_run = supplier_item.id_feed_run
        updated_at = supplier_item.updated_at or getattr(pao, "synced_at", None)
    else:
        id_feed = 0
        sku = ""
        id_last_seen_run = None
        updated_at = getattr(pao, "synced_at", None)

    return OfferOut(
        id_supplier=int(pao.id_supplier),
        supplier_name=getattr(supplier, "name", None) if supplier is not None else None,
        supplier_image=getattr(supplier, "logo_image", None) if supplier is not None else None,
        id_feed=id_feed,
        sku=sku,
        price=price_str,
        stock=stock_int,
        id_last_seen_run=id_last_seen_run,
        updated_at=updated_at,
    )
