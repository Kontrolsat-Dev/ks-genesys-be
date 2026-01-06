"""
Repositório de leitura para encomendas Dropshipping.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.orders_dropshipping import (
    DropshippingOrder,
    DropshippingOrderLine,
    OrderStatus,
    SupplierOrder,
)


class DropshippingOrderReadRepository:
    """Consultas de leitura para encomendas dropshipping."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id_order: int) -> DropshippingOrder | None:
        """Devolve encomenda por ID com linhas."""
        return self.db.get(
            DropshippingOrder,
            id_order,
            options=[joinedload(DropshippingOrder.lines)],
        )

    def get_by_ps_order_id(self, id_ps_order: int) -> DropshippingOrder | None:
        """Devolve encomenda pelo ID do PrestaShop."""
        stmt = select(DropshippingOrder).where(DropshippingOrder.id_ps_order == id_ps_order)
        return self.db.scalar(stmt)

    def exists_by_ps_order_id(self, id_ps_order: int) -> bool:
        """Verifica se encomenda já foi importada."""
        stmt = select(func.count()).where(DropshippingOrder.id_ps_order == id_ps_order)
        return self.db.scalar(stmt) > 0

    def list_orders(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        status: OrderStatus | None = None,
        since: datetime | None = None,
    ) -> tuple[list[DropshippingOrder], int]:
        """
        Lista encomendas com paginação e filtros.

        Returns:
            Tuplo de (encomendas, total)
        """
        stmt = select(DropshippingOrder)

        if status:
            # Filtrar por estado da linha (encomenda tem pelo menos uma linha com este estado)
            stmt = (
                stmt.join(DropshippingOrderLine)
                .where(DropshippingOrderLine.status == status)
                .distinct()
            )

        if since:
            stmt = stmt.where(DropshippingOrder.created_at >= since)

        # Contagem
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Paginação
        stmt = stmt.order_by(DropshippingOrder.id.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.options(joinedload(DropshippingOrder.lines))

        orders = list(self.db.scalars(stmt).unique())
        return orders, total


class DropshippingOrderLineReadRepository:
    """Consultas de leitura para linhas de encomenda."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id_line: int) -> DropshippingOrderLine | None:
        """Devolve linha por ID."""
        return self.db.get(DropshippingOrderLine, id_line)

    def list_pending_by_supplier(self, id_supplier: int) -> list[DropshippingOrderLine]:
        """Devolve todas as linhas pendentes para um fornecedor."""
        stmt = (
            select(DropshippingOrderLine)
            .where(DropshippingOrderLine.id_supplier == id_supplier)
            .where(DropshippingOrderLine.status == OrderStatus.PENDING)
            .where(DropshippingOrderLine.id_supplier_order.is_(None))
        )
        return list(self.db.scalars(stmt))

    def list_unassigned_pending(self) -> list[DropshippingOrderLine]:
        """Devolve todas as linhas pendentes sem fornecedor atribuído."""
        stmt = (
            select(DropshippingOrderLine)
            .where(DropshippingOrderLine.status == OrderStatus.PENDING)
            .where(DropshippingOrderLine.id_supplier.is_(None))
        )
        return list(self.db.scalars(stmt))

    def list_by_status(self, status: OrderStatus) -> list[DropshippingOrderLine]:
        """Devolve todas as linhas com determinado estado."""
        stmt = (
            select(DropshippingOrderLine)
            .where(DropshippingOrderLine.status == status)
            .order_by(DropshippingOrderLine.id.desc())
        )
        return list(self.db.scalars(stmt))


class SupplierOrderReadRepository:
    """Consultas de leitura para pedidos a fornecedores."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id_order: int) -> SupplierOrder | None:
        """Devolve pedido ao fornecedor por ID com linhas."""
        return self.db.get(
            SupplierOrder,
            id_order,
            options=[joinedload(SupplierOrder.lines)],
        )

    def list_orders(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        id_supplier: int | None = None,
        status: str | None = None,
    ) -> tuple[list[SupplierOrder], int]:
        """Lista pedidos a fornecedores com paginação."""
        stmt = select(SupplierOrder)

        if id_supplier:
            stmt = stmt.where(SupplierOrder.id_supplier == id_supplier)

        if status:
            stmt = stmt.where(SupplierOrder.status == status)

        # Contagem
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Paginação
        stmt = stmt.order_by(SupplierOrder.id.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.options(joinedload(SupplierOrder.lines))

        orders = list(self.db.scalars(stmt).unique())
        return orders, total
