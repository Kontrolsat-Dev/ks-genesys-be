# app/domains/procurement/usecases/feeds/upsert_supplier_feed.py
from __future__ import annotations
import json

from app.infra.uow import UoW
from app.repositories.procurement.write.supplier_feed_write_repo import SupplierFeedWriteRepository
from app.schemas.feeds import SupplierFeedCreate, SupplierFeedUpdate, SupplierFeedOut


def execute(
    uow: UoW, *, id_supplier: int, data: SupplierFeedCreate | SupplierFeedUpdate
) -> SupplierFeedOut:
    def mutate(e):
        db = uow.db

        for f in ("kind", "format", "url", "active", "csv_delimiter"):
            v = getattr(data, f, None)
            if v is not None:
                setattr(e, f, v)
        if getattr(data, "headers", None) is not None:
            e.headers_json = (
                None if data.headers is None else json.dumps(data.headers, ensure_ascii=False)
            )
        if getattr(data, "params", None) is not None:
            e.params_json = (
                None if data.params is None else json.dumps(data.params, ensure_ascii=False)
            )
        if getattr(data, "extra", None) is not None:
            e.extra_json = (
                None if data.extra is None else json.dumps(data.extra, ensure_ascii=False)
            )
        if getattr(data, "auth_kind", None) is not None:
            e.auth_kind = data.auth_kind or None
        if getattr(data, "auth", None) is not None:
            e.auth_json = None if data.auth is None else json.dumps(data.auth, ensure_ascii=False)

        repo = SupplierFeedWriteRepository(db)
        entity = repo.upsert_for_supplier(id_supplier, mutate)
        uow.commit()
        return SupplierFeedOut.from_entity(entity)
