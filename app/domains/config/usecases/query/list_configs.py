# app/domains/config/usecases/list_configs.py
"""
UseCase para listar todas as configurações agrupadas por categoria.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.repositories.config.read.platform_config_read_repo import (
    PlatformConfigReadRepository,
)
from app.schemas.config import (
    PlatformConfigOut,
    PlatformConfigCategoryGroup,
    PlatformConfigListOut,
)


def execute(uow: UoW) -> PlatformConfigListOut:
    """
    Lista todas as configurações agrupadas por categoria.
    """
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
