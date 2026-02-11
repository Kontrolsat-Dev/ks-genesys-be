# app/domains/catalog/services/best_offer_service.py
"""
Serviço centralizado para seleção da melhor oferta.

- find_best_offer_from_dicts: para dicts raw da BD (aplica desconto)
- find_best_offer_from_schemas: para OfferOut (preço já descontado pelo mapper)
"""

from decimal import Decimal
from typing import Any

from app.schemas.products import OfferOut


def find_best_offer_from_dicts(
    offers: list[dict[str, Any]],
    require_stock: bool = True,
    fallback_no_stock: bool = True,
) -> dict[str, Any] | None:
    """
    Encontra a oferta com menor custo efetivo de uma lista de dicts.
    Aplica o desconto do fornecedor usando o campo supplier_discount do dict.

    Args:
        offers: Lista de ofertas como dicts (vindos da query com supplier_discount)
        require_stock: Se True, tenta primeiro ofertas com stock
        fallback_no_stock: Se True e não houver ofertas com stock, usa sem stock

    Returns:
        A oferta com menor custo efetivo, ou None se não existir
    """
    if not offers:
        return None

    from app.domains.catalog.services.price_service import PriceService

    def effective_cost(o: dict) -> Decimal:
        """Calcula preço × (1 - desconto) usando supplier_discount do dict."""
        try:
            return PriceService.calculate_effective_cost(
                o["price"], o.get("supplier_discount") or 0
            )
        except (TypeError, ValueError, KeyError):
            return Decimal("999999")

    def filter_candidates(check_stock: bool) -> list[dict]:
        candidates = []
        for o in offers:
            if check_stock:
                stock = o.get("stock")
                if stock is None or stock <= 0:
                    continue
            if o.get("price") is None:
                continue
            candidates.append(o)
        return candidates

    # Primeiro: tentar com stock
    if require_stock:
        candidates = filter_candidates(check_stock=True)
        if candidates:
            return min(candidates, key=effective_cost)
        # Fallback: sem stock
        if fallback_no_stock:
            candidates = filter_candidates(check_stock=False)
            if candidates:
                return min(candidates, key=effective_cost)
        return None
    else:
        # Não requer stock - buscar todas
        candidates = filter_candidates(check_stock=False)
        if candidates:
            return min(candidates, key=effective_cost)
        return None


def find_best_offer_from_schemas(
    offers: list[OfferOut],
    require_stock: bool = True,
    fallback_no_stock: bool = True,
) -> OfferOut | None:
    """
    Encontra a oferta com menor preço de uma lista de OfferOut.
    O preço já vem com desconto aplicado do mapper.

    Args:
        offers: Lista de ofertas como OfferOut schemas (preço já descontado)
        require_stock: Se True, tenta primeiro ofertas com stock
        fallback_no_stock: Se True e não houver ofertas com stock, usa sem stock

    Returns:
        A oferta com menor preço, ou None se não existir
    """
    if not offers:
        return None

    def get_price(o: OfferOut) -> float:
        try:
            return float(o.price) if o.price else float("inf")
        except (TypeError, ValueError):
            return float("inf")

    def filter_candidates(check_stock: bool) -> list[OfferOut]:
        candidates = []
        for o in offers:
            if check_stock:
                if o.stock is None or o.stock <= 0:
                    continue
            if o.price is None:
                continue
            candidates.append(o)
        return candidates

    # Primeiro: tentar com stock
    if require_stock:
        candidates = filter_candidates(check_stock=True)
        if candidates:
            return min(candidates, key=get_price)
        # Fallback: sem stock
        if fallback_no_stock:
            candidates = filter_candidates(check_stock=False)
            if candidates:
                return min(candidates, key=get_price)
        return None
    else:
        # Não requer stock - buscar todas
        candidates = filter_candidates(check_stock=False)
        if candidates:
            return min(candidates, key=get_price)
        return None
