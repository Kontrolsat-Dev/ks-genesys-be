from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Query, Path
from typing import Annotated, Literal

from app.core.deps import get_uow, require_access_token
from app.domains.catalog.usecases.products.get_product_by_gtin import (
    execute as uc_q_product_detail_by_gtin,
)
from app.domains.catalog.usecases.products.get_product_detail import (
    execute as uc_q_product_detail,
)
from app.domains.catalog.usecases.products.list_products import (
    execute as uc_q_list_products,
)
from app.domains.catalog.usecases.products.update_margin import (
    execute as uc_update_product_margin,
)
from app.domains.catalog.usecases.products.list_active_offer_price_changes import (
    execute as uc_list_active_offer_price_changes,
)
from app.domains.catalog.usecases.products.list_catalog_price_changes import (
    execute as uc_list_catalog_price_changes,
)
from app.domains.catalog.usecases.products.get_product_facets import (
    execute as uc_get_product_facets,
)
from app.domains.catalog.usecases.products.import_to_prestashop import execute as uc_import_product
from app.domains.catalog.usecases.products import bulk_import as uc_bulk_import
from app.infra.uow import UoW
from app.schemas.products import (
    ProductDetailOut,
    ProductFacetsOut,
    ProductListOut,
    ProductMarginUpdate,
    ProductPriceChangeListOut,
    ProductImportIn,
    ProductImportOut,
    BulkImportIn,
    BulkImportOut,
)
from app.core.deps import get_prestashop_client
from app.external.prestashop_client import PrestashopClient

router = APIRouter(
    prefix="/products", tags=["products"], dependencies=[Depends(require_access_token)]
)
log = logging.getLogger(__name__)

# Aqui está o Depends já embutido
UowDep = Annotated[UoW, Depends(get_uow)]


@router.get(
    "",
    summary="Get Product List",
    response_model=ProductListOut,
)
def list_products(
    uow: UowDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    gtin: str | None = Query(None),
    partnumber: str | None = Query(None),
    id_brand: int | None = Query(None),
    brand: str | None = Query(None),
    id_category: int | None = Query(None),
    category: str | None = Query(None),
    has_stock: bool | None = Query(None),
    id_supplier: int | None = Query(None),
    imported: bool | None = Query(
        None, description="Filter by import status: true=imported, false=not imported"
    ),
    sort: Literal["recent", "name", "cheapest"] = Query("recent"),
    expand_offers: bool = Query(True),
) -> ProductListOut:
    """
    Lista produtos do catálogo com paginação e filtros avançados.
    Suporta pesquisa por texto, GTIN, marca, categoria, stock e fornecedor.
    Opcionalmente expande as ofertas de cada produto.
    """
    return uc_q_list_products(
        uow,
        page=page,
        page_size=page_size,
        q=q,
        gtin=gtin,
        partnumber=partnumber,
        id_brand=id_brand,
        brand=brand,
        id_category=id_category,
        category=category,
        has_stock=has_stock,
        id_supplier=id_supplier,
        imported=imported,
        sort=sort,
        expand_offers=expand_offers,
    )


