"""
UseCase: Selecionar fornecedor para uma linha de encomenda Dropshipping.
"""

from __future__ import annotations

from decimal import Decimal

from app.core.errors import BadRequest, NotFound
from app.infra.uow import UoW
from app.models.orders_dropshipping import OrderStatus
from app.repositories.orders_dropshipping.read.dropshipping_order_read_repo import (
    DropshippingOrderLineReadRepository,
)
from app.repositories.orders_dropshipping.write.dropshipping_order_write_repo import (
    DropshippingOrderLineWriteRepository,
)


class LineNotFoundError(NotFound):
    """Linha de encomenda não encontrada."""

    code = "LINE_NOT_FOUND"


class LineNotPendingError(BadRequest):
    """Linha de encomenda não está pendente."""

    code = "LINE_NOT_PENDING"


def execute(
    uow: UoW,
    *,
    order_id: int,
    line_id: int,
    id_supplier: int,
    supplier_cost: Decimal | None = None,
) -> int:
    """
    Atribui fornecedor a uma linha de encomenda.

    Args:
        uow: Unit of Work
        order_id: ID da encomenda pai
        line_id: ID da linha
        id_supplier: ID do fornecedor a atribuir
        supplier_cost: Custo opcional deste fornecedor

    Returns:
        int: ID da linha

    Raises:
        LineNotFoundError: Se linha não existir ou não pertencer à encomenda
        LineNotPendingError: Se linha não estiver pendente
    """
    line_r = DropshippingOrderLineReadRepository(uow.db)
    line_w = DropshippingOrderLineWriteRepository(uow.db)

    line = line_r.get(line_id)
    if not line or line.id_order != order_id:
        raise LineNotFoundError(f"Linha {line_id} não encontrada na encomenda {order_id}")

    if line.status != OrderStatus.PENDING:
        raise LineNotPendingError(f"Linha {line_id} não está pendente (estado: {line.status})")

    line_w.select_supplier(
        line,
        id_supplier=id_supplier,
        supplier_cost=supplier_cost,
    )
    uow.commit()

    return line_id
