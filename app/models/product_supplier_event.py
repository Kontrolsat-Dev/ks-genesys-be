# app/models/product_supplier_event.py
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.base import Base, utcnow


class ProductSupplierEvent(Base):
    __tablename__ = "products_suppliers_events"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_pse_stock_nonneg"),
        Index("ix_pse_product_created", "id_product", "created_at"),
        Index("ix_pse_supplier_product", "id_supplier", "id_product"),
        Index("ix_pse_gtin_created", "gtin", "created_at"),
        Index(
            "ix_pse_stock_positive",
            "id_product",
            "created_at",
            postgresql_where=text("stock > 0"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_product: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    id_supplier: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), index=True
    )

    price: Mapped[str] = mapped_column(String(40), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)

    gtin: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_feed_run: Mapped[int | None] = mapped_column(
        ForeignKey("feed_runs.id", ondelete="SET NULL"), nullable=True
    )

    reason: Mapped[str] = mapped_column(
        String(30), default="init", nullable=False
    )  # init|change|eol
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    product = relationship("Product", back_populates="supplier_events")
