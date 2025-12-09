# app/api/v1/prestashop.py
from __future__ import annotations
from app.schemas.prestashop import PrestashopCategoriesOut

from fastapi import APIRouter, Depends
from app.core.deps import require_access_token


router = APIRouter(
    prefix="/prestashop", tags=["prestashop"], dependencies=[Depends(require_access_token)]
)


@router.get(
    "/prestashop/categories",
    response_model=PrestashopCategoriesOut,
    summary="Get prestashop categories",
)
def get_categories():
    return {"categories": ["Category 1", "Category 2"]}
