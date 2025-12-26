# app/repositories/config/read/platform_config_read_repo.py
"""
Repositório de leitura para configurações de plataforma.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.platform_config import PlatformConfig


class PlatformConfigReadRepository:
    """Operações de leitura para PlatformConfig."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> PlatformConfig | None:
        """Obtém uma configuração por chave."""
        return self.db.get(PlatformConfig, key)

    def get_value(self, key: str, default: str | None = None) -> str | None:
        """Obtém apenas o valor de uma configuração."""
        cfg = self.get(key)
        return cfg.value if cfg else default

    def get_typed(self, key: str, default=None):
        """Obtém o valor convertido para o tipo correto."""
        cfg = self.get(key)
        if cfg is None:
            return default
        return cfg.get_typed_value()

    def list_all(self) -> list[PlatformConfig]:
        """Lista todas as configurações."""
        return (
            self.db.query(PlatformConfig)
            .order_by(
                PlatformConfig.category,
                PlatformConfig.key,
            )
            .all()
        )

    def list_by_category(self, category: str) -> list[PlatformConfig]:
        """Lista configurações de uma categoria."""
        return (
            self.db.query(PlatformConfig)
            .filter(PlatformConfig.category == category)
            .order_by(PlatformConfig.key)
            .all()
        )

    def get_categories(self) -> list[str]:
        """Lista todas as categorias distintas."""
        rows = self.db.query(PlatformConfig.category).distinct().all()
        return sorted([r[0] for r in rows])
