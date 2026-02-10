# app/domains/catalog/usecases/products/import_to_prestashop.py
"""
UseCase para importar um produto para o PrestaShop.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
from app.core.errors import NotFound, InvalidArgument
from app.domains.catalog.services.best_offer_service import find_best_offer_from_dicts
from app.domains.catalog.services.price_service import compute_sale_price
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
    3. Verificar país do fornecedor - ecotax só aplica se país != PT (extra_fees aplicam sempre)
    4. Aplicar desconto do fornecedor ao custo (se existir)
    5. Calcular preço via PriceService: (custo_descontado × (1 + margem)) + ecotax + extra_fees + arredondamento
    6. Construir payload para PrestaShop
    7. Chamar API do PrestaShop
    8. Atualizar produto com id_ecommerce e active_offer

    Returns:
        ProductImportOut schema
    """
    # Obter produto
    product = uow.products.get(id_product)
    if not product:
        raise NotFound(f"Produto {id_product} não encontrado")

    if product.id_ecommerce:
        raise InvalidArgument(f"Produto {id_product} já importado (PS ID: {product.id_ecommerce})")

    # Obter ofertas e encontrar a melhor (menor custo efetivo)
    offers = uow.supplier_items.list_offers_for_product(id_product, only_in_stock=False)

    # Encontrar melhor oferta (sem exigir stock para import)
    # O desconto vem do campo supplier_discount no dict
    best_offer = find_best_offer_from_dicts(offers, require_stock=False)

    # Obter nome da marca se o produto tiver marca
    brand_name: str | None = None
    if product.id_brand:
        brand = uow.brands.get(product.id_brand)
        if brand:
            brand_name = brand.name

    # Obter categoria para herança de taxas default
    category = uow.categories.get(product.id_category) if product.id_category else None

    supplier_country: str | None = None
    supplier = None
    if best_offer and best_offer.get("id_supplier"):
        supplier = uow.suppliers.get(best_offer["id_supplier"])
        if supplier:
            supplier_country = supplier.country

    # Calcular preço via serviço centralizado (aplica margens, ecotax, extra_fees)
    price_str: str | None = None
    stock: int | None = None
    ecotax_used: float | None = None
    raw_cost: Decimal | None = None

    if best_offer:
        stock = best_offer.get("stock") or 0
        raw_cost = Decimal(str(best_offer.get("price"))) if best_offer.get("price") else None
        calc = compute_sale_price(
            product=product,
            category=category,
            supplier_country=supplier_country,
            cost=best_offer.get("price"),
            supplier_discount=best_offer.get("supplier_discount"),
        )
        if calc:
            price_str = str(
                Decimal(str(calc.sale_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
            ecotax_used = calc.ecotax

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
        "ecotax": str(ecotax_used) if ecotax_used else None,
    }

    # Chamar API do PrestaShop
    result = ps_client.create_product(payload)

    # Atualizar produto com ID do PrestaShop
    ps_product_id = result.get("id_product")
    if ps_product_id:
        product.id_ecommerce = int(ps_product_id)
        uow.db.add(product)
        uow.db.flush()

        # Atualizar active offer com dados da oferta importada
        if best_offer:
            uow.active_offers_w.upsert(
                id_product=id_product,
                id_supplier=best_offer.get("id_supplier"),
                id_supplier_item=best_offer.get("id") or best_offer.get("id_supplier_item"),
                unit_cost=float(raw_cost) if raw_cost is not None else None,
                unit_price_sent=float(price_str) if price_str else None,
                stock_sent=stock,
            )

        # Commit de todas as alterações
        uow.commit()

        # Registar no audit log
        AuditService(uow.db).log_product_import(
            product_id=id_product,
            product_name=product.name,
            id_ecommerce=ps_product_id,
        )

    return ProductImportOut(
        id_product=id_product,
        id_ecommerce=ps_product_id,
        success=True,
    )
