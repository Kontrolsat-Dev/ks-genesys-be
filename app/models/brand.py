# app/models/brand.py
from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.base import Base, utcnow


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_brands_name_ci", func.lower(func.btrim(name))),
        Index("ux_brands_name_ci", func.lower(func.btrim(name)), unique=True),
    )
