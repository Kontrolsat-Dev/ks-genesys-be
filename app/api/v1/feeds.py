# app/api/v1/feeds.py
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import get_uow, require_access_token, get_feed_downloader
from app.domains.procurement.usecases.feeds.delete_supplier_feed import (
    execute as uc_delete,
)
from app.domains.procurement.usecases.feeds.get_by_supplier import (
    execute as uc_get_feed_by_supplier,
)
from app.domains.procurement.usecases.feeds.test_feed import execute as uc_test
from app.domains.procurement.usecases.feeds.upsert_supplier_feed import (
    execute as uc_upsert,
)
from app.external.feed_downloader import FeedDownloader
from app.infra.uow import UoW
from app.schemas.feeds import (
    FeedTestRequest,
    FeedTestResponse,
    SupplierFeedCreate,
    SupplierFeedOut,
    SupplierFeedUpdate,
)

router = APIRouter(prefix="/feeds", tags=["feeds"], dependencies=[Depends(require_access_token)])
UowDep = Annotated[UoW, Depends(get_uow)]
log = logging.getLogger("gsm.api.feeds")


@router.get(
    "/supplier/{id_supplier}",
    response_model=SupplierFeedOut,
    summary="Obter feed de um fornecedor",
)
def get_supplier_feed(
    id_supplier: int,
    *,
    uow: UowDep,
):
    """
    Retorna a configuração do feed de dados de um fornecedor.
    Inclui URL, formato, frequência de atualização e estado.
    """
    return uc_get_feed_by_supplier(uow, id_supplier=id_supplier)


@router.put(
    "/supplier/{id_supplier}",
    response_model=SupplierFeedOut,
    summary="Criar ou atualizar feed de fornecedor",
)
def upsert_supplier_feed(
    id_supplier: int,
    *,
    payload: SupplierFeedCreate | SupplierFeedUpdate,
    uow: UowDep,
):
    """
    Cria ou atualiza a configuração do feed de um fornecedor.
    Se o feed não existir, cria um novo. Se existir, atualiza os campos fornecidos.
    """
    return uc_upsert(uow, id_supplier=id_supplier, data=payload)


@router.delete(
    "/supplier/{id_supplier}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar feed de fornecedor",
)
def delete_supplier_feed(
    id_supplier: int,
    *,
    uow: UowDep,
):
    """
    Remove a configuração do feed de um fornecedor.
    Isto não elimina os dados já importados, apenas a configuração do feed.
    """
    uc_delete(uow, id_supplier=id_supplier)
    return


@router.post(
    "/test",
    response_model=FeedTestResponse,
    summary="Testar configuração de feed",
)
async def test_feed(
    *,
    payload: FeedTestRequest,
    downloader: FeedDownloader = Depends(get_feed_downloader),
):
    """
    Testa a configuração de um feed sem o guardar.
    Faz download de uma amostra e valida o formato/estrutura.
    Retorna preview das primeiras linhas e erros encontrados.
    """
    return await uc_test(payload, preview_feed=downloader.preview)
