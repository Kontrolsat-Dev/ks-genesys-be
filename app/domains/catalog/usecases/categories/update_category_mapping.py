# app/domains/catalog/usecases/categories/update_category_mapping.py
from __future__ import annotations

from app.infra.uow import UoW
from app.core.errors import NotFound
from app.models.category import Category


def execute(
    uow: UoW,
    *,
    id_category: int,
    id_ps_category: int,
    ps_category_name: str,
    auto_import: bool,
) -> Category:
    """
    Mapeia uma categoria Genesys para uma categoria PrestaShop.
    """
    db = uow.db
    cat = db.get(Category, id_category)
    if not cat:
        raise NotFound(f"Category {id_category} not found")

    cat.id_ps_category = id_ps_category
    cat.ps_category_name = ps_category_name
    cat.auto_import = auto_import

    uow.commit()
    return cat
