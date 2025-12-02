# app/domains/catalog/usecases/brands/list_brands.py

from __future__ import annotations
from collections.abc import Sequence

from app.infra.uow import UoW
from app.models.brand import Brand
from app.repositories.catalog.read.brand_read_repo import BrandsReadRepository


def execute(
    uow: UoW, *, search: str | None, page: int, page_size: int
) -> tuple[Sequence[Brand], int]:
    db = uow.db
    repo = BrandsReadRepository(db)
    return repo.list(q=search, page=page, page_size=page_size)
