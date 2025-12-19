# app/models/category.py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.base import Base, utcnow


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    # Fornecedor que criou a categoria (primeiro a usar)
    id_supplier_source: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True, index=True
    )
    supplier_source = relationship("Supplier", foreign_keys=[id_supplier_source])

    # Mapeamento PrestaShop
    id_ps_category: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ps_category_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_import: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_import_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_categories_name_ci", func.lower(func.btrim(name))),
        Index("ux_categories_name_ci", func.lower(func.btrim(name)), unique=True),
    )
