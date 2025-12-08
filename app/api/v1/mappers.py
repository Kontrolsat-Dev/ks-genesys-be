# app/api/v1/mappers.py
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.deps import get_uow, require_access_token
from app.domains.mapping.engine import supported_ops_for_api
from app.domains.procurement.usecases.mappers.get_by_supplier import (
    execute as uc_q_mapper_by_supplier,
)
from app.domains.procurement.usecases.mappers.get_mapper import execute as uc_get_mapper
from app.domains.procurement.usecases.mappers.validate_mapper import (
    execute as uc_validate,
)
from app.domains.procurement.usecases.mappers.put_mapper import execute as uc_put_mapper
from app.infra.uow import UoW
from app.schemas.mappers import (
    MapperValidateIn,
    MapperValidateOut,
    FeedMapperOut,
    FeedMapperUpsert,
    MappingOpsOut,
)

router = APIRouter(
    prefix="/mappers", tags=["mappers"], dependencies=[Depends(require_access_token)]
)
log = logging.getLogger("gsm.api.mappers")
UowDep = Annotated[UoW, Depends(get_uow)]


@router.get(
    "/feed/{id_feed}",
    response_model=FeedMapperOut,
)
def get_mapper(id_feed: int, uow: UowDep):
    return uc_get_mapper(uow, id_feed=id_feed)


@router.get(
    "/supplier/{id_supplier}",
    response_model=FeedMapperOut,
)
def get_mapper_by_supplier(id_supplier: int, uow: UowDep):
    return uc_q_mapper_by_supplier(uow, id_supplier=id_supplier)


@router.post(
    "/feed/{id_feed}/validate",
    response_model=MapperValidateOut,
)
def validate_mapper(id_feed: int, *, payload: MapperValidateIn, uow: UowDep):
    return uc_validate(uow, id_feed=id_feed, payload=payload)


@router.put(
    "/feed/{id_feed}",
    response_model=FeedMapperOut,
)
def upsert_mapper_for_feed(
    id_feed: int = Path(..., ge=1),
    *,
    payload: FeedMapperUpsert,
    uow: UowDep,
):
    return uc_put_mapper(uow, id_feed=id_feed, payload=payload)


@router.get(
    "/ops",
    response_model=MappingOpsOut,
)
def list_ops() -> MappingOpsOut:
    return MappingOpsOut(ops=supported_ops_for_api())
