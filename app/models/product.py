# app/models/product.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.base import Base, utcnow

if TYPE_CHECKING:
    from .product_meta import ProductMeta
    from .product_supplier_event import ProductSupplierEvent
    from .product_active_offer import ProductActiveOffer


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gtin: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)

    id_ecommerce: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    id_brand: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    id_category: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    partnumber: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    margin: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False, default=0)

    # Taxas adicionais
    ecotax: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)  # Remover
    extra_fees: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_eol: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_str: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    meta: Mapped[list[ProductMeta]] = relationship(
        "ProductMeta", back_populates="product", cascade="all,delete-orphan"
    )
    supplier_events: Mapped[list[ProductSupplierEvent]] = relationship(
        "ProductSupplierEvent", back_populates="product", cascade="all,delete-orphan"
    )

    active_offer: Mapped[ProductActiveOffer | None] = relationship(
        "ProductActiveOffer",
        back_populates="product",
        uselist=False,
        cascade="all,delete-orphan",
    )

    __table_args__ = (
        # 1) GTIN único quando não é NULL
        Index(
            "uq_products_gtin_not_null",
            "gtin",
            unique=True,
            postgresql_where=text("gtin IS NOT NULL"),
        ),
        # 2) brand+MPN únicos **apenas** quando NÃO há GTIN
        Index(
            "uq_products_brand_mpn",
            "id_brand",
            "partnumber",
            unique=True,
            postgresql_where=text(
                "gtin IS NULL AND id_brand IS NOT NULL AND partnumber IS NOT NULL"
            ),
        ),
    )
