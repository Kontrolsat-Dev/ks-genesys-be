# app/domains/catalog/usecases/products/get_product_facets.py
# Devolve facets (marcas/categorias/fornecedores) válidos para os filtros atuais

from app.infra.uow import UoW
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
    """
    Devolve listas de IDs (brand_ids, category_ids, supplier_ids) que têm
    pelo menos um produto compatível com os filtros fornecidos.
    """
    brand_ids, category_ids, supplier_ids = uow.products.get_facets(
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
