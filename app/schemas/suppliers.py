from datetime import datetime

from pydantic import BaseModel

from app.schemas.feeds import SupplierFeedOut, SupplierFeedUpdate
from app.schemas.mappers import FeedMapperOut, FeedMapperUpsert


class SupplierCreate(BaseModel):
    name: str
    active: bool = True
    logo_image: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    margin: float = 0
    discount: float = 0
    country: str | None = None
    ingest_enabled: bool = True
    ingest_interval_minutes: int | None = None
    ingest_next_run_at: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None
    logo_image: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    margin: float | None = None
    discount: float | None = None
    country: str | None = None
    ingest_enabled: bool | None = None
    ingest_interval_minutes: int | None = None
    ingest_next_run_at: datetime | None = None


class SupplierOut(BaseModel):
    id: int
    name: str
    active: bool
    logo_image: str | None
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    margin: float
    discount: float = 0
    country: str | None
    created_at: datetime
    updated_at: datetime | None
    ingest_enabled: bool = True
    ingest_interval_minutes: int | None = None
    ingest_next_run_at: datetime | None = None

    model_config = {"from_attributes": True}


class SupplierList(BaseModel):
    items: list[SupplierOut]
    total: int
    page: int
    page_size: int


class SupplierDetailOut(BaseModel):
    supplier: SupplierOut
    feed: SupplierFeedOut | None
    mapper: FeedMapperOut | None


class SupplierBundleUpdate(BaseModel):
    supplier: SupplierUpdate | None = None
    feed: SupplierFeedUpdate | None = None
    mapper: FeedMapperUpsert | None = None
