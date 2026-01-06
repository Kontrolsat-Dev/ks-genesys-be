"""
Pydantic schemas para encomendas Dropshipping.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.models.orders_dropshipping import OrderStatus


# --------------------- Morada ---------------------


class AddressOut(BaseModel):
    """Morada (entrega ou faturação)."""

    model_config = ConfigDict(extra="ignore")

    id_address: int | None = None
    firstname: str | None = None
    lastname: str | None = None
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


# --------------------- Linha de Encomenda ---------------------


class DropshippingOrderLineOut(BaseModel):
    """Linha de encomenda dropshipping."""

    id: int
    id_ps_order_detail: int
    id_ps_product: int

    product_name: str
    product_reference: str | None
    product_ean: str | None
    product_supplier_reference: str | None

    qty: int
    unit_price_tax_excl: Decimal
    unit_price_tax_incl: Decimal
    total_price_tax_excl: Decimal
    total_price_tax_incl: Decimal

    status: OrderStatus

    # Match com Genesys
    id_product: int | None = None
    product_matched: bool = Field(default=False)

    # Fornecedor selecionado
    id_supplier: int | None = None
    supplier_name: str | None = None
    supplier_cost: Decimal | None = None

    # Pedido ao fornecedor
    id_supplier_order: int | None = None


# --------------------- Ofertas de Fornecedor ---------------------


class SupplierOfferOut(BaseModel):
    """Oferta de um fornecedor para um produto."""

    id_supplier: int
    supplier_name: str | None = None
    supplier_image: str | None = None
    price: Decimal
    stock: int


class PendingLineWithOffersOut(BaseModel):
    """Linha pendente com ofertas disponíveis de fornecedores."""

    id: int
    id_order: int
    id_ps_order: int
    order_reference: str
    ps_state_name: str | None = None
    customer_name: str

    id_ps_order_detail: int
    id_ps_product: int

    product_name: str
    product_reference: str | None
    product_ean: str | None
    product_supplier_reference: str | None

    qty: int
    unit_price_tax_excl: Decimal
    unit_price_tax_incl: Decimal

    id_product: int | None = None
    status: OrderStatus

    # Ofertas disponíveis
    offers: list[SupplierOfferOut] = Field(default_factory=list)


class PendingLinesListOut(BaseModel):
    """Lista de linhas pendentes com ofertas."""

    items: list[PendingLineWithOffersOut]
    total: int


# --------------------- Encomenda ---------------------


class DropshippingOrderOut(BaseModel):
    """Encomenda dropshipping do PrestaShop."""

    id: int
    id_ps_order: int
    reference: str
    ps_state_id: int
    ps_state_name: str | None

    customer_email: str
    customer_firstname: str
    customer_lastname: str
    customer_name: str = Field(default="")

    delivery_address: AddressOut | None = None
    invoice_address: AddressOut | None = None

    carrier_name: str | None
    payment_method: str | None

    total_paid_tax_incl: Decimal
    total_paid_tax_excl: Decimal
    total_shipping_tax_incl: Decimal
    total_shipping_tax_excl: Decimal

    ps_date_add: datetime
    ps_date_upd: datetime
    created_at: datetime

    lines: list[DropshippingOrderLineOut] = Field(default_factory=list)
    lines_count: int = 0
    lines_pending: int = 0
    lines_matched: int = 0


class DropshippingOrderListOut(BaseModel):
    """Lista paginada de encomendas."""

    items: list[DropshippingOrderOut]
    total: int
    page: int
    page_size: int


# --------------------- Pedido ao Fornecedor ---------------------


class SupplierOrderLineOut(BaseModel):
    """Linha dentro de um pedido ao fornecedor."""

    id: int
    id_order: int  # FK da encomenda PS
    order_reference: str
    product_name: str
    product_ean: str | None
    qty: int
    supplier_cost: Decimal | None


class SupplierOrderOut(BaseModel):
    """Pedido ao fornecedor."""

    id: int
    id_supplier: int
    supplier_name: str | None = None

    status: OrderStatus
    total_cost: Decimal
    total_items: int

    sage_order_id: str | None
    clickup_task_id: str | None

    created_at: datetime
    ordered_at: datetime | None
    completed_at: datetime | None

    lines: list[SupplierOrderLineOut] = Field(default_factory=list)


class SupplierOrderListOut(BaseModel):
    """Lista paginada de pedidos a fornecedores."""

    items: list[SupplierOrderOut]
    total: int
    page: int
    page_size: int


# --------------------- Acções ---------------------


class SelectSupplierIn(BaseModel):
    """Payload para selecionar fornecedor para uma linha."""

    id_supplier: int
    supplier_cost: Decimal | None = None


class ConfirmSupplierOrderIn(BaseModel):
    """Payload para confirmar pedido ao fornecedor."""

    notes: str | None = None
