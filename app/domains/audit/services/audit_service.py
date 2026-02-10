# app/domains/audit/services/audit_service.py
"""
Serviço de auditoria para registar eventos importantes do sistema.

Uso:
    from app.domains.audit.services.audit_service import AuditService

    # Dentro de um usecase ou API route:
    AuditService(uow.db).log_product_import(
        product_id=123,
        product_name="Produto X",
        id_ecommerce=456,
        actor_id="user_1",
        actor_name="João",
    )

O serviço recebe a sessão DB porque cada operação precisa estar
na mesma transação que a operação de negócio.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

from datetime import datetime
from decimal import Decimal

log = logging.getLogger(__name__)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, Decimal)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class AuditService:
    """
    Serviço para registar audit logs.
    Recebe sessão DB para participar na mesma transação.
    """

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        event_type: str,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
        actor_id: str | None = None,
        actor_name: str | None = None,
        description: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Regista um evento de auditoria genérico.
        """
        audit_log = AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=description,
            details_json=json.dumps(details, default=json_serial) if details else None,
        )
        self.db.add(audit_log)
        log.debug("Audit: %s %s:%s by %s", event_type, entity_type, entity_id, actor_id)
        return audit_log

    # ──────────────────────────────────────────────────────────────────────────
    # Métodos de conveniência para eventos comuns
    # ──────────────────────────────────────────────────────────────────────────

    def log_product_import(
        self,
        product_id: int,
        product_name: str | None,
        id_ecommerce: int | None,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista importação de produto para PrestaShop."""
        return self.log(
            "product_import",
            entity_type="product",
            entity_id=product_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Produto '{product_name}' importado para PrestaShop (ID: {id_ecommerce})",
            details={"id_ecommerce": id_ecommerce, "product_name": product_name},
        )

    def log_bulk_import(
        self,
        total: int,
        imported: int,
        failed: int,
        skipped: int = 0,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista bulk import de produtos."""
        return self.log(
            "product_import_bulk",
            entity_type="product",
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Bulk import: {imported}/{total} produtos importados ({failed} falharam, {skipped} saltados)",
            details={
                "total": total,
                "imported": imported,
                "failed": failed,
                "skipped": skipped,
            },
        )

    def log_category_mapping(
        self,
        category_id: int,
        category_name: str | None,
        ps_category_id: int,
        ps_category_name: str | None,
        auto_import: bool,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista mapeamento de categoria para PrestaShop."""
        return self.log(
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
        self,
        config_key: str,
        old_value: str | None,
        new_value: str,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista alteração de configuração."""
        return self.log(
            "config_update",
            entity_type="config",
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Configuração '{config_key}' alterada de '{old_value}' para '{new_value}'",
            details={"key": config_key, "old_value": old_value, "new_value": new_value},
        )

    def log_user_login(
        self,
        user_id: str,
        user_name: str | None,
        email: str | None = None,
    ) -> AuditLog:
        """Regista login de utilizador."""
        return self.log(
            "user_login",
            entity_type="user",
            actor_id=user_id,
            actor_name=user_name,
            description=f"Utilizador '{user_name}' ({email}) iniciou sessão",
            details={"email": email},
        )

    def log_auto_import(
        self,
        total_eligible: int,
        imported: int,
        failed: int,
        skipped: int = 0,
    ) -> AuditLog:
        """Regista execução do auto-import worker."""
        return self.log(
            "product_auto_import",
            entity_type="product",
            actor_id="system",
            actor_name="Worker",
            description=f"Auto-import: {imported}/{total_eligible} produtos importados ({failed} falharam)",
            details={
                "total_eligible": total_eligible,
                "imported": imported,
                "failed": failed,
                "skipped": skipped,
            },
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Supplier events
    # ──────────────────────────────────────────────────────────────────────────

    def log_supplier_create(
        self,
        supplier_id: int,
        supplier_name: str,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista criação de fornecedor."""
        return self.log(
            "supplier_create",
            entity_type="supplier",
            entity_id=supplier_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Fornecedor '{supplier_name}' criado",
            details={"supplier_name": supplier_name},
        )

    def log_supplier_update(
        self,
        supplier_id: int,
        supplier_name: str,
        changes: dict[str, Any] | None = None,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista atualização de fornecedor."""
        return self.log(
            "supplier_update",
            entity_type="supplier",
            entity_id=supplier_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Fornecedor '{supplier_name}' atualizado",
            details={"supplier_name": supplier_name, "changes": changes},
        )

    def log_supplier_delete(
        self,
        supplier_id: int,
        supplier_name: str,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista eliminação de fornecedor."""
        return self.log(
            "supplier_delete",
            entity_type="supplier",
            entity_id=supplier_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Fornecedor '{supplier_name}' eliminado",
            details={"supplier_name": supplier_name},
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Category events
    # ──────────────────────────────────────────────────────────────────────────

    def log_category_mapping_delete(
        self,
        category_id: int,
        category_name: str | None,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista remoção de mapeamento de categoria."""
        return self.log(
            "category_mapping_delete",
            entity_type="category",
            entity_id=category_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Mapeamento da categoria '{category_name}' removido",
            details={"category_name": category_name},
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Product events
    # ──────────────────────────────────────────────────────────────────────────

    def log_product_margin_update(
        self,
        product_id: int,
        product_name: str | None,
        old_margin: float | None,
        new_margin: float | None,
        actor_id: str | None = None,
        actor_name: str | None = None,
    ) -> AuditLog:
        """Regista alteração de margem de produto."""
        return self.log(
            "product_margin_update",
            entity_type="product",
            entity_id=product_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"Margem do produto '{product_name}' alterada de {old_margin} para {new_margin}",
            details={
                "product_name": product_name,
                "old_margin": old_margin,
                "new_margin": new_margin,
            },
        )

    def log_product_eol_marked(
        self,
        products_marked: int,
        events_enqueued: int,
    ) -> AuditLog:
        """Regista produtos marcados como EOL."""
        return self.log(
            "product_eol_marked",
            entity_type="product",
            actor_id="system",
            actor_name="Worker",
            description=f"EOL check: {products_marked} produtos marcados, {events_enqueued} eventos enfileirados",
            details={
                "products_marked": products_marked,
                "events_enqueued": events_enqueued,
            },
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Ingest events
    # ──────────────────────────────────────────────────────────────────────────

    def log_ingest_complete(
        self,
        supplier_id: int,
        supplier_name: str | None,
        run_id: int,
        rows_processed: int,
        products_created: int = 0,
        products_updated: int = 0,
        errors: int = 0,
    ) -> AuditLog:
        """Regista conclusão de ingest de fornecedor."""
        return self.log(
            "ingest_complete",
            entity_type="feed_run",
            entity_id=run_id,
            actor_id="system",
            actor_name="Worker",
            description=f"Ingest do fornecedor '{supplier_name}' concluído: {rows_processed} linhas processadas",
            details={
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "run_id": run_id,
                "rows_processed": rows_processed,
                "products_created": products_created,
                "products_updated": products_updated,
                "errors": errors,
            },
        )
