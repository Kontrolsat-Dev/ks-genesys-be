# app/domains/catalog/usecases/categories/query/list_categories.py
# Lista categorias com paginação e filtros

from __future__ import annotations

from app.infra.uow import UoW
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
    items, total = uow.categories.list(
        q=search, page=page, page_size=page_size, auto_import=auto_import
    )

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
            default_ecotax=float(cat.default_ecotax) if cat.default_ecotax else 0,
            default_extra_fees=float(cat.default_extra_fees) if cat.default_extra_fees else 0,
        )
        for cat in items
    ]

    return CategoryListOut(
        items=serialized,
        total=total,
        page=page,
        page_size=page_size,
    )
