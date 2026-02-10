# app/domains/config/usecases/update_config.py
"""
UseCase para atualizar o valor de uma configuração.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.core.errors import NotFound, InvalidArgument
from app.repositories.config.read.platform_config_read_repo import (
    PlatformConfigReadRepository,
)
from app.repositories.config.write.platform_config_write_repo import (
    PlatformConfigWriteRepository,
)
from app.domains.config.services.config_service import config_service
from app.domains.audit.services.audit_service import AuditService
from app.schemas.config import PlatformConfigOut


def execute(
    uow: UoW,
    *,
    key: str,
    new_value: str,
) -> PlatformConfigOut:
    """
    Atualiza o valor de uma configuração.

    Args:
        uow: Unit of Work
        key: Chave da configuração
        new_value: Novo valor (string, será validado contra o tipo)

    Returns:
        PlatformConfigOut schema atualizado

    Raises:
        NotFound: Se a configuração não existir
        InvalidArgument: Se o valor não for válido para o tipo
    """
    db = uow.db
    read_repo = PlatformConfigReadRepository(db)
    write_repo = PlatformConfigWriteRepository(db)

    existing = read_repo.get(key)
    if not existing:
        raise NotFound(f"Config '{key}' not found")

    old_value = existing.value

    # Validar tipo
    _validate_value_type(new_value, existing.value_type)

    updated = write_repo.upsert(
        key=key,
        value=new_value,
        value_type=existing.value_type,
        category=existing.category,
        description=existing.description,
    )

    # Audit log
    AuditService(db).log_config_update(
        config_key=key,
        old_value=old_value,
        new_value=new_value,
    )

    uow.commit()

    # Invalidar cache do ConfigService
    config_service.invalidate_cache()

    return PlatformConfigOut.model_validate(updated)


def _validate_value_type(value: str, value_type: str) -> None:
    """
    Valida se o valor é compatível com o tipo esperado.

    Raises:
        InvalidArgument: Se o valor não for válido
    """
    try:
        if value_type == "int":
            int(value)
        elif value_type == "float":
            float(value)
        elif value_type == "bool":
            if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                raise ValueError("Invalid boolean")
    except ValueError as e:
        raise InvalidArgument(f"Invalid value for type '{value_type}': {e}") from e
