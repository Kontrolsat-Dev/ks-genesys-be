# app/domains/catalog/usecases/categories/list_categories.py
from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.catalog.read.category_read_repo import CategoryReadRepository
from app.schemas.categories import CategoryOut, CategoryListOut


def execute(
    uow: UoW,
    *,
    search: str | None,
    page: int,
    page_size: int,
    auto_import: bool | None = None,
) -> CategoryListOut:
    """
    Lista categorias com paginação e filtros.
    Retorna CategoryListOut pronto para a API.
    """
    db = uow.db
    repo = CategoryReadRepository(db)
    items, total = repo.list(q=search, page=page, page_size=page_size, auto_import=auto_import)

    # Serializar para schema com supplier_source_name
    serialized = [
        CategoryOut(
            id=cat.id,
            name=cat.name,
            id_supplier_source=cat.id_supplier_source,
            supplier_source_name=cat.supplier_source.name if cat.supplier_source else None,
            id_ps_category=cat.id_ps_category,
            ps_category_name=cat.ps_category_name,
            auto_import=cat.auto_import,
        )
        for cat in items
    ]

    return CategoryListOut(
        items=serialized,
        total=total,
        page=page,
        page_size=page_size,
    )
