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
from app.infra.uow import UoW
from app.schemas.products import (
    ProductDetailOut,
    ProductFacetsOut,
    ProductListOut,
    ProductMarginUpdate,
    ProductPriceChangeListOut,
)

router = APIRouter(
    prefix="/products", tags=["products"], dependencies=[Depends(require_access_token)]
)
log = logging.getLogger("gsm.api.products")

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
    sort: Literal["recent", "name", "cheapest"] = Query("recent"),
    expand_offers: bool = Query(True),
):
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
)
def update_product_margin(
    id_product: int = Path(..., ge=1),
    payload: ProductMarginUpdate = ...,
    uow: UowDep = None,
    expand_meta: bool = Query(True),
    expand_offers: bool = Query(True),
    expand_events: bool = Query(True),
    events_days: int | None = Query(90, ge=1, le=3650),
    events_limit: int | None = Query(2000, ge=1, le=100000),
    aggregate_daily: bool = Query(True),
) -> ProductDetailOut:
    """
    Atualiza a margem de um produto e devolve o detalhe atualizado.

    Mantemos as mesmas flags de expansão do GET /products/{id_product}
    para poderes reutilizar este endpoint no frontend sem teres de re-fetchar
    o detalhe numa segunda chamada.
    """
    return uc_update_product_margin(
        uow,
        id_product=id_product,
        margin=payload.margin,
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
