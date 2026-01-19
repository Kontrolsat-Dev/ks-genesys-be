# app/api/v1/prestashop.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_access_token, get_prestashop_client
from app.core.errors import BadRequest
from app.domains.prestashop.usecases.categories.list_categories import (
    execute as uc_list_ps_categories,
)
from app.domains.prestashop.usecases.brands.list_brands import execute as uc_list_brands
from app.domains.prestashop.usecases.orders.list_orders_dropshipping import (
    execute as uc_list_orders_dropshipping,
)
from app.domains.prestashop.usecases.orders.get_order import (
    execute as uc_get_ps_order,
)
from app.external.prestashop_client import PrestashopClient
from app.schemas.prestashop import (
    PrestashopCategoriesOut,
    PrestashopBrandsOut,
    PrestashopOrderDetailOut,
)

router = APIRouter(
    prefix="/prestashop",
    tags=["prestashop"],
    dependencies=[Depends(require_access_token)],
)


@router.get(
    "/categories",
    response_model=PrestashopCategoriesOut,
    summary="Listar categorias do PrestaShop",
)
def get_categories(
    client: PrestashopClient = Depends(get_prestashop_client),
):
    """
    Obtém a árvore de categorias do PrestaShop via módulo r_genesys.
    Inclui hierarquia completa (parent, children) e estado de cada categoria.
    Usado para mapear categorias Genesys para categorias PS.
    """
    return uc_list_ps_categories(ps_client=client)


@router.get(
    path="/brands",
    response_model=PrestashopBrandsOut,
    summary="Listar marcas do PrestaShop",
)
def get_brands(
    client: PrestashopClient = Depends(get_prestashop_client),
):
    """
    Obtém a lista de marcas registadas no PrestaShop via módulo r_genesys.
    Inclui ID, nome e metadados de cada marca.
    Usado para matching de marcas durante importação de produtos.
    """
    return uc_list_brands(ps_client=client)


@router.get(
    path="/orders-dropshipping",
    summary="Listar linhas de encomendas dropshipping",
)
def get_orders(
    client: PrestashopClient = Depends(get_prestashop_client),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
):
    return uc_list_orders_dropshipping(page=page, page_size=page_size, ps_client=client)


@router.get(
    "/orders/{id_order}",
    response_model=PrestashopOrderDetailOut,
    summary="Obter detalhes de uma encomenda (JIT)",
)
def get_order_detail(
    id_order: int,
    client: PrestashopClient = Depends(get_prestashop_client),
):
    """
    Obtém detalhes completos de uma encomenda diretamente do PrestaShop via API (JIT).
    Não usa base de dados local.
    """
    try:
        return uc_get_ps_order(id_order=id_order, ps_client=client)
    except Exception as e:
        raise BadRequest(f"Erro ao obter encomenda do PrestaShop: {e}") from e
