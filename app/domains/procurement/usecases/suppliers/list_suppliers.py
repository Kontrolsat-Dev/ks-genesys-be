# app/domains/procurement/usecases/suppliers/list_suppliers.py
"""
UseCase para listar fornecedores com paginação e pesquisa.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.schemas.suppliers import SupplierList, SupplierOut


def execute(uow: UoW, *, search: str | None, page: int, page_size: int) -> SupplierList:
    """
    Lista fornecedores com paginação e pesquisa opcional.

    Returns:
        SupplierList schema
    """
    items, total = uow.suppliers.search_paginated(search, page, page_size)

    return SupplierList(
        items=[SupplierOut.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
    )