@router.get(
    "/facets",
    response_model=ProductFacetsOut,
    summary="Obter facets (marcas/categorias/fornecedores) válidos para os filtros atuais",
)
def get_product_facets(
    uow: UowDep,
    q: str | None = Query(None),
    gtin: str | None = Query(None),
    partnumber: str | None = Query(None),
    id_brand: int | None = Query(None, description="Filtrar inicialmente por id_brand (opcional)"),
    brand: str | None = Query(
        None, description="Filtrar inicialmente por nome de marca (opcional)"
    ),
    id_category: int | None = Query(
        None, description="Filtrar inicialmente por id_category (opcional)"
    ),
    category: str | None = Query(
        None, description="Filtrar inicialmente por nome de categoria (opcional)"
    ),
    has_stock: bool | None = Query(
        None,
        description="true=apenas produtos com stock; false=apenas sem stock; omitido=todos",
    ),
    id_supplier: int | None = Query(
        None,
        description="Filtrar inicialmente por supplier (opcional)",
    ),
) -> ProductFacetsOut:
    """
    Devolve listas de IDs (brand_ids, category_ids, supplier_ids) que têm pelo menos
    um produto compatível com os filtros fornecidos.

    Para cada facet, o cálculo ignora o filtro dessa própria dimensão
    (ex.: para calcular brand_ids, é ignorado id_brand/brand), mas respeita
    os restantes filtros (q, categoria, supplier, stock, ...).
    """
    return uc_get_product_facets(
        uow,
        q=q,
        gtin=gtin,
        partnumber=partnumber,
        id_brand=id_brand,
        brand=brand,
        id_category=id_category,
        category=category,
        has_stock=has_stock,
        id_supplier=id_supplier,
    )


@router.post(
    "/bulk-import",
    response_model=BulkImportOut,
    summary="Importar múltiplos produtos para o PrestaShop",
)
def bulk_import_products(
    uow: UowDep,
    ps_client: Annotated[PrestashopClient, Depends(get_prestashop_client)],
    payload: BulkImportIn,
) -> BulkImportOut:
    """
    Importa múltiplos produtos para o PrestaShop em batch.

    - Produtos já importados são skipped
    - Produtos sem categoria PS mapeada falham
    - Usa a categoria PS da categoria do produto (ou override se fornecido)
    """
    result = uc_bulk_import.execute(
        uow,
        ps_client,
        product_ids=payload.product_ids,
        id_ps_category_override=payload.id_ps_category,
        category_margins=payload.category_margins,
    )
    return result


@router.get(
    "/{id_product}",
    response_model=ProductDetailOut,
    summary="Get Product Details by ID",
)
def get_product_detail(
    uow: UowDep,
    id_product: int,
    expand_meta: bool = Query(True),
    expand_offers: bool = Query(True),
    expand_events: bool = Query(True),
    events_days: int | None = Query(90, ge=1, le=3650),
    events_limit: int | None = Query(2000, ge=1, le=100000),
    aggregate_daily: bool = Query(True),
):
    """
    Obtém informação detalhada de um produto por ID.
    Inclui metadados, ofertas de fornecedores e histórico de eventos.
    Parâmetros permitem controlar que secções são expandidas.
    """
    return uc_q_product_detail(
        uow,
        id_product=id_product,
        expand_meta=expand_meta,
        expand_offers=expand_offers,
        expand_events=expand_events,
        events_days=events_days,
        events_limit=events_limit,
        aggregate_daily=aggregate_daily,
    )


@router.get(
    "/gtin/{gtin}",
    response_model=ProductDetailOut,
    summary="Get Product Detail by GTIN",
)
def get_product_detail_by_gtin(
    uow: UowDep,
    gtin: Annotated[str, Path(min_length=8, max_length=18, pattern=r"^\d{8,18}$")],
    expand_meta: bool = Query(True),
    expand_offers: bool = Query(True),
    expand_events: bool = Query(True),
    events_days: int | None = Query(90, ge=1, le=3650),
    events_limit: int | None = Query(2000, ge=1, le=100000),
    aggregate_daily: bool = Query(True),
) -> ProductDetailOut:
    """
    Obtém informação detalhada de um produto por código GTIN/EAN.
    Útil para pesquisa por código de barras.
    """
    return uc_q_product_detail_by_gtin(
        uow,
        gtin=gtin.strip(),
        expand_meta=expand_meta,
        expand_offers=expand_offers,
        expand_events=expand_events,
        events_days=events_days,
        events_limit=events_limit,
        aggregate_daily=aggregate_daily,
    )


