from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.errors import InvalidArgument
from app.core.normalize import normalize_simple, normalize_key_ci
from app.models.brand import Brand
from app.repositories.catalog.read.brand_read_repo import BrandReadRepository, MAX_NAME_LEN


class BrandWriteRepository(BrandReadRepository):
    """
    Reutiliza o 'read' via herança para get/get_required/get_by_name.
    Métodos de escrita fazem apenas mutações + flush (commit fica no use case).
    """

    def get_or_create(self, name: str) -> Brand:
        shown = normalize_simple(name, MAX_NAME_LEN)
        key = normalize_key_ci(name, MAX_NAME_LEN)
        if not key:
            raise InvalidArgument("Brand name is empty")

        existing = self.get_by_name(shown)
        if existing:
            return existing

        b = Brand(name=shown)
        self.db.add(b)
        try:
            self.db.flush()
            return b
        except IntegrityError:
            # corrida entre lookup e flush; tenta novamente via lookup CI
            self.db.rollback()
            again = self.get_by_name(shown)
            if again:
                return again
            raise

    def create(self, name: str) -> Brand:
        return self.get_or_create(name)

    def update(self, id_brand: int, *, name: str | None = None) -> Brand:
        b = self.get_required(id_brand)
        if name is not None:
            shown = normalize_simple(name, MAX_NAME_LEN)
            key = normalize_key_ci(name, MAX_NAME_LEN)
            if not key:
                raise InvalidArgument("Brand name is empty")

            other = self.get_by_name(shown)  # CI
            if other and other.id != b.id:
                raise InvalidArgument("Brand name already exists")

            b.name = shown

        self.db.flush()
        return b

    def delete(self, id_brand: int) -> None:
        b = self.get_required(id_brand)
        self.db.delete(b)
