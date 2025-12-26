# app/repositories/config/write/platform_config_write_repo.py
"""
Repositório de escrita para configurações de plataforma.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.infra.base import utcnow
from app.models.platform_config import PlatformConfig


class PlatformConfigWriteRepository:
    """Operações de escrita para PlatformConfig."""

    def __init__(self, db: Session):
        self.db = db

    def upsert(
        self,
        key: str,
        value: str,
        value_type: str = "str",
        category: str = "general",
        description: str | None = None,
    ) -> PlatformConfig:
        """
        Insere ou atualiza uma configuração.
        """
        existing = self.db.get(PlatformConfig, key)

        if existing:
            existing.value = value
            existing.value_type = value_type
            existing.category = category
            if description is not None:
                existing.description = description
            existing.updated_at = utcnow()
            return existing

        cfg = PlatformConfig(
            key=key,
            value=value,
            value_type=value_type,
            category=category,
            description=description,
        )
        self.db.add(cfg)
        return cfg

    def delete(self, key: str) -> bool:
        """Remove uma configuração."""
        cfg = self.db.get(PlatformConfig, key)
        if cfg:
            self.db.delete(cfg)
            return True
        return False

    def seed_defaults(self) -> int:
        """
        Popular com valores default se não existirem.
        Retorna número de configs criadas.
        """
        defaults = [
            # Preços
            ("vat_rate", "1.23", "float", "prices", "Taxa de IVA (1.23 = 23%)"),
            (
                "price_rounding_enabled",
                "true",
                "bool",
                "prices",
                "Activar arredondamento de preços para .40/.90",
            ),
            # Workers - Stale timeouts
            (
                "stale_job_timeout_supplier_ingest",
                "3600",
                "int",
                "workers",
                "Timeout (segundos) para jobs de ingest serem marcados como stale",
            ),
            (
                "stale_job_timeout_default",
                "600",
                "int",
                "workers",
                "Timeout (segundos) default para jobs serem marcados como stale",
            ),
            (
                "stale_feed_run_timeout_minutes",
                "120",
                "int",
                "workers",
                "Timeout (minutos) para FeedRuns serem marcados como error",
            ),
            # Workers - Auto-import
            (
                "auto_import_interval_hours",
                "4",
                "int",
                "workers",
                "Intervalo (horas) entre execuções de auto-import",
            ),
            (
                "auto_import_batch_limit",
                "50",
                "int",
                "workers",
                "Máximo de produtos por batch de auto-import",
            ),
            # Workers - Catalog stream
            (
                "catalog_stream_claim_limit",
                "50",
                "int",
                "workers",
                "Máximo de eventos a processar por batch",
            ),
            # Sync prioridades
            ("priority_stock_out", "10", "int", "sync", "Prioridade para eventos de stock-out"),
            (
                "priority_stock_reentry",
                "9",
                "int",
                "sync",
                "Prioridade para eventos de reentrada de stock",
            ),
            (
                "priority_price_change",
                "8",
                "int",
                "sync",
                "Prioridade para eventos de alteração de preço",
            ),
            ("priority_default", "5", "int", "sync", "Prioridade default para eventos"),
            ("priority_eol", "4", "int", "sync", "Prioridade para eventos de EOL"),
        ]

        created = 0
        for key, value, vtype, category, description in defaults:
            existing = self.db.get(PlatformConfig, key)
            if not existing:
                self.db.add(
                    PlatformConfig(
                        key=key,
                        value=value,
                        value_type=vtype,
                        category=category,
                        description=description,
                    )
                )
                created += 1

        return created
