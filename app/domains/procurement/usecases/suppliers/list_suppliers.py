from __future__ import annotations

from collections.abc import Sequence

from app.infra.uow import UoW
from app.models.supplier import Supplier
from app.repositories.procurement.read.supplier_read_repo import SupplierReadRepository


def execute(
    uow: UoW, *, search: str | None, page: int, page_size: int
) -> tuple[Sequence[Supplier], int]:
    db = uow.db
    repo = SupplierReadRepository(db)
    return repo.search_paginated(search, page, page_size)
