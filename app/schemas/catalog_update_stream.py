# app/schemas/catalog_update_stream.py
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator


class CatalogUpdatePayload(BaseModel):
    reason: str
    product: dict[str, Any]
    active_offer: dict[str, Any] | None = None
    shipping: dict[str, Any] | None = None


class CatalogUpdateEventOut(BaseModel):
    id: int
    id_product: int
    id_ecommerce: int | None
    priority: int
    event_type: str
    created_at: datetime
    payload: CatalogUpdatePayload

    model_config = {"from_attributes": True}


class CatalogUpdateBatchOut(BaseModel):
    items: list[CatalogUpdateEventOut]
    total: int


class CatalogUpdateAckIn(BaseModel):
    ids: list[int] = Field(..., min_length=1)
    status: Literal["done", "failed"]
    error: str | None = None


# ----------------------------------------------------


class CatalogUpdateStreamItemOut(BaseModel):
    id: int
    id_product: int
    id_ecommerce: int | None = None

    status: str
    event_type: str
    priority: int
    attempts: int
    last_error: str | None = None

    created_at: datetime
    processed_at: datetime | None = None

    # payload completo (JSON) – pode vir como TEXT (str) da DB
    payload: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v: Any) -> dict[str, Any] | None:
        """
        Aceita:
        - None
        - dict -> devolve como está
        - str  -> tenta fazer json.loads
        Caso contrário, devolve None para não rebentar.
        """
        if v is None:
            return None

        if isinstance(v, dict):
            return v

        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
                # se for lista ou outro tipo, ignoramos
                return None
            except json.JSONDecodeError:
                # payload malformado → não queremos partir a API por causa disto
                return None

        # fallback seguro
        return None


class CatalogUpdateStreamListOut(BaseModel):
    items: list[CatalogUpdateStreamItemOut]
    total: int
    page: int
    page_size: int
