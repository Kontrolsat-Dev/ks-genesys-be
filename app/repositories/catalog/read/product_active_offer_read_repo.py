# app/repositories/catalog/read/product_active_offer_read_repo.py
from __future__ import annotations

from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.category import Category
from app.models.brand import Brand
from app.models.product_active_offer import ProductActiveOffer


class ProductActiveOfferReadRepository:
    """
    Operações de leitura para a oferta ativa de um produto.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_product(self, id_product: int) -> ProductActiveOffer | None:
        if not id_product:
            return None
        stmt = select(ProductActiveOffer).where(ProductActiveOffer.id_product == id_product)
        return self.db.scalar(stmt)

    def get(self, id_offer: int) -> ProductActiveOffer | None:
        return self.db.get(ProductActiveOffer, id_offer)

    def list_for_products(self, ids: list[int]) -> dict[int, ProductActiveOffer]:
        """
        Devolve um mapa {id_product: ProductActiveOffer} para uma lista de produtos.
        Útil para listagens em batch.
        """
        if not ids:
            return {}
        stmt = select(ProductActiveOffer).where(ProductActiveOffer.id_product.in_(ids))
        rows = self.db.scalars(stmt).all()
        return {row.id_product: row for row in rows}

    def list_with_product_info(self) -> list[dict[str, Any]]:
        """
        Lista todas as active_offers com info de produto (nome, marca, categoria, margem).
        Usado para calcular alterações de preço da active_offer.
        """
        stmt = (
            select(
                ProductActiveOffer.id_product,
                ProductActiveOffer.id_supplier,
                ProductActiveOffer.unit_cost,
                ProductActiveOffer.unit_price_sent,
                Product.margin,
                Product.name,
                Brand.name.label("brand_name"),
                Category.name.label("category_name"),
            )
            .join(Product, Product.id == ProductActiveOffer.id_product)
            .join(Brand, Brand.id == Product.id_brand, isouter=True)
            .join(Category, Category.id == Product.id_category, isouter=True)
        )

        rows = self.db.execute(stmt).all()
        return [dict(row._mapping) for row in rows]
