# app/models/feed_run.py

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.base import Base, utcnow
from app.models.enums import RUN_STATUS


class FeedRun(Base):
    __tablename__ = "feed_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_feed: Mapped[int] = mapped_column(
        Integer, ForeignKey("supplier_feeds.id", ondelete="CASCADE"), index=True
    )

    started_at: Mapped[DateTime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime, default=None)
    status: Mapped[str] = mapped_column(RUN_STATUS, default="running", nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, default=None)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_changed: Mapped[int] = mapped_column(Integer, default=0)
    rows_failed: Mapped[int] = mapped_column(Integer, default=0)
    rows_unseen: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    error_msg: Mapped[str | None] = mapped_column(Text, default=None)

    feed = relationship("SupplierFeed", back_populates="runs")
