# app/api/v1/brands.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Query, Depends

from app.infra.uow import UoW
from app.core.deps import get_uow, require_access_token
from app.schemas.brands import BrandListOut
from app.domains.catalog.usecases.brands.query.list_brands import execute as uc_list


router = APIRouter(
    prefix="/brands",
    tags=["brands"],
    dependencies=[Depends(require_access_token)],
)

UowDep = Annotated[UoW, Depends(get_uow)]


@router.get("", response_model=BrandListOut, summary="Listar marcas")
def list_brands(
    uow: UowDep,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> BrandListOut:
    """
    Lista as marcas.
    """
    return uc_list(uow, search=search, page=page, page_size=page_size)
