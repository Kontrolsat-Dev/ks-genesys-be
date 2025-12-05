# app/domains/catalog/usecases/products/get_product_facets.py

from app.infra.uow import UoW
from app.repositories.catalog.read.products_read_repo import ProductsReadRepository
from app.schemas.products import ProductFacetsOut


def execute(
    uow: UoW,
    *,
    q: str | None = None,
    gtin: str | None = None,
    partnumber: str | None = None,
    id_brand: int | None = None,
    brand: str | None = None,
    id_category: int | None = None,
    category: str | None = None,
    has_stock: bool | None = None,
    id_supplier: int | None = None,
) -> ProductFacetsOut:
    db = uow.db
    repo = ProductsReadRepository(db)

    brand_ids, category_ids, supplier_ids = repo.get_facets(
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

    return ProductFacetsOut(
        brand_ids=brand_ids,
        category_ids=category_ids,
        supplier_ids=supplier_ids,
    )
