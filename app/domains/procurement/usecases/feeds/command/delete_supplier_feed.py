# app/domains/procurement/usecases/feeds/delete_supplier_feed.py
from __future__ import annotations
from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict, NotFound
from app.repositories.procurement.read.supplier_feed_read_repo import SupplierFeedReadRepository
from app.repositories.procurement.write.supplier_feed_write_repo import SupplierFeedWriteRepository
from app.infra.uow import UoW


def execute(uow: UoW, *, id_supplier: int) -> None:
    db = uow.db
    rread = SupplierFeedReadRepository(db)
    rwrite = SupplierFeedWriteRepository(db)

    feed = rread.get_by_supplier(id_supplier)
    if not feed:
        raise NotFound("Feed not found for supplier")

    try:
        rwrite.delete(feed)  # aceita a entity
        uow.commit()
    except IntegrityError as err:
        uow.rollback()
        raise Conflict("Cannot delete feed due to integrity constraints") from err
