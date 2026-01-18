# app/schemas/prestashop.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# -------- Categories --------


class PrestashopCategoryNode(BaseModel):
    """
    Nó de categoria tal como vem do Prestashop.
    Aceita campos extra (se o módulo adicionar mais coisas no futuro).
    """

    model_config = ConfigDict(extra="ignore")

    id_category: int
    id_parent: int
    name: str
    level_depth: int
    active: bool
    position: int
    children: list[PrestashopCategoryNode] = Field(default_factory=list)


PrestashopCategoryNode.model_rebuild()


class PrestashopCategoriesOut(BaseModel):
    """
    Envelope completo devolvido pelo endpoint /prestashop/categories.
    É basicamente o payload do r_genesys/getcategories validado.
    """

    model_config = ConfigDict(extra="ignore")
    root_category_id: int
    language_id: int
    shop_id: int
    categories: list[PrestashopCategoryNode]


# -------- Brands --------


class PrestashopBrand(BaseModel):
    id_brand: int
    name: str
    date_add: str
    date_upd: str
    description: str | None
    link_rewrite: str | None
    meta_title: str | None
    meta_description: str | None
    meta_keywords: str | None


class PrestashopBrandsOut(BaseModel):
    """
    Envelope completo devolvido pelo endpoint /prestashop/brands.
    Payload do r_genesys/getbrands validado.
    """

    model_config = ConfigDict(extra="ignore")
    language_id: int
    brands: list[PrestashopBrand]


# -------- ORDERS --------


class OrderCustomer(BaseModel):
    """
    Cliente
    """

    id_customer: int
    email: str
    firstname: str
    lastname: str


class OrderCarrier(BaseModel):
    id_carrier: int
    name: str


# Shipping and billing address same schema
class OrderAddress(BaseModel):
    id_address: int
    firstname: str
    lastname: str
    company: str | None = None
    address1: str | None = None
    address2: str | None = None
    postcode: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    phone: str | None = None
    phone_mobile: str | None = None
    vat_number: str | None = None
    dni: str | None = None


class OrderDropshippingLine(BaseModel):
    id_order_detail: int
    id_product: int
    id_product_attribute: int
    product_name: str
    product_reference: str
    product_supplier_reference: str
    product_ean13: str
    product_upc_order_detail: str
    product_upc_current: str
    qty: int
    unit_price_tax_excl: float
    unit_price_tax_incl: float
    total_price_tax_excl: float
    total_price_tax_incl: float


class Order(BaseModel):
    id_order: int
    reference: str
    date_add: str
    date_upd: str
    current_state: int
    payment: str
    total_paid_tax_incl: float
    total_paid_tax_excl: float
    total_shipping_tax_incl: float
    total_shipping_tax_excl: float
    customer: OrderCustomer
    carrier: OrderCarrier
    delivery_address: OrderAddress
    invoice_address: OrderAddress
    dropshipping_lines: list[OrderDropshippingLine]


class PrestashopOrdersDropshippingOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    success: bool
    page: int
    page_size: int
    items: list[Order]


# -------- GET ORDER DETAIL (JIT) --------


class OrderDetailCustomer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    email: str | None = None
    group: int | None = None


class OrderDetailCountry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    iso_code: str
    name: str


class OrderDetailAddressJIT(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    company: str | None = None
    vat_number: str | None = None
    address1: str | None = None
    address2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    mobile: str | None = None
    country: OrderDetailCountry | None = None


class OrderDetailStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    color: str


class OrderDetailService(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cart_service_id: int
    id_service_item: int
    type: str
    name: str
    cost: float
    sage_reference: str | None = None
    quantity: int
    total_cost: float


class OrderDetailProduct(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_id: int | str
    product_reference: str | None = None
    product_name: str
    product_quantity: int | str
    product_price: float
    product_ecotax: float | None = None
    product_ean13: str | None = None
    product_weight: float | None = None
    product_category: str | None = None
    product_manufacturer: str | None = None
    product_upc: int | str | None = None
    product_image: str | None = None
    services: list[OrderDetailService] | None = None

    @field_validator("product_upc", mode="before")
    def parse_upc(cls, v: Any) -> int:
        if not v:
            return 0
        try:
            return int(v)
        except ValueError:
            return 0


class OrderDetailShipping(BaseModel):
    model_config = ConfigDict(extra="ignore")
    carrier: str | None = None
    price: float | None = None
    weight: float | None = None


class PrestashopOrderDetailOut(BaseModel):
    """
    Detalhes de uma encomenda obtidos via /getorder (JIT).
    """

    model_config = ConfigDict(extra="ignore")
    id: int
    reference: str
    date_add: str | None = None
    payment: str
    discount: float | None = 0
    total: float
    total_products: float | None = 0
    total_wrapping: float | None = 0
    payment_tax: float | None = 0
    customer: OrderDetailCustomer
    delivery: OrderDetailAddressJIT
    invoice: OrderDetailAddressJIT
    shipping: OrderDetailShipping | None = None
    status: OrderDetailStatus
    products: list[OrderDetailProduct] = Field(default_factory=list)
    notes: str | None = None
    latest_message: str | None = None
    hfrio: bool | None = False
