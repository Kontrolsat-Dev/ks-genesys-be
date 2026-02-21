from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.errors import InvalidArgument
from app.core.normalize import normalize_simple, normalize_key_ci
from app.models.category import Category
from app.repositories.catalog.read.category_read_repo import (
    CategoryReadRepository,
    MAX_NAME_LEN,
)


class CategoryWriteRepository(CategoryReadRepository):
    def get_or_create(self, name: str, *, id_supplier: int | None = None) -> Category:
        shown = normalize_simple(name, MAX_NAME_LEN)
        key = normalize_key_ci(name, MAX_NAME_LEN)
        if not key:
            raise InvalidArgument("Category name is empty")

        existing = self.get_by_name(shown)
        if existing:
            return existing

        c = Category(name=shown, id_supplier_source=id_supplier)
        self.db.add(c)
        try:
            self.db.flush()
            return c
        except IntegrityError:
            self.db.rollback()
            again = self.get_by_name(shown)
            if again:
                return again
            raise

    def create(self, name: str, *, id_supplier: int | None = None) -> Category:
        return self.get_or_create(name, id_supplier=id_supplier)

    def update(self, id_category: int, *, name: str | None = None) -> Category:
        c = self.get_required(id_category)
        if name is not None:
            shown = normalize_simple(name, MAX_NAME_LEN)
            key = normalize_key_ci(name, MAX_NAME_LEN)
            if not key:
                raise InvalidArgument("Category name is empty")

            other = self.get_by_name(shown)  # CI
            if other and other.id != c.id:
                raise InvalidArgument("Category name already exists")

            c.name = shown

        self.db.flush()
        return c

    def delete(self, id_category: int) -> None:
        c = self.get_required(id_category)
        self.db.delete(c)

    def clear_ps_mapping(self, id_category: int) -> Category:
        """Remove o mapeamento PrestaShop de uma categoria."""
        c = self.get_required(id_category)
        c.id_ps_category = None
        c.ps_category_name = None
        c.auto_import = False
        c.auto_import_since = None
        self.db.flush()
        return c
