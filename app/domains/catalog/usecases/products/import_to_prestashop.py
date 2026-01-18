# app/domains/catalog/usecases/products/import_to_prestashop.py
"""
UseCase para importar um produto para o PrestaShop.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
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
    3. Verificar país do fornecedor - taxas só aplicam se país != PT
    4. Aplicar desconto do fornecedor ao custo (se existir)
    5. Calcular preço: (custo_descontado × (1 + margem)) + ecotax + extra_fees
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
        raise InvalidArgument(
            f"Produto {id_product} já importado (PS ID: {product.id_ecommerce})"
        )

    # Obter ofertas e encontrar a melhor (menor custo efetivo)
    from app.domains.catalog.services.best_offer_service import find_best_offer_from_dicts

    offers = uow.supplier_items.list_offers_for_product(
        id_product, only_in_stock=False)

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
    category = uow.categories.get(
        product.id_category) if product.id_category else None

    # Verificar país do fornecedor da melhor oferta
    # Só aplicamos taxas (ecotax, extra_fees) se fornecedor NÃO é de Portugal
    supplier_country: str | None = None
    if best_offer and best_offer.get("id_supplier"):
        supplier = uow.suppliers.get(best_offer["id_supplier"])
        if supplier:
            supplier_country = supplier.country

    # Taxas só se aplicam se país != PT (ou país não definido trata como não-PT)
    apply_taxes = supplier_country is None or supplier_country.upper() != "PT"

    # Determinar ecotax e extra_fees (produto tem precedência, se não usa default da categoria)
    if apply_taxes:
        ecotax = (
            product.ecotax if product.ecotax > 0 else (
                category.default_ecotax if category else 0)
        )
        extra_fees = (
            product.extra_fees
            if product.extra_fees > 0
            else (category.default_extra_fees if category else 0)
        )
    else:
        # Fornecedor português - não aplicar taxas adicionais
        ecotax = 0
        extra_fees = 0

    # Calcular preço: (custo × margem) + ecotax + taxas adicionais
    price_str: str | None = None
    stock: int | None = None
    cost: Decimal | None = None

    if best_offer:
        cost = Decimal(best_offer["price"]) if best_offer.get(
            "price") else None
        stock = best_offer.get("stock") or 0

        if cost is not None:
            from app.domains.catalog.services.price_rounding import (
                round_to_pretty_price,
            )

            # Aplicar desconto do fornecedor ao custo (se existir)
            # custo_descontado = custo × (1 - desconto)
            supplier_discount = Decimal(
                str(best_offer.get("supplier_discount") or 0))
            discounted_cost = cost * (1 - supplier_discount)

            # Preço = (custo_descontado × (1 + margem)) + ecotax + extra_fees
            margin = Decimal(str(product.margin or 0))
            price_with_margin = discounted_cost * (1 + margin)
            raw_sale_price = float(
                price_with_margin +
                Decimal(str(ecotax)) + Decimal(str(extra_fees))
            )
            sale_price = round_to_pretty_price(raw_sale_price)
            price_str = str(
                Decimal(str(sale_price)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP)
            )

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
        "ecotax": str(ecotax) if ecotax else None,
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
                id_supplier_item=best_offer.get(
                    "id") or best_offer.get("id_supplier_item"),
                unit_cost=float(cost) if cost is not None else None,
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
