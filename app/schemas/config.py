# app/schemas/config.py
"""
Schemas para configurações de plataforma.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlatformConfigOut(BaseModel):
    """Output de uma configuração."""

    key: str
    value: str
    value_type: str
    category: str
    description: str | None
    updated_at: datetime

    class Config:
        from_attributes = True


class PlatformConfigUpdate(BaseModel):
    """Input para atualizar uma configuração."""

    value: str


class PlatformConfigCategoryGroup(BaseModel):
    """Grupo de configurações por categoria."""

    category: str
    configs: list[PlatformConfigOut]


class PlatformConfigListOut(BaseModel):
    """Output da listagem de configurações."""

    total: int
    categories: list[PlatformConfigCategoryGroup]


class PlatformConfigSeedOut(BaseModel):
    """Output do seed de configurações."""

    created: int
    message: str
