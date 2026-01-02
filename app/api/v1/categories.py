# app/api/v1/categories.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Query, Depends

from app.infra.uow import UoW
from app.core.deps import get_uow, require_access_token
from app.schemas.categories import (
    CategoryListOut,
    CategoryMappingIn,
    CategoryMappingOut,
)
from app.domains.catalog.usecases.categories import list_categories as uc_list
from app.domains.catalog.usecases.categories import update_category_mapping as uc_update_mapping
from app.domains.catalog.usecases.categories import delete_category_mapping as uc_delete_mapping
from app.domains.catalog.usecases.categories import list_mapped_categories as uc_list_mapped

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    dependencies=[Depends(require_access_token)],
)
UowDep = Annotated[UoW, Depends(get_uow)]


@router.get(
    "",
    response_model=CategoryListOut,
    summary="Listar categorias",
)
def list_categories(
    uow: UowDep,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auto_import: bool | None = Query(None, description="Filtrar por auto_import ativo/inativo"),
):
    """
    Lista as categorias do catálogo com paginação e pesquisa opcional.
    Inclui informação de mapeamento PrestaShop e fornecedor de origem.
    """
    return uc_list.execute(
        uow, search=search, page=page, page_size=page_size, auto_import=auto_import
    )


@router.get(
    "/mapped",
    response_model=list[CategoryMappingOut],
    summary="Listar categorias mapeadas",
)
def list_mapped_categories(uow: UowDep):
    """
    Lista apenas as categorias que têm mapeamento PrestaShop configurado.
    Útil para verificar que categorias estão prontas para importação automática.
    """
    return uc_list_mapped.execute(uow)


@router.put(
    "/{id_category}/mapping",
    response_model=CategoryMappingOut,
    summary="Mapear categoria para PrestaShop",
)
def update_category_mapping(
    id_category: int,
    payload: CategoryMappingIn,
    uow: UowDep,
):
    """
    Mapeia uma categoria do Genesys para uma categoria do PrestaShop.
    Permite ativar importação automática de produtos desta categoria.
    """
    return uc_update_mapping.execute(
        uow,
        id_category=id_category,
        id_ps_category=payload.id_ps_category,
        ps_category_name=payload.ps_category_name,
        auto_import=payload.auto_import,
        default_ecotax=payload.default_ecotax,
        default_extra_fees=payload.default_extra_fees,
    )


@router.delete(
    "/{id_category}/mapping",
    status_code=204,
    summary="Remover mapeamento de categoria",
)
def delete_category_mapping(id_category: int, uow: UowDep):
    """
    Remove o mapeamento PrestaShop de uma categoria.
    Desativa a importação automática de produtos desta categoria.
    """
    uc_delete_mapping.execute(uow, id_category=id_category)
