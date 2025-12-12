# app/repositories/read/feed_run_read_repo.py
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload
from app.core.errors import NotFound
from app.models.feed_run import FeedRun
from app.models.supplier_feed import SupplierFeed


class FeedRunReadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id_run: int) -> FeedRun | None:
        return self.db.get(FeedRun, id_run)

    def get_required(self, id_run: int) -> FeedRun:
        run = self.get(id_run)
        if not run:
            raise NotFound("Run not found")
        return run

    def list(self, page: int = 1, page_size: int = 50) -> tuple[list[FeedRun], int]:
        query = self.db.query(FeedRun).options(
            joinedload(FeedRun.feed).joinedload(SupplierFeed.supplier)
        )
        total = self.db.query(FeedRun).count()
        items = (
            query.order_by(FeedRun.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        )
        return items, total
