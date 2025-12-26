# app/schemas/audit.py
"""
Schemas para API de audit logs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    event_type: str
    entity_type: str | None
    entity_id: int | None
    actor_id: str | None
    actor_name: str | None
    description: str | None
    details: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int


class EventTypesResponse(BaseModel):
    event_types: list[str]
