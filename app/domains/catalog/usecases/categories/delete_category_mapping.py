# app/domains/catalog/usecases/categories/delete_category_mapping.py
from __future__ import annotations

from app.infra.uow import UoW
from app.core.errors import NotFound
from app.models.category import Category


def execute(uow: UoW, *, id_category: int) -> None:
    """
    Remove o mapeamento PrestaShop de uma categoria.
    """
    db = uow.db
    cat = db.get(Category, id_category)
    if not cat:
        raise NotFound(f"Category {id_category} not found")

    cat.id_ps_category = None
    cat.ps_category_name = None
    cat.auto_import = False

    uow.commit()
