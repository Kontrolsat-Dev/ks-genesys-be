# app/schemas/prestashop.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
