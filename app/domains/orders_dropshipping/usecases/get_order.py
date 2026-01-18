"""
UseCase: Obter detalhes de uma encomenda Dropshipping.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.models.orders_dropshipping import OrderStatus
from app.repositories.orders_dropshipping.read.dropshipping_order_read_repo import (
    DropshippingOrderReadRepository,
)
from app.schemas.dropshipping import (
    AddressOut,
    DropshippingOrderOut,
    DropshippingOrderLineOut,
)


class OrderNotFoundError(Exception):
    """Encomenda não encontrada."""


def execute(
    uow: UoW,
    *,
    order_id: int,
) -> DropshippingOrderOut:
    """
    Obtém detalhes de uma encomenda dropshipping.

    Args:
        uow: Unit of Work
        order_id: ID da encomenda

    Returns:
        DropshippingOrderOut: Detalhes da encomenda

    Raises:
        OrderNotFoundError: Se encomenda não existir
    """
    repo = DropshippingOrderReadRepository(uow.db)
    order = repo.get(order_id)

    if not order:
        raise OrderNotFoundError(f"Encomenda {order_id} não encontrada")

    lines_out = [
        DropshippingOrderLineOut(
            id=ln.id,
            id_ps_order_detail=ln.id_ps_order_detail,
            id_ps_product=ln.id_ps_product,
            product_name=ln.product_name,
            product_reference=ln.product_reference,
            product_ean=ln.product_ean,
            product_supplier_reference=ln.product_supplier_reference,
            qty=ln.qty,
            unit_price_tax_excl=ln.unit_price_tax_excl,
            unit_price_tax_incl=ln.unit_price_tax_incl,
            total_price_tax_excl=ln.total_price_tax_excl,
            total_price_tax_incl=ln.total_price_tax_incl,
            status=ln.status,
            id_product=ln.id_product,
            product_matched=ln.id_product is not None,
            id_supplier=ln.id_supplier,
            supplier_name=ln.supplier.name if ln.supplier else None,
            supplier_cost=ln.supplier_cost,
            id_supplier_order=ln.id_supplier_order,
        )
        for ln in order.lines
    ]

    return DropshippingOrderOut(
        id=order.id,
        id_ps_order=order.id_ps_order,
        reference=order.reference,
        customer_email=order.customer_email,
        customer_firstname=order.customer_firstname,
        customer_lastname=order.customer_lastname,
        customer_name=f"{order.customer_firstname} {order.customer_lastname}",
        delivery_address=AddressOut(**order.delivery_address) if order.delivery_address else None,
        invoice_address=AddressOut(**order.invoice_address) if order.invoice_address else None,
        carrier_name=order.carrier_name,
        payment_method=order.payment_method,
        total_paid_tax_incl=order.total_paid_tax_incl,
        total_paid_tax_excl=order.total_paid_tax_excl,
        total_shipping_tax_incl=order.total_shipping_tax_incl,
        total_shipping_tax_excl=order.total_shipping_tax_excl,
        ps_date_add=order.ps_date_add,
        ps_date_upd=order.ps_date_upd,
        created_at=order.created_at,
        lines=lines_out,
        lines_count=len(lines_out),
        lines_pending=sum(1 for ln in lines_out if ln.status == OrderStatus.PENDING),
        lines_matched=sum(1 for ln in lines_out if ln.product_matched),
    )
