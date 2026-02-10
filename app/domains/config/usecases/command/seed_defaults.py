# app/domains/config/usecases/seed_defaults.py
"""
UseCase para popular configurações com valores default.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.config.write.platform_config_write_repo import (
    PlatformConfigWriteRepository,
)
from app.domains.config.services.config_service import config_service
from app.schemas.config import PlatformConfigSeedOut


def execute(uow: UoW) -> PlatformConfigSeedOut:
    """
    Popula configurações com valores default.

    Returns:
        PlatformConfigSeedOut com número de configs criadas
    """
    repo = PlatformConfigWriteRepository(uow.db)
    created = repo.seed_defaults()
    uow.commit()

    # Invalidar cache para carregar novos valores
    config_service.invalidate_cache()

    return PlatformConfigSeedOut(
        created=created,
        message=f"Created {created} default config(s)",
    )