@router.patch(
    "/{id_product}/margin",
    response_model=ProductDetailOut,
    summary="Atualizar margem de produto",
)
def update_product_margin(
    uow: UowDep,
    id_product: int = Path(..., ge=1),
    payload: ProductMarginUpdate = ...,
    expand_meta: bool = Query(True),
    expand_offers: bool = Query(True),
    expand_events: bool = Query(True),
    events_days: int | None = Query(90, ge=1, le=3650),
    events_limit: int | None = Query(2000, ge=1, le=100000),
    aggregate_daily: bool = Query(True),
) -> ProductDetailOut:
    """
    Atualiza a margem e taxas de um produto e devolve o detalhe atualizado.

    - margin: nova margem (decimal, ex: 0.20 = 20%)
    - ecotax: ecotax em EUR (enviado separadamente ao PrestaShop)
    - extra_fees: taxas adicionais em EUR (DAF, direitos, etc. - embute no preço)

    Mantemos as mesmas flags de expansão do GET /products/{id_product}
    para poderes reutilizar este endpoint no frontend sem teres de re-fetchar
    o detalhe numa segunda chamada.
    """
    return uc_update_product_margin(
        uow,
        id_product=id_product,
        margin=payload.margin,
        ecotax=payload.ecotax,
        extra_fees=payload.extra_fees,
        expand_meta=expand_meta,
        expand_offers=expand_offers,
        expand_events=expand_events,
        events_days=events_days,
        events_limit=events_limit,
        aggregate_daily=aggregate_daily,
    )


@router.get(
    "/active-offer/price-changes",
    response_model=ProductPriceChangeListOut,
    summary="Listar produtos com alterações de preço na active_offer",
)
def list_active_offer_price_changes(
    uow: UowDep,
    direction: Literal["up", "down", "both"] = Query(
        "down",
        description="Filtrar por quedas (down), subidas (up) ou ambos (both).",
    ),
    days: int = Query(
        7,
        ge=1,
        le=365,
        description="Janela temporal em dias para olhar os eventos.",
    ),
    min_abs_delta: float | None = Query(
        None,
        ge=0,
        description="Variação mínima em euros (absoluto).",
    ),
    min_pct_delta: float | None = Query(
        None,
        ge=0,
        le=1000,
        description="Variação mínima em percentagem (absoluto).",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> ProductPriceChangeListOut:
    return uc_list_active_offer_price_changes(
        uow,
        direction=direction,
        days=days,
        min_abs_delta=min_abs_delta,
        min_pct_delta=min_pct_delta,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/price-changes/catalog",
    response_model=ProductPriceChangeListOut,
    summary="Listar movimentos de preço para produtos não importados (catálogo)",
)
def list_catalog_price_changes(
    uow: UowDep,
    direction: Literal["up", "down", "both"] = Query(
        "down",
        description="up= subidas, down= quedas, both= ambos",
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Janela temporal em dias para procurar alterações",
    ),
    min_abs_delta: float | None = Query(
        0,
        ge=0,
        description="Mínimo de variação absoluta em € (0 para desligar filtro)",
    ),
    min_pct_delta: float | None = Query(
        5,
        ge=0,
        description="Mínimo de variação percentual (0 para desligar filtro)",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> ProductPriceChangeListOut:
    return uc_list_catalog_price_changes(
        uow,
        direction=direction,
        days=days,
        min_abs_delta=min_abs_delta,
        min_pct_delta=min_pct_delta,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{id_product}/import",
    response_model=ProductImportOut,
    summary="Importar produto para PrestaShop",
)
def import_product_to_prestashop(
    uow: UowDep,
    id_product: int = Path(..., ge=1),
    payload: ProductImportIn = ...,
    ps_client: PrestashopClient = Depends(get_prestashop_client),
) -> ProductImportOut:
    """
    Importa um produto para o PrestaShop.

    - Valida que o produto existe e não está já importado
    - Envia dados para a API do PrestaShop (r_genesys module)
    - Atualiza o product.id_ecommerce com o ID do PS
    """
    return uc_import_product(
        uow,
        ps_client,
        id_product=id_product,
        id_ps_category=payload.id_ps_category,
    )
