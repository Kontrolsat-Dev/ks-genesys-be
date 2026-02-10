"""
Endpoints da API para encomendas Dropshipping.
Routes simples - lógica nos usecases.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_uow
from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
from app.models.orders_dropshipping import OrderStatus
from app.schemas.dropshipping import (
    DropshippingOrderOut,
    DropshippingOrderListOut,
    SupplierOrderListOut,
    SelectSupplierIn,
    SelectSupplierOut,
    ImportOrdersOut,
    PendingLinesListOut,
)
from app.domains.orders_dropshipping.usecases.query.list_orders import (
    execute as uc_list_orders,
)
from app.domains.orders_dropshipping.usecases.query.get_order import (
    execute as uc_get_order,
)
from app.domains.orders_dropshipping.usecases.command.select_supplier import (
    execute as uc_select_supplier,
)
from app.domains.orders_dropshipping.usecases.query.list_supplier_orders import (
    execute as uc_list_supplier_orders,
)
from app.domains.orders_dropshipping.usecases.command.import_orders import (
    execute as uc_import_orders,
)
from app.domains.orders_dropshipping.usecases.query.list_pending_lines import (
    execute as uc_list_pending_lines,
)


router = APIRouter(prefix="/orders-dropshipping", tags=["orders-dropshipping"])


# --------------------- Encomendas ---------------------


@router.get("/orders", response_model=DropshippingOrderListOut)
def list_orders(
    uow: Annotated[UoW, Depends(get_uow)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: OrderStatus | None = None,
) -> DropshippingOrderListOut:
    """Listar encomendas dropshipping."""
    return uc_list_orders(
        uow=uow,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get("/orders/{order_id}", response_model=DropshippingOrderOut)
def get_order(
    order_id: int,
    uow: Annotated[UoW, Depends(get_uow)],
) -> DropshippingOrderOut:
    """Obter detalhes de uma encomenda."""
    return uc_get_order(uow=uow, order_id=order_id)


# --------------------- Linhas ---------------------


@router.get("/pending-lines", response_model=PendingLinesListOut)
def list_pending_lines(
    uow: Annotated[UoW, Depends(get_uow)],
    status: OrderStatus | None = Query(None, description="Filtrar por estado"),
) -> PendingLinesListOut:
    """Lista linhas com ofertas disponíveis de fornecedores."""
    return uc_list_pending_lines(uow=uow, status=status)


@router.post(
    "/orders/{order_id}/lines/{line_id}/select-supplier",
    response_model=SelectSupplierOut,
)
def select_supplier_for_line(
    order_id: int,
    line_id: int,
    payload: SelectSupplierIn,
    uow: Annotated[UoW, Depends(get_uow)],
) -> SelectSupplierOut:
    """Selecionar fornecedor para uma linha."""
    line_id_result = uc_select_supplier(
        uow=uow,
        order_id=order_id,
        line_id=line_id,
        id_supplier=payload.id_supplier,
        supplier_cost=payload.supplier_cost,
    )
    return SelectSupplierOut(line_id=line_id_result)


# --------------------- Importação ---------------------


@router.post("/import", response_model=ImportOrdersOut)
def trigger_import(
    uow: Annotated[UoW, Depends(get_uow)],
    since: str | None = Query(None, description="Filtrar por date_upd >= since (YYYY-MM-DD)"),
) -> ImportOrdersOut:
    """Importar manualmente encomendas dropshipping do PrestaShop."""
    ps_client = PrestashopClient()

    result = uc_import_orders(
        uow=uow,
        ps_client=ps_client,
        since=since,
    )

    return ImportOrdersOut(
        total_fetched=result.total_fetched,
        imported=result.imported,
        skipped=result.skipped,
        errors=result.error_messages or [],
    )


# --------------------- Pedidos a Fornecedores ---------------------


@router.get("/supplier-orders", response_model=SupplierOrderListOut)
def list_supplier_orders(
    uow: Annotated[UoW, Depends(get_uow)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    id_supplier: int | None = None,
    status: str | None = None,
) -> SupplierOrderListOut:
    """Listar pedidos a fornecedores."""
    return uc_list_supplier_orders(
        uow=uow,
        page=page,
        page_size=page_size,
        id_supplier=id_supplier,
        status=status,
    )
