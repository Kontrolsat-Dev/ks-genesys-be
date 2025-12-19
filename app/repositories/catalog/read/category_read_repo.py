# app/repositories/category_repo.py
from __future__ import annotations

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, joinedload

from app.core.normalize import normalize_key_ci
from app.models.category import Category

MAX_NAME_LEN = 300


class CategoryReadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id_category: int) -> Category | None:
        """Get category by ID."""
        return self.db.get(Category, id_category)

    def get_by_name(self, name: str) -> Category | None:
        key = normalize_key_ci(name, MAX_NAME_LEN)
        if not key:
            return None
        return (
            self.db.execute(
                select(Category).where(func.lower(func.btrim(Category.name)) == key).limit(1)
            )
            .scalars()
            .first()
        )

    def list(
        self,
        *,
        q: str | None,
        page: int,
        page_size: int,
        auto_import: bool | None = None,
    ):
        # bounds
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # base & filtros
        stmt = select(Category).options(joinedload(Category.supplier_source))
        filters = []
        if q:
            like = f"%{q.strip()}%"
            filters.append(func.btrim(Category.name).ilike(like))

        if auto_import is not None:
            filters.append(Category.auto_import == auto_import)

        if filters:
            stmt = stmt.where(and_(*filters))

        # total (sem ORDER BY/LIMIT)
        total = (
            self.db.scalar(
                (select(func.count()).select_from(Category).where(and_(*filters)))
                if filters
                else (select(func.count()).select_from(Category))
            )
            or 0
        )

        # ordenação estável, case-insensitive
        stmt = stmt.order_by(
            func.lower(func.btrim(Category.name)).asc(),
            Category.id.asc(),
        )

        rows = (
            self.db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
            .scalars()
            .unique()
            .all()
        )
        return rows, int(total)
