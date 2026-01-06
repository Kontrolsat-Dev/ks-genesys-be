"""
Modelos SQLAlchemy para sistema de encomendas Dropshipping.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.supplier import Supplier


# --------------------- ENUMS ---------------------


class OrderStatus(str, Enum):
    """
    Estado unificado para linhas e pedidos a fornecedores.
    Quando um SupplierOrder muda de estado, todas as linhas associadas mudam também.
    """

    PENDING = "pending"  # Importada, aguarda processamento
    ORDERED = "ordered"  # Encomendada ao fornecedor
    SHIPPED_STORE = "shipped_store"  # Enviado de stock loja
    COMPLETED = "completed"  # Concluída
    CANCELLED = "cancelled"  # Cancelada
    ERROR = "error"  # Erro no processamento


# --------------------- MODELOS ---------------------


class DropshippingOrder(Base):
    """
    Encomenda do PrestaShop.
    Contém os dados do cliente e linhas de produtos.
    """

    __tablename__ = "dropshipping_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificação PS
    id_ps_order: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Cliente
    customer_email: Mapped[str] = mapped_column(String(250), nullable=False)
    customer_firstname: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_lastname: Mapped[str] = mapped_column(String(100), nullable=False)

    # Moradas (JSON)
    delivery_address: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    invoice_address: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Transportadora
    carrier_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Pagamento
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Valores
    total_paid_tax_incl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_paid_tax_excl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_shipping_tax_incl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_shipping_tax_excl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # Datas PS
    ps_date_add: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ps_date_upd: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Timestamps Genesys
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=utcnow, nullable=True)

    # Notas/erros
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relações
    lines: Mapped[list[DropshippingOrderLine]] = relationship(
        back_populates="order", cascade="all,delete-orphan"
    )


class DropshippingOrderLine(Base):
    """
    Linha de uma encomenda PS.
    Cada linha pode ser associada a um SupplierOrder diferente.
    """

    __tablename__ = "dropshipping_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK para encomenda PS
    id_order: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dropshipping_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identificação PS
    id_ps_order_detail: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    id_ps_product: Mapped[int] = mapped_column(Integer, nullable=False)
    id_ps_product_attribute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Produto info (do PS)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_ean: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    product_supplier_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Quantidades e preços
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_tax_excl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_price_tax_incl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_price_tax_excl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_price_tax_incl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # Estado da linha
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        nullable=False,
    )

    # Match com produto Genesys (se encontrado)
    id_product: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )

    # Fornecedor selecionado
    id_supplier: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    supplier_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # FK para pedido ao fornecedor (quando agrupada)
    id_supplier_order: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("supplier_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=utcnow, nullable=True)

    # Relações
    order: Mapped[DropshippingOrder] = relationship(back_populates="lines")
    product: Mapped[Product | None] = relationship()
    supplier: Mapped[Supplier | None] = relationship()
    supplier_order: Mapped[SupplierOrder | None] = relationship(back_populates="lines")


class SupplierOrder(Base):
    """
    Pedido ao fornecedor.
    Agrega linhas de múltiplas encomendas PS para o mesmo fornecedor.
    """

    __tablename__ = "supplier_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Fornecedor
    id_supplier: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Estado
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status", create_constraint=False),
        default=OrderStatus.PENDING,
        nullable=False,
    )

    # Valores calculados
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Integração Sage
    sage_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Integração ClickUp
    clickup_task_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=utcnow, nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Notas
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relações
    supplier: Mapped[Supplier] = relationship()
    lines: Mapped[list[DropshippingOrderLine]] = relationship(back_populates="supplier_order")
