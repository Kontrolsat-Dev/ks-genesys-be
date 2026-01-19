# app/domains/config/services/config_service.py
"""
Serviço de configurações com cache em memória.

Uso:
    from app.domains.config.services.config_service import config_service

    vat_rate = config_service.get_float("vat_rate", default=1.23)

    # Após actualizar via API, invalidar cache:
    config_service.invalidate_cache()
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from app.infra.session import SessionLocal
from app.repositories.config.read.platform_config_read_repo import (
    PlatformConfigReadRepository,
)

log = logging.getLogger(__name__)


class ConfigService:
    """
    Serviço para acesso rápido a configurações com cache em memória.
    Thread-safe.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._loaded = False

    def _load_all(self) -> None:
        """Carrega todas as configs para cache."""
        with SessionLocal() as db:
            repo = PlatformConfigReadRepository(db)
            configs = repo.list_all()
            with self._lock:
                self._cache = {cfg.key: cfg.get_typed_value() for cfg in configs}
                self._loaded = True
        log.debug("ConfigService: loaded %d configs into cache", len(self._cache))

    def _ensure_loaded(self) -> None:
        """Garante que o cache está carregado."""
        if not self._loaded:
            self._load_all()

    def invalidate_cache(self) -> None:
        """Invalida o cache. Próximo acesso vai recarregar."""
        with self._lock:
            self._cache.clear()
            self._loaded = False
        log.debug("ConfigService: cache invalidated")

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor do cache."""
        self._ensure_loaded()
        with self._lock:
            return self._cache.get(key, default)

    def get_str(self, key: str, default: str = "") -> str:
        """Obtém um valor string."""
        val = self.get(key, default)
        return str(val) if val is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Obtém um valor inteiro."""
        val = self.get(key, default)
        try:
            return int(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Obtém um valor float."""
        val = self.get(key, default)
        try:
            return float(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Obtém um valor boolean."""
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val) if val is not None else default

    def get_all(self) -> dict[str, Any]:
        """Retorna todas as configs em cache."""
        self._ensure_loaded()
        with self._lock:
            return dict(self._cache)


# Singleton global
config_service = ConfigService()
