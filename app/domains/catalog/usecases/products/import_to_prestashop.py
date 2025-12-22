# app/domains/catalog/usecases/products/import_to_prestashop.py
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
from app.repositories.catalog.read.products_read_repo import ProductsReadRepository
from app.repositories.catalog.read.brand_read_repo import BrandsReadRepository
from app.repositories.catalog.write.product_active_offer_write_repo import (
    ProductActiveOfferWriteRepository,
)
from app.repositories.procurement.read.supplier_item_read_repo import SupplierItemReadRepository
from app.core.errors import NotFound, InvalidArgument


def execute(
    uow: UoW,
    ps_client: PrestashopClient,
    *,
    id_product: int,
    id_ps_category: int,
) -> dict:
    """
    Import a product to PrestaShop.

    1. Get product from database
    2. Get best offer (lowest price with stock > 0)
    3. Calculate sale price = cost * (1 + margin)
    4. Build product payload
    5. Call PrestaShop API to create product
    6. Update product with id_ecommerce

    Returns the PS response with id_product.
    """
    db = uow.db
    prod_r = ProductsReadRepository(db)
    brand_r = BrandsReadRepository(db)
    item_r = SupplierItemReadRepository(db)
    active_offer_w = ProductActiveOfferWriteRepository(db)

    # Get product
    product = prod_r.get(id_product)
    if not product:
        raise NotFound(f"Product {id_product} not found")

    if product.id_ecommerce:
        raise InvalidArgument(
            f"Product {id_product} already imported (PS ID: {product.id_ecommerce})"
        )

    # Get offers and find best one (lowest price, regardless of stock)
    offers = item_r.list_offers_for_product(id_product, only_in_stock=False)

    best_offer = None
    if offers:
        # Sort by price ascending and pick the lowest
        offers_sorted = sorted(
            offers,
            key=lambda o: Decimal(o["price"]) if o.get("price") else Decimal("999999"),
        )
        best_offer = offers_sorted[0] if offers_sorted else None

    # Calculate price with margin
    price_str: str | None = None
    stock: int | None = None
    cost: Decimal | None = None

    if best_offer:
        cost = Decimal(best_offer["price"]) if best_offer.get("price") else None
        stock = best_offer.get("stock") or 0

        if cost is not None:
            margin = Decimal(str(product.margin or 0))
            sale_price = cost * (1 + margin)
            # Round to 2 decimal places
            price_str = str(sale_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    # Get brand name if product has a brand
    brand_name: str | None = None
    if product.id_brand:
        brand = brand_r.get(product.id_brand)
        if brand:
            brand_name = brand.name

    # Build payload for PrestaShop
    payload = {
        "name": product.name or f"Product #{product.id}",
        "description": product.description or "",
        "id_category": id_ps_category,
        "price": price_str,
        "stock": stock,
        "gtin": product.gtin,
        "partnumber": product.partnumber,
        "image_url": product.image_url,
        "weight": product.weight_str,
        "brand_name": brand_name,
    }

    # Call PrestaShop API
    result = ps_client.create_product(payload)

    # Update product with PS ID
    ps_product_id = result.get("id_product")
    if ps_product_id:
        product.id_ecommerce = int(ps_product_id)
        db.add(product)
        db.flush()

        # Update active offer with the imported offer data
        if best_offer:
            active_offer_w.upsert(
                id_product=id_product,
                id_supplier=best_offer.get("id_supplier"),
                id_supplier_item=best_offer.get("id") or best_offer.get("id_supplier_item"),
                unit_cost=float(cost) if cost is not None else None,
                unit_price_sent=float(price_str) if price_str else None,
                stock_sent=stock,
            )

        # Commit all changes (id_ecommerce + active_offer)
        uow.commit()

    return {
        "id_product": id_product,
        "id_ecommerce": ps_product_id,
        "success": True,
        "price_sent": price_str,
        "stock_sent": stock,
        **result,
    }
