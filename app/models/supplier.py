# app/models/Supplier.py
# SQLAlchemy model for Supplier entity

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.supplier_feed import SupplierFeed


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    logo_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(250), nullable=True)
    margin: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False, default=0)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Scheduling de ingest
    ingest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ingest_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    ingest_next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=utcnow, nullable=True)

    feeds: Mapped[list["SupplierFeed"]] = relationship(
        back_populates="supplier", cascade="all,delete-orphan"
    )
