# app/domains/audit/services/audit.py
"""
Service para registar audit logs.
Funções utilitárias para registar eventos.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.audit.write.audit_log_write_repo import AuditLogWriteRepo


def log(
    db: Session,
    event_type: str,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor_id: str | None = None,
    actor_name: str | None = None,
    description: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Regista um evento de auditoria.
    """
    repo = AuditLogWriteRepo(db)
    repo.create(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        actor_name=actor_name,
        description=description,
        details=details,
    )


# Funções de conveniência para eventos comuns


def log_product_import(
    db: Session,
    product_id: int,
    product_name: str | None,
    id_ecommerce: int | None,
    actor_id: str | None = None,
    actor_name: str | None = None,
) -> None:
    log(
        db,
        "product_import",
        entity_type="product",
        entity_id=product_id,
        actor_id=actor_id,
        actor_name=actor_name,
        description=f"Produto '{product_name}' importado para PrestaShop (ID: {id_ecommerce})",
        details={"id_ecommerce": id_ecommerce, "product_name": product_name},
    )


def log_bulk_import(
    db: Session,
    total: int,
    imported: int,
    failed: int,
    actor_id: str | None = None,
    actor_name: str | None = None,
) -> None:
    log(
        db,
        "product_import_bulk",
        entity_type="product",
        actor_id=actor_id,
        actor_name=actor_name,
        description=f"Bulk import: {imported}/{total} produtos importados ({failed} falharam)",
        details={"total": total, "imported": imported, "failed": failed},
    )


def log_category_mapping(
    db: Session,
    category_id: int,
    category_name: str | None,
    ps_category_id: int,
    ps_category_name: str | None,
    auto_import: bool,
    actor_id: str | None = None,
    actor_name: str | None = None,
) -> None:
    log(
        db,
        "category_mapping",
        entity_type="category",
        entity_id=category_id,
        actor_id=actor_id,
        actor_name=actor_name,
        description=f"Categoria '{category_name}' mapeada para '{ps_category_name}' (auto-import: {auto_import})",
        details={
            "ps_category_id": ps_category_id,
            "ps_category_name": ps_category_name,
            "auto_import": auto_import,
        },
    )


def log_config_update(
    db: Session,
    config_key: str,
    old_value: str | None,
    new_value: str,
    actor_id: str | None = None,
    actor_name: str | None = None,
) -> None:
    log(
        db,
        "config_update",
        entity_type="config",
        actor_id=actor_id,
        actor_name=actor_name,
        description=f"Configuração '{config_key}' alterada de '{old_value}' para '{new_value}'",
        details={"key": config_key, "old_value": old_value, "new_value": new_value},
    )


def log_user_login(
    db: Session,
    user_id: str,
    user_name: str | None,
    email: str | None,
) -> None:
    log(
        db,
        "user_login",
        entity_type="user",
        actor_id=user_id,
        actor_name=user_name,
        description=f"Utilizador '{user_name}' ({email}) iniciou sessão",
        details={"email": email},
    )
