# app/api/v1/config.py
"""
Endpoints para configurações de plataforma.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_uow
from app.infra.uow import UoW
from app.repositories.config.read.platform_config_read_repo import (
    PlatformConfigReadRepository,
)
from app.repositories.config.write.platform_config_write_repo import (
    PlatformConfigWriteRepository,
)
from app.domains.config.services.config_service import config_service
from app.schemas.config import (
    PlatformConfigOut,
    PlatformConfigUpdate,
    PlatformConfigCategoryGroup,
    PlatformConfigListOut,
    PlatformConfigSeedOut,
)

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("", response_model=PlatformConfigListOut)
def list_configs(uow: UoW = Depends(get_uow)):
    """Lista todas as configurações agrupadas por categoria."""
    repo = PlatformConfigReadRepository(uow.db)

    configs = repo.list_all()
    categories = repo.get_categories()

    groups = []
    for cat in categories:
        cat_configs = [c for c in configs if c.category == cat]
        groups.append(
            PlatformConfigCategoryGroup(
                category=cat,
                configs=[PlatformConfigOut.model_validate(c) for c in cat_configs],
            )
        )

    return PlatformConfigListOut(total=len(configs), categories=groups)


@router.get("/{key}", response_model=PlatformConfigOut)
def get_config(key: str, uow: UoW = Depends(get_uow)):
    """Obtém uma configuração por chave."""
    repo = PlatformConfigReadRepository(uow.db)
    cfg = repo.get(key)

    if not cfg:
        raise HTTPException(status_code=404, detail=f"Config '{key}' not found")

    return PlatformConfigOut.model_validate(cfg)


@router.put("/{key}", response_model=PlatformConfigOut)
def update_config(
    key: str,
    body: PlatformConfigUpdate,
    uow: UoW = Depends(get_uow),
):
    """Atualiza o valor de uma configuração."""
    read_repo = PlatformConfigReadRepository(uow.db)
    write_repo = PlatformConfigWriteRepository(uow.db)

    existing = read_repo.get(key)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Config '{key}' not found")

    # Validar tipo
    try:
        if existing.value_type == "int":
            int(body.value)
        elif existing.value_type == "float":
            float(body.value)
        elif existing.value_type == "bool":
            if body.value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                raise ValueError("Invalid boolean")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for type '{existing.value_type}': {e}",
        ) from e

    updated = write_repo.upsert(
        key=key,
        value=body.value,
        value_type=existing.value_type,
        category=existing.category,
        description=existing.description,
    )
    uow.commit()

    # Invalidar cache do ConfigService
    config_service.invalidate_cache()

    return PlatformConfigOut.model_validate(updated)


@router.post("/seed", response_model=PlatformConfigSeedOut)
def seed_defaults(uow: UoW = Depends(get_uow)):
    """Popular configurações com valores default."""
    repo = PlatformConfigWriteRepository(uow.db)
    created = repo.seed_defaults()
    uow.commit()

    # Invalidar cache para carregar novos valores
    config_service.invalidate_cache()

    return PlatformConfigSeedOut(
        created=created,
        message=f"Created {created} default config(s)",
    )
