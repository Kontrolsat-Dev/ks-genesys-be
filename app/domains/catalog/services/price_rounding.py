# app/domains/catalog/services/price_rounding.py
"""
Serviço de arredondamento de preços para valores "bonitos" (.40 / .90).
O arredondamento é aplicado ao preço COM IVA, depois convertido para SEM IVA.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.domains.config.services.config_service import config_service

# Default fallback se config não estiver disponível
_DEFAULT_VAT_RATE = Decimal("1.23")


def get_vat_rate() -> Decimal:
    """Obtém a taxa de IVA da configuração."""
    return Decimal(str(config_service.get_float("vat_rate", default=1.23)))


def round_to_pretty_price(
    price_without_vat: float | Decimal, vat_rate: Decimal | None = None
) -> float:
    """
    Arredonda preço para terminar em .40 ou .90 (com IVA).

    Args:
        price_without_vat: Preço sem IVA (custo * (1 + margem))
        vat_rate: Taxa de IVA (default 1.23 = 23%)

    Returns:
        Preço sem IVA que, quando aplicado IVA, termina em .40 ou .90

    Exemplo:
        >>> round_to_pretty_price(2.15)  # 2.15 * 1.23 = 2.64 → 2.90 → 2.36
        2.36
    """
    price = Decimal(str(price_without_vat))

    # Usar VAT rate da config se não especificado
    if vat_rate is None:
        vat_rate = get_vat_rate()

    # Calcular preço com IVA
    price_with_vat = price * vat_rate

    # Arredondar para .40 ou .90
    rounded_with_vat = _round_to_40_or_90(price_with_vat)

    # Converter de volta para sem IVA
    final_price = rounded_with_vat / vat_rate

    # Arredondar para 2 casas decimais
    return float(final_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _round_to_40_or_90(price_with_vat: Decimal) -> Decimal:
    """
    Arredonda preço com IVA para o .40 ou .90 mais próximo.

    Regra:
    - cents <= 0.15 → vai para euros anteriores + 0.90 (arredonda para baixo e adiciona .90)
    - cents <= 0.65 → vai para .40
    - cents > 0.65  → vai para .90

    Exemplos (com IVA):
        2.12 → 1.90  (estava mais perto de 1.90 que de 2.40)
        2.30 → 2.40  (estava mais perto de 2.40)
        2.63 → 2.90  (estava mais perto de 2.90)
        2.83 → 2.90  (estava mais perto de 2.90)
        3.10 → 2.90  (estava mais perto de 2.90 que de 3.40)
    """
    euros = int(price_with_vat)
    cents = price_with_vat - euros

    if cents <= Decimal("0.15"):
        # Mais perto do .90 do euro anterior
        if euros > 0:
            return Decimal(f"{euros - 1}.90")
        else:
            return Decimal("0.40")
    elif cents <= Decimal("0.65"):
        # Mais perto de .40
        return Decimal(f"{euros}.40")
    else:
        # Mais perto de .90
        return Decimal(f"{euros}.90")


def calculate_pretty_price_preview(
    cost: float,
    margin: float,
    vat_rate: Decimal | None = None,
) -> dict:
    """
    Calcula preview de preço com arredondamento para o frontend.

    Returns:
        dict com:
        - cost: custo original
        - margin: margem em decimal (0.25 = 25%)
        - raw_price: preço bruto sem IVA
        - raw_price_vat: preço bruto com IVA
        - rounded_vat: preço arredondado com IVA (.40/.90)
        - final_price: preço final sem IVA (para PS)
    """
    cost_dec = Decimal(str(cost))
    margin_dec = Decimal(str(margin))

    # Usar VAT rate da config se não especificado
    if vat_rate is None:
        vat_rate = get_vat_rate()

    raw_price = cost_dec * (1 + margin_dec)
    raw_price_vat = raw_price * vat_rate

    # Arredondar
    rounded_vat = _round_to_40_or_90(raw_price_vat)
    final_price = rounded_vat / vat_rate

    return {
        "cost": float(cost_dec.quantize(Decimal("0.01"))),
        "margin": float(margin_dec),
        "raw_price": float(raw_price.quantize(Decimal("0.01"))),
        "raw_price_vat": float(raw_price_vat.quantize(Decimal("0.01"))),
        "rounded_vat": float(rounded_vat),
        "final_price": float(final_price.quantize(Decimal("0.01"))),
    }
