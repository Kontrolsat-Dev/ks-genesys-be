"""
UseCase: Listar encomendas Dropshipping.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.models.orders_dropshipping import OrderStatus
from app.schemas.dropshipping import (
    AddressOut,
    DropshippingOrderOut,
    DropshippingOrderListOut,
    DropshippingOrderLineOut,
)


def execute(
    uow: UoW,
    *,
    page: int = 1,
    page_size: int = 50,
    status: OrderStatus | None = None,
) -> DropshippingOrderListOut:
    """
    Lista encomendas dropshipping com paginação.

    Args:
        uow: Unit of Work
        page: Página actual
        page_size: Tamanho da página
        status: Filtrar por estado

    Returns:
        DropshippingOrderListOut: Lista paginada
    """
    orders, total = uow.dropshipping_orders.list_orders(
        page=page,
        page_size=page_size,
        status=status,
    )

    items = []
    for o in orders:
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
            for ln in o.lines
        ]

        items.append(
            DropshippingOrderOut(
                id=o.id,
                id_ps_order=o.id_ps_order,
                reference=o.reference,
                ps_state_id=o.ps_state_id,
                ps_state_name=o.ps_state_name,
                customer_email=o.customer_email,
                customer_firstname=o.customer_firstname,
                customer_lastname=o.customer_lastname,
                customer_name=f"{o.customer_firstname} {o.customer_lastname}",
                delivery_address=AddressOut(
                    **o.delivery_address) if o.delivery_address else None,
                invoice_address=AddressOut(
                    **o.invoice_address) if o.invoice_address else None,
                carrier_name=o.carrier_name,
                payment_method=o.payment_method,
                total_paid_tax_incl=o.total_paid_tax_incl,
                total_paid_tax_excl=o.total_paid_tax_excl,
                total_shipping_tax_incl=o.total_shipping_tax_incl,
                total_shipping_tax_excl=o.total_shipping_tax_excl,
                ps_date_add=o.ps_date_add,
                ps_date_upd=o.ps_date_upd,
                created_at=o.created_at,
                lines=lines_out,
                lines_count=len(lines_out),
                lines_pending=sum(
                    1 for ln in lines_out if ln.status == OrderStatus.PENDING),
                lines_matched=sum(1 for ln in lines_out if ln.product_matched),
            )
        )

    return DropshippingOrderListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
