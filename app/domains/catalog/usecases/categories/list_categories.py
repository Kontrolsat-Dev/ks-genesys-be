# app/domains/catalog/usecases/categories/list_categories.py
from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.catalog.read.category_read_repo import CategoryReadRepository


def execute(
    uow: UoW,
    *,
    search: str | None,
    page: int,
    page_size: int,
    auto_import: bool | None = None,
):
    db = uow.db
    repo = CategoryReadRepository(db)
    return repo.list(q=search, page=page, page_size=page_size, auto_import=auto_import)
