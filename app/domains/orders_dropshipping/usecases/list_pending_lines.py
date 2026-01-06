"""
UseCase: Listar linhas pendentes com ofertas de fornecedores.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.infra.uow import UoW
from app.models.orders_dropshipping import OrderStatus
from app.models.supplier_item import SupplierItem
from app.models.supplier_feed import SupplierFeed
from app.models.supplier import Supplier
from app.repositories.orders_dropshipping.read.dropshipping_order_read_repo import (
    DropshippingOrderLineReadRepository,
    DropshippingOrderReadRepository,
)


def execute(uow: UoW, status: OrderStatus | None = None) -> dict:
    """
    Lista linhas com ofertas disponíveis de fornecedores.
    Ofertas são encontradas pelo match EAN (linha) -> GTIN (SupplierItem).

    Args:
        status: Filtrar por estado (None = todos)

    Returns:
        dict com items (linhas com ofertas) e total
    """
    db = uow.db
    order_r = DropshippingOrderReadRepository(db)
    line_r = DropshippingOrderLineReadRepository(db)

    # Obter linhas (filtradas por estado ou todas)
    if status:
        pending_lines = line_r.list_by_status(status)
    else:
        # Listar todas as linhas não concluídas/canceladas
        from app.models.orders_dropshipping import DropshippingOrderLine

        stmt = (
            select(DropshippingOrderLine)
            .where(
                DropshippingOrderLine.status.notin_([OrderStatus.COMPLETED, OrderStatus.CANCELLED])
            )
            .order_by(DropshippingOrderLine.id.desc())
        )
        pending_lines = list(db.scalars(stmt))

    items = []
    for line in pending_lines:
        # Obter info da encomenda pai
        order = order_r.get(line.id_order)
        if not order:
            continue

        # Obter ofertas para este produto por EAN -> GTIN
        offers = []
        ean = line.product_ean
        if ean:
            # Buscar supplier items com GTIN correspondente e stock > 0
            stmt = (
                select(SupplierItem, Supplier)
                .join(SupplierFeed, SupplierItem.id_feed == SupplierFeed.id)
                .join(Supplier, SupplierFeed.id_supplier == Supplier.id)
                .where(
                    SupplierItem.gtin == ean,
                    SupplierItem.stock > 0,
                )
                .order_by(SupplierItem.price.asc())
            )
            results = db.execute(stmt).all()
            for item, supplier in results:
                offers.append(
                    {
                        "id_supplier": supplier.id,
                        "supplier_name": supplier.name,
                        "supplier_image": supplier.logo_image,
                        "price": Decimal(str(item.price)) if item.price else Decimal(0),
                        "stock": item.stock or 0,
                    }
                )

        items.append(
            {
                "id": line.id,
                "id_order": line.id_order,
                "id_ps_order": order.id_ps_order,
                "order_reference": order.reference,
                "ps_state_name": order.ps_state_name,
                "customer_name": f"{order.customer_firstname} {order.customer_lastname}".strip(),
                "id_ps_order_detail": line.id_ps_order_detail,
                "id_ps_product": line.id_ps_product,
                "product_name": line.product_name,
                "product_reference": line.product_reference,
                "product_ean": line.product_ean,
                "product_supplier_reference": line.product_supplier_reference,
                "qty": line.qty,
                "unit_price_tax_excl": line.unit_price_tax_excl,
                "unit_price_tax_incl": line.unit_price_tax_incl,
                "id_product": line.id_product,
                "status": line.status,
                "offers": offers,
            }
        )

    return {
        "items": items,
        "total": len(items),
    }
