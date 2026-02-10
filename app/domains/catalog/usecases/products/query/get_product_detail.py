# app/domains/catalog/usecases/products/get_product_detail.py
from app.infra.uow import UoW
from app.schemas.products import ProductDetailOut
from app.domains.catalog.services.product_detail import get_product_detail, DetailOptions


def execute(uow: UoW, *, id_product: int, **kwargs) -> ProductDetailOut:
    return get_product_detail(uow, id_product=id_product, opts=DetailOptions(**kwargs))
