# app/schemas/feeds.py
from __future__ import annotations
from datetime import datetime
from typing import Any, TYPE_CHECKING
import json
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.supplier_feed import SupplierFeed


class SupplierFeedCreate(BaseModel):
    kind: str
    format: str
    url: str
    active: bool = True
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    auth_kind: str | None = None
    auth: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None
    csv_delimiter: str | None = ","


class SupplierFeedUpdate(SupplierFeedCreate):
    pass


class SupplierFeedOut(BaseModel):
    id: int
    id_supplier: int
    kind: str
    format: str
    url: str
    active: bool
    headers_json: str | None
    params_json: str | None
    auth_kind: str | None
    auth_json: str | None
    extra_json: str | None
    csv_delimiter: str | None
    has_auth: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, e: SupplierFeed) -> SupplierFeedOut:
        has_auth = False
        try:
            parsed = json.loads(e.auth_json) if getattr(e, "auth_json", None) else {}
            has_auth = bool(parsed)
        except Exception:
            has_auth = False
        return cls(
            id=e.id,
            id_supplier=e.id_supplier,
            kind=e.kind,
            format=e.format,
            url=e.url,
            active=e.active,
            headers_json=getattr(e, "headers_json", None),
            params_json=getattr(e, "params_json", None),
            auth_kind=getattr(e, "auth_kind", None),
            auth_json=getattr(e, "auth_json", None),
            extra_json=getattr(e, "extra_json", None),
            csv_delimiter=(getattr(e, "csv_delimiter", None) or ","),
            has_auth=has_auth,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class FeedTestRequest(BaseModel):
    kind: str | None = None
    format: str
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    auth_kind: str | None = None
    auth: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None
    csv_delimiter: str | None = ","
    max_rows: int | None = 20


class FeedTestResponse(BaseModel):
    ok: bool
    status_code: int
    content_type: str | None
    bytes_read: int
    preview_type: str | None  # "json"|"csv"|None
    rows_preview: list[dict[str, Any]] | None
    error: str | None = None
