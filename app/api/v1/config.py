# app/api/v1/config.py
"""
Endpoints para configurações de plataforma.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_uow
from app.infra.uow import UoW
from app.domains.config.usecases import list_configs
from app.domains.config.usecases import get_config
from app.domains.config.usecases import update_config
from app.domains.config.usecases import seed_defaults
from app.schemas.config import (
    PlatformConfigOut,
    PlatformConfigUpdate,
    PlatformConfigListOut,
    PlatformConfigSeedOut,
)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=PlatformConfigListOut)
def list_all_configs(uow: UoW = Depends(get_uow)):
    """Lista todas as configurações agrupadas por categoria."""
    return list_configs.execute(uow)


@router.get("/{key}", response_model=PlatformConfigOut)
def get_single_config(key: str, uow: UoW = Depends(get_uow)):
    """Obtém uma configuração por chave."""
    return get_config.execute(uow, key=key)


@router.put("/{key}", response_model=PlatformConfigOut)
def update_single_config(
    key: str,
    body: PlatformConfigUpdate,
    uow: UoW = Depends(get_uow),
):
    """Atualiza o valor de uma configuração."""
    return update_config.execute(uow, key=key, new_value=body.value)


@router.post("/seed", response_model=PlatformConfigSeedOut)
def seed_default_configs(uow: UoW = Depends(get_uow)):
    """Popular configurações com valores default."""
    return seed_defaults.execute(uow)
