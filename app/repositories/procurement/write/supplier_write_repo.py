from __future__ import annotations
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import InvalidArgument, Conflict
from app.core.normalize import normalize_key_ci, normalize_simple
from app.models.supplier import Supplier
from app.schemas.suppliers import SupplierCreate

MAX_NAME_LEN = 200


class SupplierWriteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id_supplier: int) -> Supplier | None:
        return self.db.get(Supplier, id_supplier)

    # helper local (evita importar o read repo)
    def _get_by_name_ci(self, name: str) -> Supplier | None:
        key = normalize_key_ci(name, MAX_NAME_LEN)
        if not key:
            return None
        return (
            self.db.execute(
                select(Supplier).where(func.lower(func.btrim(Supplier.name)) == key).limit(1)
            )
            .scalars()
            .first()
        )

    def create(self, data: SupplierCreate) -> Supplier:
        shown = normalize_simple((data.name or ""), MAX_NAME_LEN)
        key = normalize_key_ci(shown, MAX_NAME_LEN)
        if not key:
            raise InvalidArgument("Supplier name is empty")

        existing = self._get_by_name_ci(shown)
        if existing:
            # mantém idempotência se o nome já existe
            return existing

        e = Supplier(
            name=shown,
            active=data.active if data.active is not None else True,
            logo_image=(data.logo_image or None),
            contact_name=(data.contact_name or None),
            contact_email=(data.contact_email or None),
            contact_phone=(data.contact_phone or None),
            margin=(data.margin or 0.0),
            country=(data.country or None),
        )
        self.db.add(e)
        try:
            self.db.flush()
            return e
        except IntegrityError:
            # corrida entre lookup e flush
            self.db.rollback()
            again = self._get_by_name_ci(shown)
            if again:
                return again
            raise

    def add(self, entity: Supplier) -> None:
        if not entity.name:
            raise InvalidArgument("Supplier name is empty")
        self.db.add(entity)
        self.db.flush()

    def delete(self, entity: Supplier) -> None:
        self.db.delete(entity)
        # flush/commit ficam ao cargo do UoW

    def update(
        self,
        id_supplier: int,
        *,
        name: str | None = None,
        active: bool | None = None,
        logo_image: str | None = None,
        contact_name: str | None = None,
        contact_email: str | None = None,
        contact_phone: str | None = None,
        margin: float | None = None,
        country: str | None = None,
        ingest_enabled: bool | None = None,
        ingest_interval_minutes: int | None = None,
        ingest_next_run_at: datetime | None = None,
    ) -> Supplier:
        s = self.db.get(Supplier, id_supplier)
        if not s:
            raise Conflict("Supplier not found")

        if name is not None:
            shown = normalize_simple(name, MAX_NAME_LEN)
            key = normalize_key_ci(name, MAX_NAME_LEN)
            if not key:
                raise InvalidArgument("Supplier name is empty")
            other = self._get_by_name_ci(shown)
            if other and other.id != s.id:
                raise InvalidArgument("Supplier name already exists")
            s.name = shown

        if active is not None:
            s.active = active
        if logo_image is not None:
            s.logo_image = logo_image or None
        if contact_name is not None:
            s.contact_name = contact_name or None
        if contact_email is not None:
            s.contact_email = contact_email or None
        if contact_phone is not None:
            s.contact_phone = contact_phone or None
        if margin is not None:
            s.margin = margin
        if country is not None:
            s.country = country or None
        if ingest_enabled is not None:
            s.ingest_enabled = ingest_enabled
        if ingest_interval_minutes is not None:
            s.ingest_interval_minutes = ingest_interval_minutes
        if ingest_next_run_at is not None:
            s.ingest_next_run_at = ingest_next_run_at

        self.db.flush()
        return s
