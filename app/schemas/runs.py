from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FeedRunOut(BaseModel):
    id: int
    id_feed: int
    # Supplier info (joined from feed -> supplier)
    supplier_id: int | None = None
    supplier_name: str | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    rows_total: int
    rows_changed: int  # Note: This is item-level changes, can exceed rows_total
    rows_failed: int = 0
    rows_unseen: int = 0
    http_status: int | None = None
    duration_ms: int | None = None
    error_msg: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FeedRunListOut(BaseModel):
    items: list[FeedRunOut]
    total: int
    page: int
    page_size: int
