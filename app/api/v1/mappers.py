# app/api/v1/mappers.py
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.deps import get_uow, require_access_token
from app.domains.mapping.engine import supported_ops_for_api
from app.domains.procurement.usecases.mappers.query.get_by_supplier import (
    execute as uc_q_mapper_by_supplier,
)
from app.domains.procurement.usecases.mappers.query.get_mapper import execute as uc_get_mapper
from app.domains.procurement.usecases.mappers.command.validate_mapper import (
    execute as uc_validate,
)
from app.domains.procurement.usecases.mappers.command.put_mapper import execute as uc_put_mapper
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
log = logging.getLogger(__name__)
UowDep = Annotated[UoW, Depends(get_uow)]


@router.get(
    "/feed/{id_feed}",
    response_model=FeedMapperOut,
    summary="Obter mapper de um feed",
)
def get_mapper(id_feed: int, uow: UowDep):
    """
    Retorna a configuração do mapper associado a um feed.
    O mapper define como os campos do feed são mapeados para os campos do sistema.
    """
    return uc_get_mapper(uow, id_feed=id_feed)


@router.get(
    "/supplier/{id_supplier}",
    response_model=FeedMapperOut,
    summary="Obter mapper por fornecedor",
)
def get_mapper_by_supplier(id_supplier: int, uow: UowDep):
    """
    Retorna o mapper do feed principal de um fornecedor.
    Atalho conveniente para não ter de saber o id_feed.
    """
    return uc_q_mapper_by_supplier(uow, id_supplier=id_supplier)


@router.post(
    "/feed/{id_feed}/validate",
    response_model=MapperValidateOut,
    summary="Validar configuração de mapper",
)
def validate_mapper(id_feed: int, *, payload: MapperValidateIn, uow: UowDep):
    """
    Valida uma configuração de mapper sem a guardar.
    Verifica se as expressões são válidas e se os campos de destino existem.
    Retorna erros de validação encontrados.
    """
    return uc_validate(uow, id_feed=id_feed, payload=payload)


@router.put(
    "/feed/{id_feed}",
    response_model=FeedMapperOut,
    summary="Criar ou atualizar mapper de feed",
)
def upsert_mapper_for_feed(
    id_feed: int = Path(..., ge=1),
    *,
    payload: FeedMapperUpsert,
    uow: UowDep,
):
    """
    Cria ou atualiza o mapper de um feed.
    Define as regras de transformação dos dados do feed para o sistema.
    """
    return uc_put_mapper(uow, id_feed=id_feed, payload=payload)


@router.get(
    "/ops",
    response_model=MappingOpsOut,
    summary="Listar operações de mapeamento suportadas",
)
def list_ops() -> MappingOpsOut:
    """
    Lista todas as operações de transformação disponíveis para mappers.
    Cada operação inclui nome, descrição e parâmetros aceites.
    """
    return MappingOpsOut(ops=supported_ops_for_api())
