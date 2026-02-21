from __future__ import annotations

from app.core.errors import NotFound, Conflict
from app.infra.uow import UoW
from app.schemas.products import ProductDetailOut
from app.domains.catalog.services.product_detail import get_product_detail, DetailOptions


def execute(
        uow: UoW,
        *,
        gtin: str,
        id_product_ecommerce: int,
        override: bool = False,
) -> ProductDetailOut:
    product_r = uow.products
    product_w = uow.products_w

    product = product_r.get_by_gtin(gtin)
    if not product:
        raise NotFound(f"Product with GTIN '{gtin}' not found")
    if product.id_ecommerce and not override:
        raise Conflict(
            f"Product '{gtin}' already mapped to Ecommerce ID [{product.id_ecommerce}]")

    product_w.add_ecommerce_id(product.id, id_product_ecommerce)
    uow.commit()

    return get_product_detail(uow, id_product=product.id, opts=DetailOptions())
