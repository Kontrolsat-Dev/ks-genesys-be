# app/api/v1/prestashop.py
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import require_access_token, get_prestashop_client
from app.domains.prestashop.usecases.categories.list_categories import (
    execute as uc_list_ps_categories,
)
from app.domains.prestashop.usecases.brands.list_brands import execute as uc_list_brands
from app.external.prestashop_client import PrestashopClient
from app.schemas.prestashop import PrestashopCategoriesOut, PrestashopBrandsOut

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
