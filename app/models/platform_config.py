# app/models/platform_config.py
"""
Modelo para configurações de plataforma editáveis via UI.
Complementa as Settings (.env) com valores que podem ser alterados em runtime.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.base import Base, utcnow


class PlatformConfig(Base):
    """
    Configuração de plataforma key-value.

    Categorias:
    - prices: VAT rate, arredondamentos
    - workers: Timeouts, intervalos, limites de batch
    - sync: Prioridades de eventos
    """

    __tablename__ = "platform_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False, default="str")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PlatformConfig {self.key}={self.value}>"

    def get_typed_value(self):
        """Retorna o valor convertido para o tipo correto."""
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json

            return json.loads(self.value)
        return self.value
