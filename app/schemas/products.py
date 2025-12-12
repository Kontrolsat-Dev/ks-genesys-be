from __future__ import annotations

from decimal import Decimal
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class OfferOut(BaseModel):
    id_supplier: int
    supplier_name: str | None = None
    supplier_image: str | None = None
    id_feed: int
    sku: str
    price: str | None = None
    stock: int | None = None
    id_last_seen_run: int | None = None
    updated_at: datetime | None = None


class ProductOut(BaseModel):
    """
    Produto base: NUNCA tem offers nem best_offer.
    É usado no detalhe dentro de ProductDetailOut.product.
    """

    id: int
    gtin: str | None = None
    id_ecommerce: int | None = None
    id_brand: int | None = None
    brand_name: str | None = None
    id_category: int | None = None
    category_name: str | None = None
    partnumber: str | None = None
    name: str | None = None
    margin: float | None = None
    description: str | None = None
    image_url: str | None = None
    weight_str: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductListItemOut(ProductOut):
    """
    Produto específico para listagens: tem sempre os campos de produto base
    + as ofertas agregadas + best_offer.
    """

    offers: list[OfferOut] = Field(default_factory=list)
    best_offer: OfferOut | None = None
    active_offer: OfferOut | None = None


class ProductListOut(BaseModel):
    items: list[ProductListItemOut]
    total: int
    page: int
    page_size: int


# --------------------------


class ProductMetaOut(BaseModel):
    name: str
    value: str
    created_at: datetime


class ProductEventOut(BaseModel):
    model_config = ConfigDict(extra="forbid")  # apanha campos errados cedo
    created_at: datetime
    reason: str
    price: str | None = None
    stock: int | None = None
    id_supplier: int | None = None
    supplier_name: str | None = None
    id_feed_run: int | None = None


class SeriesPointOut(BaseModel):
    date: datetime  # dia (00:00) ou timestamp consolidado do dia
    price: str | None = None
    stock: int | None = None


class ProductStatsOut(BaseModel):
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    suppliers_count: int = 0
    offers_in_stock: int = 0
    last_change_at: datetime | None = None


class ProductDetailOut(BaseModel):
    """
    Detalhe completo de produto:
    - product: info base
    - offers/best_offer: SEMPRE aqui, nunca em product.*
    """

    product: ProductOut
    meta: list[ProductMetaOut] = Field(default_factory=list)
    offers: list[OfferOut] = Field(default_factory=list)
    best_offer: OfferOut | None = None
    active_offer: OfferOut | None = None
    stats: ProductStatsOut
    events: list[ProductEventOut] | None = None
    series_daily: list[SeriesPointOut] | None = None


# --------------------------


class ProductMarginUpdate(BaseModel):
    """
    Payload para atualização da margem de um produto.

    A margem é um multiplicador usado para calcular o preço de venda
    a partir do custo: unit_price_sent = unit_cost * (1 + margin).
    """

    margin: float = Field(..., ge=0.0)


class ProductImportIn(BaseModel):
    """Payload para importar produto para PrestaShop."""

    id_ps_category: int = Field(..., description="ID da categoria no PrestaShop")


class ProductImportOut(BaseModel):
    """Response após importar produto."""

    id_product: int
    id_ecommerce: int | None
    success: bool


# --------------------------


class ProductPriceChangeOut(BaseModel):
    id_product: int
    name: str | None
    brand_name: str | None
    category_name: str | None

    current_price: Decimal
    previous_price: Decimal
    delta_abs: Decimal
    delta_pct: Decimal
    direction: Literal["up", "down", "both"]

    updated_at: datetime


class ProductPriceChangeListOut(BaseModel):
    items: list[ProductPriceChangeOut]
    total: int
    page: int
    page_size: int


# ----------- FACETES ---------------
class ProductFacetsOut(BaseModel):
    """
    Facets para filtros de produtos.
    Cada lista contem **IDs** válidos para a dimensão correspondente,
    já respeitando os filtros atuais.
    """

    brand_ids: list[int] = Field(default_factory=list)
    category_ids: list[int] = Field(default_factory=list)
    supplier_ids: list[int] = Field(default_factory=list)
