from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any
from collections.abc import Sequence

from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session

from app.models.supplier import Supplier as S
from app.models.product_supplier_event import ProductSupplierEvent as PSE


class ProductEventReadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id_event: int) -> PSE | None:
        return self.db.get(PSE, id_event)

    def list_by_product(
        self,
        id_product: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[PSE]:
        stmt = (
            select(PSE)
            .where(PSE.id_product == id_product)
            .order_by(desc(PSE.created_at), desc(PSE.id))
            .limit(limit)
            .offset(offset)
        )
        return self.db.scalars(stmt).all()

    def list_recent_for_supplier(
        self,
        id_supplier: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[PSE]:
        stmt = (
            select(PSE)
            .where(PSE.id_supplier == id_supplier)
            .order_by(desc(PSE.created_at), desc(PSE.id))
            .limit(limit)
            .offset(offset)
        )
        return self.db.scalars(stmt).all()

    def last_for_product_supplier(
        self,
        *,
        id_product: int,
        id_supplier: int,
    ) -> PSE | None:
        stmt = (
            select(PSE)
            .where(
                PSE.id_product == id_product,
                PSE.id_supplier == id_supplier,
            )
            .order_by(desc(PSE.created_at), desc(PSE.id))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def count_by_run(self, id_feed_run: int) -> int:
        stmt = select(func.count()).select_from(PSE).where(PSE.id_feed_run == id_feed_run)
        return int(self.db.scalar(stmt) or 0)

    def list_events_for_product(
        self,
        id_product: int,
        *,
        days: int | None = 90,
        limit: int | None = 2000,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                PSE.created_at,
                PSE.reason,
                PSE.price,
                PSE.stock,
                PSE.id_supplier,
                S.name.label("supplier_name"),
                PSE.id_feed_run,
            )
            .join(S, S.id == PSE.id_supplier, isouter=True)
            .where(PSE.id_product == id_product)
            .order_by(PSE.created_at.asc())
        )
        if days and days > 0:
            since = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(PSE.created_at >= since)
        if limit and limit > 0:
            stmt = stmt.limit(limit)
        return [dict(r._mapping) for r in self.db.execute(stmt).all()]

    def list_events_for_product_supplier(
        self,
        *,
        id_product: int,
        id_supplier: int,
        since: datetime | None = None,
        limit: int | None = 200,
    ) -> list[dict[str, Any]]:
        """
        Eventos para um par (produto, fornecedor), mais recentes primeiro.
        Usado para calcular old/new price.
        """
        stmt = (
            select(
                PSE.created_at,
                PSE.reason,
                PSE.price,
                PSE.stock,
                PSE.id_supplier,
                S.name.label("supplier_name"),
                PSE.id_feed_run,
            )
            .join(S, S.id == PSE.id_supplier, isouter=True)
            .where(PSE.id_product == id_product)
            .where(PSE.id_supplier == id_supplier)
            .order_by(PSE.created_at.desc())
        )
        if since is not None:
            stmt = stmt.where(PSE.created_at >= since)
        if limit and limit > 0:
            stmt = stmt.limit(limit)
        return [dict(r._mapping) for r in self.db.execute(stmt).all()]
