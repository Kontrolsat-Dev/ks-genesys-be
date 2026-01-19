# app/domains/catalog/usecases/products/auto_import_new_products.py
"""
Usecase para auto-importar produtos novos em categorias com auto_import ativo.
Executado pelo worker job 'product_auto_import'.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import and_

from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
from app.models.product import Product
from app.models.category import Category
from app.domains.catalog.usecases.products import import_to_prestashop
from app.domains.audit.services.audit_service import AuditService

log = logging.getLogger(__name__)


@dataclass
class AutoImportResult:
    """Resultado da execução do auto-import."""

    total_eligible: int = 0
    imported: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] | None = None


def execute(
    uow: UoW,
    ps_client: PrestashopClient,
    *,
    batch_size: int = 50,
) -> AutoImportResult:
    """
    Importa automaticamente TODOS os produtos novos em categorias com auto_import ativo.
    Processa em batches para evitar sobrecarga.

    Critérios de elegibilidade:
    1. Produto sem id_ecommerce (não importado)
    2. Categoria com auto_import=True e id_ps_category definido
    3. Produto criado após auto_import_since da categoria

    Args:
        uow: Unit of Work
        ps_client: Cliente PrestaShop
        batch_size: Tamanho de cada batch (default: 50)

    Returns:
        AutoImportResult com estatísticas totais
    """
    db = uow.db

    # Obter batch_size da config (usa default se não configurado)
    from app.domains.config.services.config_service import config_service

    batch_size = config_service.get_int("auto_import_batch_limit", default=batch_size)

    result = AutoImportResult(errors=[])
    total_processed = 0

    while True:
        # Query batch de produtos elegíveis para auto-import
        eligible_products = (
            db.query(Product)
            .join(Category, Product.id_category == Category.id)
            .filter(
                and_(
                    # Produto não importado
                    Product.id_ecommerce.is_(None),
                    # Categoria com auto_import ativo
                    Category.auto_import == True,  # noqa: E712
                    # Categoria mapeada para PS
                    Category.id_ps_category.isnot(None),
                    # auto_import_since definido
                    Category.auto_import_since.isnot(None),
                    # Produto criado após ativação do auto_import
                    Product.created_at > Category.auto_import_since,
                )
            )
            .order_by(Product.created_at.asc())
            .limit(batch_size)
            .all()
        )

        if not eligible_products:
            # Não há mais produtos para processar
            break

        log.info(
            "Auto-import batch: processando %d produtos (total até agora: %d)",
            len(eligible_products),
            total_processed,
        )
        result.total_eligible += len(eligible_products)

        for product in eligible_products:
            try:
                # Obter categoria para buscar id_ps_category
                category = db.get(Category, product.id_category)
                if not category or not category.id_ps_category:
                    log.warning(
                        "Auto-import: produto %d sem categoria PS válida, a saltar",
                        product.id,
                    )
                    result.skipped += 1
                    continue

                # Importar produto
                import_result = import_to_prestashop.execute(
                    uow,
                    ps_client,
                    id_product=product.id,
                    id_ps_category=category.id_ps_category,
                )

                if import_result.success or import_result.id_ecommerce:
                    result.imported += 1
                    log.info(
                        "Auto-import: produto %d importado para PS (id_ecommerce=%s)",
                        product.id,
                        import_result.id_ecommerce,
                    )
                else:
                    result.failed += 1
                    error_msg = f"Produto {product.id}: import retornou sem sucesso"
                    result.errors.append(error_msg)
                    log.warning("Auto-import: %s", error_msg)

            except Exception as e:
                result.failed += 1
                error_msg = f"Produto {product.id}: {type(e).__name__}: {e}"
                result.errors.append(error_msg)
                log.warning("Auto-import: erro ao importar produto %d: %s", product.id, e)

        # Commit após cada batch para persistir progresso
        db.commit()
        total_processed += len(eligible_products)

        log.info(
            "Auto-import batch concluído: batch=%d importados=%d falhados=%d",
            len(eligible_products),
            result.imported,
            result.failed,
        )

    log.info(
        "Auto-import TOTAL concluído: elegíveis=%d importados=%d falhados=%d saltados=%d",
        result.total_eligible,
        result.imported,
        result.failed,
        result.skipped,
    )

    # Audit log (só se houve produtos elegíveis)
    if result.total_eligible > 0:
        AuditService(db).log_auto_import(
            total_eligible=result.total_eligible,
            imported=result.imported,
            failed=result.failed,
            skipped=result.skipped,
        )

    return result
