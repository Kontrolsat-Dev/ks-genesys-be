from __future__ import annotations
from datetime import datetime
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel
import json

if TYPE_CHECKING:
    from app.models.feed_mapper import FeedMapper


class FeedMapperOut(BaseModel):
    id: int
    id_feed: int
    profile: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, e: FeedMapper) -> FeedMapperOut:
        try:
            profile = json.loads(e.profile_json) if getattr(e, "profile_json", None) else {}
        except Exception:
            profile = {}
        return cls(
            id=e.id,
            id_feed=e.id_feed,
            profile=profile,
            version=e.version,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class FeedMapperUpsert(BaseModel):
    profile: dict[str, Any]
    bump_version: bool = True


class MapperValidateIn(BaseModel):
    profile: dict[str, Any] | None = None
    headers: list[str] | None = None


class MapperValidateOut(BaseModel):
    ok: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    required_coverage: dict[str, Any]
    headers_checked: bool


class MappingOpOut(BaseModel):
    """Operação suportada pelo motor de mapeamento."""

    op: str
    label: str
    arity: int
    input: str


class MappingOpsOut(BaseModel):
    """Lista de operações suportadas para condições no mapper."""

    ops: list[MappingOpOut]
