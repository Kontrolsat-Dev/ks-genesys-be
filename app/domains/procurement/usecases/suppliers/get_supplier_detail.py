# app/domains/procurement/usecases/suppliers/get_supplier_detail.py
from __future__ import annotations

import json

from app.core.errors import NotFound  # << usar AppError
from app.infra.uow import UoW
from app.repositories.procurement.read.mapper_read_repo import MapperReadRepository
from app.repositories.procurement.read.supplier_feed_read_repo import (
    SupplierFeedReadRepository,
)
from app.repositories.procurement.read.supplier_read_repo import SupplierReadRepository
from app.schemas.feeds import SupplierFeedOut
from app.schemas.mappers import FeedMapperOut
from app.schemas.suppliers import SupplierDetailOut, SupplierOut


def _supplier_to_out(s) -> SupplierOut:
    return SupplierOut(
        id=s.id,
        name=s.name,
        active=s.active,
        logo_image=s.logo_image,
        contact_name=s.contact_name,
        contact_phone=s.contact_phone,
        contact_email=s.contact_email,
        margin=s.margin,
        country=s.country,
        discount=s.discount,
        created_at=s.created_at,
        updated_at=s.updated_at,
        ingest_enabled=s.ingest_enabled,
        ingest_next_run_at=s.ingest_next_run_at,
        ingest_interval_minutes=s.ingest_interval_minutes,
    )


def _feed_to_out(f) -> SupplierFeedOut | None:
    if not f:
        return None
    return SupplierFeedOut.model_validate(
        {
            "id": f.id,
            "id_supplier": f.id_supplier,
            "kind": f.kind,
            "format": f.format,
            "url": f.url,
            "active": f.active,
            "csv_delimiter": f.csv_delimiter or ",",  # default consistente
            "headers_json": getattr(f, "headers_json", None),
            "params_json": getattr(f, "params_json", None),
            "extra_json": getattr(f, "extra_json", None),
            "auth_kind": getattr(f, "auth_kind", None),
            "auth_json": getattr(f, "auth_json", None),
            "has_auth": bool(getattr(f, "auth_json", None)),
            "created_at": f.created_at,
            "updated_at": f.updated_at,
        }
    )


def _mapper_to_out(m) -> FeedMapperOut | None:
    if not m:
        return None
    try:
        profile = json.loads(m.profile_json) if getattr(m, "profile_json", None) else {}
    except Exception:
        profile = {}
    return FeedMapperOut(
        id=m.id,
        id_feed=m.id_feed,
        profile=profile,
        version=m.version or 1,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def execute(uow: UoW, *, id_supplier: int) -> SupplierDetailOut:
    db = uow.db
    sup_repo = SupplierReadRepository(db)
    feed_repo = SupplierFeedReadRepository(db)
    map_repo = MapperReadRepository(db)

    s = sup_repo.get(id_supplier)
    if not s:
        raise NotFound("Supplier not found")  # << em vez de HTTPException

    f = feed_repo.get_by_supplier(id_supplier)
    m = map_repo.get_by_feed(f.id) if f else None

    return SupplierDetailOut(
        supplier=_supplier_to_out(s),
        feed=_feed_to_out(f),
        mapper=_mapper_to_out(m),
    )
