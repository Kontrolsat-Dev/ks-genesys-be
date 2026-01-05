"""
Repositório de escrita para encomendas Dropshipping.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.orders_dropshipping import (
    DropshippingOrder,
    DropshippingOrderLine,
    OrderStatus,
    SupplierOrder,
)


class DropshippingOrderWriteRepository:
    """Operações de escrita para encomendas dropshipping."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        id_ps_order: int,
        reference: str,
        ps_state_id: int,
        ps_state_name: str | None,
        customer_email: str,
        customer_firstname: str,
        customer_lastname: str,
        delivery_address: dict,
        invoice_address: dict,
        carrier_name: str | None,
        payment_method: str | None,
        total_paid_tax_incl: Decimal,
        total_paid_tax_excl: Decimal,
        total_shipping_tax_incl: Decimal,
        total_shipping_tax_excl: Decimal,
        ps_date_add: datetime,
        ps_date_upd: datetime,
    ) -> DropshippingOrder:
        """Cria nova encomenda dropshipping."""
        order = DropshippingOrder(
            id_ps_order=id_ps_order,
            reference=reference,
            ps_state_id=ps_state_id,
            ps_state_name=ps_state_name,
            customer_email=customer_email,
            customer_firstname=customer_firstname,
            customer_lastname=customer_lastname,
            delivery_address=delivery_address,
            invoice_address=invoice_address,
            carrier_name=carrier_name,
            payment_method=payment_method,
            total_paid_tax_incl=total_paid_tax_incl,
            total_paid_tax_excl=total_paid_tax_excl,
            total_shipping_tax_incl=total_shipping_tax_incl,
            total_shipping_tax_excl=total_shipping_tax_excl,
            ps_date_add=ps_date_add,
            ps_date_upd=ps_date_upd,
        )
        self.db.add(order)
        self.db.flush()
        return order


class DropshippingOrderLineWriteRepository:
    """Operações de escrita para linhas de encomenda."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        id_order: int,
        id_ps_order_detail: int,
        id_ps_product: int,
        id_ps_product_attribute: int,
        product_name: str,
        product_reference: str | None,
        product_ean: str | None,
        product_supplier_reference: str | None,
        qty: int,
        unit_price_tax_excl: Decimal,
        unit_price_tax_incl: Decimal,
        total_price_tax_excl: Decimal,
        total_price_tax_incl: Decimal,
        id_product: int | None = None,
    ) -> DropshippingOrderLine:
        """Cria nova linha de encomenda."""
        line = DropshippingOrderLine(
            id_order=id_order,
            id_ps_order_detail=id_ps_order_detail,
            id_ps_product=id_ps_product,
            id_ps_product_attribute=id_ps_product_attribute,
            product_name=product_name,
            product_reference=product_reference,
            product_ean=product_ean,
            product_supplier_reference=product_supplier_reference,
            qty=qty,
            unit_price_tax_excl=unit_price_tax_excl,
            unit_price_tax_incl=unit_price_tax_incl,
            total_price_tax_excl=total_price_tax_excl,
            total_price_tax_incl=total_price_tax_incl,
            id_product=id_product,
            status=OrderStatus.PENDING,
        )
        self.db.add(line)
        self.db.flush()
        return line

    def select_supplier(
        self,
        line: DropshippingOrderLine,
        *,
        id_supplier: int,
        supplier_cost: Decimal | None = None,
    ) -> DropshippingOrderLine:
        """Atribui fornecedor a uma linha."""
        line.id_supplier = id_supplier
        line.supplier_cost = supplier_cost
        self.db.add(line)
        self.db.flush()
        return line

    def assign_to_supplier_order(
        self,
        line: DropshippingOrderLine,
        id_supplier_order: int,
    ) -> DropshippingOrderLine:
        """Associa linha a um pedido ao fornecedor."""
        line.id_supplier_order = id_supplier_order
        self.db.add(line)
        self.db.flush()
        return line

    def update_status(
        self,
        line: DropshippingOrderLine,
        status: OrderStatus,
    ) -> DropshippingOrderLine:
        """Atualiza estado da linha."""
        line.status = status
        self.db.add(line)
        self.db.flush()
        return line


class SupplierOrderWriteRepository:
    """Operações de escrita para pedidos a fornecedores."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        id_supplier: int,
        total_cost: Decimal = Decimal("0"),
        total_items: int = 0,
    ) -> SupplierOrder:
        """Cria novo pedido ao fornecedor."""
        order = SupplierOrder(
            id_supplier=id_supplier,
            status=OrderStatus.PENDING,
            total_cost=total_cost,
            total_items=total_items,
        )
        self.db.add(order)
        self.db.flush()
        return order

    def update_totals(
        self,
        order: SupplierOrder,
        total_cost: Decimal,
        total_items: int,
    ) -> SupplierOrder:
        """Atualiza totais do pedido."""
        order.total_cost = total_cost
        order.total_items = total_items
        self.db.add(order)
        self.db.flush()
        return order

    def confirm(
        self,
        order: SupplierOrder,
        *,
        sage_order_id: str | None = None,
        clickup_task_id: str | None = None,
    ) -> SupplierOrder:
        """Confirma pedido ao fornecedor (transição para ORDERED)."""
        order.status = OrderStatus.ORDERED
        order.ordered_at = datetime.utcnow()
        order.sage_order_id = sage_order_id
        order.clickup_task_id = clickup_task_id
        self.db.add(order)
        self.db.flush()
        return order

    def complete(self, order: SupplierOrder) -> SupplierOrder:
        """Marca pedido como concluído."""
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        self.db.add(order)
        self.db.flush()
        return order

    def set_error(self, order: SupplierOrder, notes: str | None = None) -> SupplierOrder:
        """Marca pedido com erro."""
        order.status = OrderStatus.ERROR
        if notes:
            order.notes = notes
        self.db.add(order)
        self.db.flush()
        return order
