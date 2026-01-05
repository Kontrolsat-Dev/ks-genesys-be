"""
UseCase: Listar pedidos a fornecedores.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.orders_dropshipping.read.dropshipping_order_read_repo import (
    SupplierOrderReadRepository,
)
from app.schemas.dropshipping import (
    SupplierOrderOut,
    SupplierOrderListOut,
    SupplierOrderLineOut,
)


def execute(
    uow: UoW,
    *,
    page: int = 1,
    page_size: int = 50,
    id_supplier: int | None = None,
    status: str | None = None,
) -> SupplierOrderListOut:
    """
    Lista pedidos a fornecedores com paginação.

    Args:
        uow: Unit of Work
        page: Página actual
        page_size: Tamanho da página
        id_supplier: Filtrar por fornecedor
        status: Filtrar por estado

    Returns:
        SupplierOrderListOut: Lista paginada
    """
    repo = SupplierOrderReadRepository(uow.db)
    orders, total = repo.list_orders(
        page=page,
        page_size=page_size,
        id_supplier=id_supplier,
        status=status,
    )

    items = []
    for o in orders:
        lines_out = [
            SupplierOrderLineOut(
                id=ln.id,
                id_order=ln.id_order,
                order_reference=ln.order.reference if ln.order else "",
                product_name=ln.product_name,
                product_ean=ln.product_ean,
                qty=ln.qty,
                supplier_cost=ln.supplier_cost,
            )
            for ln in o.lines
        ]

        items.append(
            SupplierOrderOut(
                id=o.id,
                id_supplier=o.id_supplier,
                supplier_name=o.supplier.name if o.supplier else None,
                status=o.status,
                total_cost=o.total_cost,
                total_items=o.total_items,
                sage_order_id=o.sage_order_id,
                clickup_task_id=o.clickup_task_id,
                created_at=o.created_at,
                ordered_at=o.ordered_at,
                completed_at=o.completed_at,
                lines=lines_out,
            )
        )

    return SupplierOrderListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
