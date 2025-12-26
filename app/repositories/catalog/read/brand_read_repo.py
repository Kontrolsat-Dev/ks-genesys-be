# app/repositories/catalog/read/BrandReadRepository
from __future__ import annotations

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models.brand import Brand
from app.core.normalize import normalize_key_ci

MAX_NAME_LEN = 200


class BrandReadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id_brand: int) -> Brand | None:
        return self.db.get(Brand, id_brand)

    def get_required(self, id_brand: int) -> Brand:
        b = self.get(id_brand)
        if not b:
            raise NotFound("Brand not found")
        return b

    def get_by_name(self, name: str) -> Brand | None:
        """Lookup case-insensitive com trim no lado da BD."""
        key = normalize_key_ci(name, MAX_NAME_LEN)
        if not key:
            return None
        stmt = select(Brand).where(func.lower(func.btrim(Brand.name)) == key).limit(1)
        return self.db.execute(stmt).scalars().first()

    def list(self, *, q: str | None, page: int, page_size: int):
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        filters = []
        if q:
            like = f"%{q.strip()}%"
            filters.append(func.btrim(Brand.name).ilike(like))

        if filters:
            total = (
                self.db.scalar(select(func.count()).select_from(Brand).where(and_(*filters))) or 0
            )
            stmt = select(Brand).where(and_(*filters))
        else:
            total = self.db.scalar(select(func.count()).select_from(Brand)) or 0
            stmt = select(Brand)

        stmt = stmt.order_by(
            func.lower(func.btrim(Brand.name)).asc(),
            Brand.id.asc(),
        )

        rows = self.db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).scalars().all()
        return rows, int(total)
