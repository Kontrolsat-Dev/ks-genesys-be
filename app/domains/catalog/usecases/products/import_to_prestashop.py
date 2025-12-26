# app/domains/catalog/usecases/products/import_to_prestashop.py
"""
UseCase para importar um produto para o PrestaShop.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
from app.repositories.catalog.read.product_read_repo import ProductReadRepository
from app.repositories.catalog.read.brand_read_repo import BrandReadRepository
from app.repositories.catalog.write.product_active_offer_write_repo import (
    ProductActiveOfferWriteRepository,
)
from app.repositories.procurement.read.supplier_item_read_repo import SupplierItemReadRepository
from app.core.errors import NotFound, InvalidArgument
from app.domains.audit.services.audit_service import AuditService
from app.schemas.products import ProductImportOut


def execute(
    uow: UoW,
    ps_client: PrestashopClient,
    *,
    id_product: int,
    id_ps_category: int,
) -> ProductImportOut:
    """
    Importa um produto para o PrestaShop.

    Passos:
    1. Obter produto da base de dados
    2. Obter melhor oferta (menor preço)
    3. Calcular preço de venda = custo * (1 + margem)
    4. Construir payload para PrestaShop
    5. Chamar API do PrestaShop
    6. Atualizar produto com id_ecommerce

    Returns:
        ProductImportOut schema
    """
    db = uow.db
    prod_r = ProductReadRepository(db)
    brand_r = BrandReadRepository(db)
    item_r = SupplierItemReadRepository(db)
    active_offer_w = ProductActiveOfferWriteRepository(db)

    # Obter produto
    product = prod_r.get(id_product)
    if not product:
        raise NotFound(f"Product {id_product} not found")

    if product.id_ecommerce:
        raise InvalidArgument(
            f"Product {id_product} already imported (PS ID: {product.id_ecommerce})"
        )

    # Obter ofertas e encontrar a melhor (menor preço)
    offers = item_r.list_offers_for_product(id_product, only_in_stock=False)

    best_offer = None
    if offers:
        # Ordenar por preço ascendente e escolher o menor
        offers_sorted = sorted(
            offers,
            key=lambda o: Decimal(o["price"]) if o.get("price") else Decimal("999999"),
        )
        best_offer = offers_sorted[0] if offers_sorted else None

    # Calcular preço com margem
    price_str: str | None = None
    stock: int | None = None
    cost: Decimal | None = None

    if best_offer:
        cost = Decimal(best_offer["price"]) if best_offer.get("price") else None
        stock = best_offer.get("stock") or 0

        if cost is not None:
            from app.domains.catalog.services.price_rounding import round_to_pretty_price

            margin = Decimal(str(product.margin or 0))
            raw_sale_price = float(cost * (1 + margin))
            sale_price = round_to_pretty_price(raw_sale_price)
            price_str = str(
                Decimal(str(sale_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )

    # Obter nome da marca se o produto tiver marca
    brand_name: str | None = None
    if product.id_brand:
        brand = brand_r.get(product.id_brand)
        if brand:
            brand_name = brand.name

    # Construir payload para PrestaShop
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

    # Chamar API do PrestaShop
    result = ps_client.create_product(payload)

    # Atualizar produto com ID do PrestaShop
    ps_product_id = result.get("id_product")
    if ps_product_id:
        product.id_ecommerce = int(ps_product_id)
        db.add(product)
        db.flush()

        # Atualizar active offer com dados da oferta importada
        if best_offer:
            active_offer_w.upsert(
                id_product=id_product,
                id_supplier=best_offer.get("id_supplier"),
                id_supplier_item=best_offer.get("id") or best_offer.get("id_supplier_item"),
                unit_cost=float(cost) if cost is not None else None,
                unit_price_sent=float(price_str) if price_str else None,
                stock_sent=stock,
            )

        # Commit de todas as alterações
        uow.commit()

        # Registar no audit log
        AuditService(db).log_product_import(
            product_id=id_product,
            product_name=product.name,
            id_ecommerce=ps_product_id,
        )

    return ProductImportOut(
        id_product=id_product,
        id_ecommerce=ps_product_id,
        success=True,
    )
