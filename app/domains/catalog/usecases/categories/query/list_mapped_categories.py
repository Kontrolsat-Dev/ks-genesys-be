# app/domains/catalog/usecases/categories/list_mapped_categories.py
"""
UseCase para listar categorias com mapeamento PrestaShop.
"""

from __future__ import annotations

from sqlalchemy import select

from app.infra.uow import UoW
from app.models.category import Category
from app.schemas.categories import CategoryMappingOut


def execute(uow: UoW) -> list[CategoryMappingOut]:
    """
    Lista apenas categorias que têm mapeamento PrestaShop ativo
    (id_ps_category IS NOT NULL).

    Returns:
        list[CategoryMappingOut] schemas
    """
    db = uow.db
    stmt = select(Category).where(Category.id_ps_category.is_not(None)).order_by(Category.name)
    categories = list(db.scalars(stmt).all())

    return [CategoryMappingOut.model_validate(cat) for cat in categories]
