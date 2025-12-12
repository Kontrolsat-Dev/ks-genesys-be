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


@router.get("", response_model=CategoryListOut)
def list_categories(
    uow: UowDep,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auto_import: bool | None = Query(None, description="Filtrar por auto_import ativo/inativo"),
):
    items, total = uc_list.execute(
        uow, search=search, page=page, page_size=page_size, auto_import=auto_import
    )
    # Serialize with supplier name
    serialized = [
        {
            "id": cat.id,
            "name": cat.name,
            "id_supplier_source": cat.id_supplier_source,
            "supplier_source_name": cat.supplier_source.name if cat.supplier_source else None,
            "id_ps_category": cat.id_ps_category,
            "ps_category_name": cat.ps_category_name,
            "auto_import": cat.auto_import,
        }
        for cat in items
    ]
    return {"items": serialized, "total": total, "page": page, "page_size": page_size}


@router.get("/mapped", response_model=list[CategoryMappingOut])
def list_mapped_categories(uow: UowDep):
    """Listar apenas categorias com mapeamento PrestaShop ativo"""
    return uc_list_mapped.execute(uow)


@router.put("/{id_category}/mapping", response_model=CategoryMappingOut)
def update_category_mapping(
    id_category: int,
    payload: CategoryMappingIn,
    uow: UowDep,
):
    """Mapear categoria Genesys para categoria PrestaShop"""
    return uc_update_mapping.execute(
        uow,
        id_category=id_category,
        id_ps_category=payload.id_ps_category,
        ps_category_name=payload.ps_category_name,
        auto_import=payload.auto_import,
    )


@router.delete("/{id_category}/mapping", status_code=204)
def delete_category_mapping(id_category: int, uow: UowDep):
    """Remover mapeamento de categoria"""
    uc_delete_mapping.execute(uow, id_category=id_category)
