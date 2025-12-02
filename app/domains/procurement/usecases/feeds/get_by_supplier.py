# app/domains/procurement/usecases/feeds/get_by_supplier.py
from __future__ import annotations

from app.core.errors import NotFound
from app.repositories.procurement.read.supplier_feed_read_repo import SupplierFeedReadRepository
from app.infra.uow import UoW
from app.schemas.feeds import SupplierFeedOut


def execute(uow: UoW, *, id_supplier: int) -> SupplierFeedOut:
    db = uow.db
    repo = SupplierFeedReadRepository(db)
    e = repo.get_by_supplier(id_supplier)
    if not e:
        raise NotFound("Feed not found")
    return SupplierFeedOut.from_entity(e)
