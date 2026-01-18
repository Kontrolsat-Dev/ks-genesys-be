# app/domains/catalog/usecases/brands/list_brands.py
"""
UseCase para listar marcas com paginação e pesquisa.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.schemas.brands import BrandListOut, BrandOut


def execute(uow: UoW, *, search: str | None, page: int, page_size: int) -> BrandListOut:
    """
    Lista marcas com paginação e pesquisa opcional.

    Returns:
        BrandListOut schema
    """
    items, total = uow.brands.list(q=search, page=page, page_size=page_size)

    return BrandListOut(
        items=[BrandOut.model_validate(b) for b in items],
        total=total,
        page=page,
        page_size=page_size,
    )
