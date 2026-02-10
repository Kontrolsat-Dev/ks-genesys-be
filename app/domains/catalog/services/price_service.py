# app/domains/catalog/services/price_service.py
"""
Serviço centralizado para cálculo de preço de venda (manual ou worker).

Formula base:
    preco_venda = (custo_liquido × (1 + margem)) + ecotax + extra_fees

- custo_liquido = custo_bruto × (1 - supplier_discount)
- ecotax só é aplicada se o fornecedor NÃO for PT; extra_fees aplicam sempre.
- O arredondamento final segue a regra .40/.90 com IVA via round_to_pretty_price.

Retorna sempre um breakdown com os componentes usados para facilitar debug.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.domains.catalog.services.price_rounding import round_to_pretty_price


@dataclass
class PriceBreakdown:
    sale_price: float
    raw_sale_price: float
    discounted_cost: float
    margin: float
    ecotax: float
    extra_fees: float


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def compute_sale_price(
    *,
    product,
    category=None,
    supplier_country: str | None,
    cost: Any,
    supplier_discount: Any = 0,
) -> PriceBreakdown | None:
    """
    Calcula o preço de venda para PrestaShop (ou active_offer) aplicando
    margem, ecotax e extra_fees de forma consistente para API e worker.

    Args:
        product: entidade Product (precisa de margin/ecotax/extra_fees/id_category)
        category: entidade Category opcional (para defaults de ecotax/extra_fees)
        supplier_country: país do fornecedor (para regra da ecotax)
        cost: custo bruto recebido do supplier_item
        supplier_discount: desconto percentagem (0.05 = 5%)
    """

    cost_dec = _to_decimal(cost, default="-1")
    if cost_dec <= 0:
        return None

    discount_dec = _to_decimal(supplier_discount)
    discounted_cost = cost_dec * (1 - discount_dec)

    margin_dec = _to_decimal(getattr(product, "margin", 0))

    # Ecotax depende do país do fornecedor; extra_fees aplica SEMPRE
    is_pt = (supplier_country or "").upper() == "PT"

    # Herança: se product.ecotax for None -> usa default da categoria (permite override para 0)
    p_ecotax = getattr(product, "ecotax", None)
    if p_ecotax is None and category is not None:
        ecotax_val = _to_decimal(getattr(category, "default_ecotax", 0))
    else:
        ecotax_val = _to_decimal(p_ecotax)

    if is_pt:
        ecotax_val = Decimal("0")

    # Herança: se product.extra_fees for None -> usa default da categoria (permite override para 0)
    p_extra_fees = getattr(product, "extra_fees", None)
    if p_extra_fees is None and category is not None:
        extra_fees_val = _to_decimal(getattr(category, "default_extra_fees", 0))
    else:
        extra_fees_val = _to_decimal(p_extra_fees)
    # extra_fees nunca é removido para PT

    raw_sale_price = discounted_cost * (1 + margin_dec) + ecotax_val + extra_fees_val

    sale_price = round_to_pretty_price(float(raw_sale_price))

    # Quantizar para 2 casas para payloads/armazenamento previsíveis
    sale_price_q = float(_to_decimal(sale_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return PriceBreakdown(
        sale_price=sale_price_q,
        raw_sale_price=float(raw_sale_price),
        discounted_cost=float(discounted_cost),
        margin=float(margin_dec),
        ecotax=float(ecotax_val),
        extra_fees=float(extra_fees_val),
    )
