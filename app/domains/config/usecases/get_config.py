# app/domains/config/usecases/get_config.py
"""
UseCase para obter uma configuração por chave.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.core.errors import NotFound
from app.repositories.config.read.platform_config_read_repo import (
    PlatformConfigReadRepository,
)
from app.schemas.config import PlatformConfigOut


def execute(uow: UoW, *, key: str) -> PlatformConfigOut:
    """
    Obtém uma configuração por chave.

    Returns:
        PlatformConfigOut schema

    Raises:
        NotFound: Se a configuração não existir.
    """
    repo = PlatformConfigReadRepository(uow.db)
    cfg = repo.get(key)

    if not cfg:
        raise NotFound(f"Config '{key}' not found")

    return PlatformConfigOut.model_validate(cfg)
