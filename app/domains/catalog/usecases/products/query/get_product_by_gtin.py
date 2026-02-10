# app/domains/catalog/usecases/products/get_product_by_gtin.py
# Obtém detalhe de produto por GTIN

from app.infra.uow import UoW
from app.core.errors import NotFound
from app.domains.catalog.services.product_detail import get_product_detail, DetailOptions
from app.schemas.products import ProductDetailOut


def execute(uow: UoW, *, gtin: str, **kwargs) -> ProductDetailOut:
    """Obtém informação detalhada de um produto por código GTIN/EAN."""
    gtin = (gtin or "").strip()
    if not gtin:
        raise NotFound("GTIN inválido.")

    pid = uow.products.get_id_by_gtin(gtin)
    if not pid:
        raise NotFound(f"Produto com GTIN {gtin} não encontrado.")

    return get_product_detail(uow, id_product=pid, opts=DetailOptions(**kwargs))
