# app/api/v1/suppliers.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import get_uow, require_access_token
from app.domains.procurement.usecases.suppliers.create_supplier import (
    execute as uc_create,
)
from app.domains.procurement.usecases.suppliers.delete_supplier import (
    execute as uc_delete,
)
from app.domains.procurement.usecases.suppliers.get_supplier_detail import (
    execute as uc_q_detail,
)
from app.domains.procurement.usecases.suppliers.list_suppliers import (
    execute as uc_q_list,
)
from app.domains.procurement.usecases.suppliers.update_bundle import (
    execute as uc_update,
)
from app.infra.uow import UoW
from app.schemas.suppliers import (
    SupplierBundleUpdate,
    SupplierCreate,
    SupplierDetailOut,
    SupplierList,
    SupplierOut,
)

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(require_access_token)],
)
UowDep = Annotated[UoW, Depends(get_uow)]


@router.get("", response_model=SupplierList)
def list_suppliers(
    uow: UowDep,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    items, total = uc_q_list(uow, search=search, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{id_supplier}", response_model=SupplierDetailOut)
def get_supplier_detail(id_supplier: int, uow: UowDep):
    return uc_q_detail(uow, id_supplier=id_supplier)


@router.post(
    "",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_access_token)],
)
def create_supplier(payload: SupplierCreate, uow: UowDep):
    return uc_create(uow, data=payload)


@router.put("/{id_supplier}", response_model=SupplierDetailOut)
def update_supplier_bundle(
    uow: UowDep,
    id_supplier: int = Path(..., ge=1),
    payload: SupplierBundleUpdate = ...,
):
    return uc_update(uow, id_supplier=id_supplier, payload=payload)


@router.delete("/{id_supplier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier_endpoint(id_supplier: int, uow: UowDep):
    uc_delete(uow, id_supplier=id_supplier)
    return
