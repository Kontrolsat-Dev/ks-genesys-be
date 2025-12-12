# app/domains/catalog/usecases/categories/list_mapped_categories.py
from __future__ import annotations

from sqlalchemy import select

from app.infra.uow import UoW
from app.models.category import Category


def execute(uow: UoW) -> list[Category]:
    """
    Lista apenas categorias que têm mapeamento PrestaShop ativo
    (id_ps_category IS NOT NULL).
    """
    db = uow.db
    stmt = select(Category).where(Category.id_ps_category.is_not(None)).order_by(Category.name)
    return list(db.scalars(stmt).all())
