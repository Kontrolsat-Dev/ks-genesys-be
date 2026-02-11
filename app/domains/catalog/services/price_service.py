# app/domains/catalog/services/price_service.py
from __future__ import annotations

from decimal import Decimal

from app.domains.config.services.config_service import config_service


class PriceService:
    @staticmethod
    def get_vat_rate() -> Decimal:
        """Obtém a taxa de IVA da configuração."""
        return Decimal(str(config_service.get_float("vat_rate", default=1.23)))

    @staticmethod
    def calculate_effective_cost(price: float | Decimal, discount: float | Decimal) -> Decimal:
        """
        Calcula o custo efetivo: price * (1 - discount).
        """
        p = Decimal(str(price))
        d = Decimal(str(discount or 0))
        return p * (1 - d)

    @staticmethod
    def calculate_price_breakdown(
        cost: float | Decimal,
        margin: float | Decimal,
        ecotax: float | Decimal = 0,
        extra_fees: float | Decimal = 0,
        vat_rate: Decimal | None = None,
    ) -> dict:
        """
        Calcula o preço final e todos os passos intermédios.

        Regra:
        1. Base = Custo * (1 + Margem)
        2. Bruto sem IVA = Base + Ecotax + Extra Fees
        3. Bruto com IVA = Bruto sem IVA * IVA
        4. Arredondamento = (Bruto com IVA) -> .40 ou .90
        5. Final sem IVA = Arredondado / IVA
        """
        cost_d = Decimal(str(cost))
        margin_d = Decimal(str(margin))
        ecotax_d = Decimal(str(ecotax or 0))
        extra_fees_d = Decimal(str(extra_fees or 0))

        if vat_rate is None:
            vat_rate = PriceService.get_vat_rate()

        # 1. Base (Custo + Margem)
        base_price = cost_d * (1 + margin_d)

        # 2. Bruto sem IVA (Soma taxas)
        # NOTA: Margem não incide sobre ecotax nem extra_fees (são pass-through)
        gross_price_no_vat = base_price + ecotax_d + extra_fees_d

        # 3. Bruto com IVA
        gross_price_vat = gross_price_no_vat * vat_rate

        # 4. Arredondamento
        final_price_vat = PriceService._round_to_40_or_90(gross_price_vat)

        # 5. Final sem IVA (Valor a enviar para o PrestaShop)
        final_price_no_vat = final_price_vat / vat_rate

        return {
            "cost": float(cost_d),
            "margin_pct": float(margin_d),
            "margin_value": float(cost_d * margin_d),
            "ecotax": float(ecotax_d),
            "extra_fees": float(extra_fees_d),
            "vat_rate": float(vat_rate),
            "base_price": float(base_price.quantize(Decimal("0.01"))),
            "gross_price_no_vat": float(gross_price_no_vat.quantize(Decimal("0.01"))),
            "gross_price_vat": float(gross_price_vat.quantize(Decimal("0.01"))),
            "final_price_vat": float(final_price_vat),
            # Mais precisão para o PS
            "final_price_no_vat": float(final_price_no_vat.quantize(Decimal("0.000001"))),
        }

    @staticmethod
    def _round_to_40_or_90(price_with_vat: Decimal) -> Decimal:
        """
        Arredonda preço com IVA para o .40 ou .90 mais próximo.
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

    @staticmethod
    def resolve_pricing_params(product, category=None, supplier=None) -> dict[str, float]:
        """
        Centraliza a lógica de decisão de preços/taxas (Herança e Isenções).

        Regras:
        1. Margem: Produto > Categoria > 0
        2. Ecotax: (Se fornecedor PT -> 0) SENÃO (Produto > Categoria > 0)
        3. Extra Fees: Produto > Categoria > 0
        """

        # 1. Margem
        margin = 0.0
        if product.margin is not None and product.margin > 0:
            margin = float(product.margin)
        elif category and getattr(category, "margin", None) is not None:
            # Nota: Category pode vir como dict ou object, ou ter campo 'margin' diferente.
            # Assumimos object standard. Se for dict, tratar caller.
            try:
                margin = float(category.margin)
            except (TypeError, ValueError):
                margin = 0.0

        # 2. Ecotax
        ecotax = 0.0
        # Isenção fornecedor PT
        supplier_country = getattr(supplier, "country", "") or ""
        if supplier_country.strip().upper() == "PT":
            ecotax = 0.0
        else:
            # Herança
            if product.ecotax is not None:
                ecotax = float(product.ecotax)
            elif category:
                # Tenta 'default_ecotax' (nome na DB) ou 'category_ecotax' (nome no join)
                cat_eco = getattr(category, "default_ecotax", None)
                # Se category for dict vindo de read model
                if cat_eco is None and isinstance(category, dict):
                    cat_eco = category.get("default_ecotax")

                if cat_eco is not None:
                    ecotax = float(cat_eco)

        # 3. Extra Fees
        extra_fees = 0.0
        if product.extra_fees is not None:
            extra_fees = float(product.extra_fees)
        elif category:
            cat_fees = getattr(category, "default_extra_fees", None)
            if cat_fees is None and isinstance(category, dict):
                cat_fees = category.get("default_extra_fees")

            if cat_fees is not None:
                extra_fees = float(cat_fees)

        return {"margin": margin, "ecotax": ecotax, "extra_fees": extra_fees}
