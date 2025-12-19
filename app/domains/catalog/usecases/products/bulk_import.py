# app/domains/catalog/usecases/products/bulk_import.py
"""
Bulk import de produtos para o PrestaShop.
Reutiliza o usecase import_to_prestashop para cada produto.
"""

from __future__ import annotations

import logging

from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
from app.repositories.catalog.read.products_read_repo import ProductsReadRepository
from app.repositories.catalog.read.category_read_repo import CategoryReadRepository
from app.schemas.products import BulkImportOut, BulkImportItemResult
from app.domains.catalog.usecases.products import import_to_prestashop

log = logging.getLogger(__name__)


def execute(
    uow: UoW,
    ps_client: PrestashopClient,
    *,
    product_ids: list[int],
    id_ps_category_override: int | None = None,
) -> BulkImportOut:
    """
    Importa múltiplos produtos para o PrestaShop.

    Args:
        uow: Unit of Work
        ps_client: Cliente PrestaShop
        product_ids: Lista de IDs de produtos a importar
        id_ps_category_override: Categoria PS para usar em todos (opcional)

    Returns:
        BulkImportOut com resultados agregados
    """
    db = uow.db
    prod_repo = ProductsReadRepository(db)
    cat_repo = CategoryReadRepository(db)

    results: list[BulkImportItemResult] = []
    imported = 0
    failed = 0
    skipped = 0

    for pid in product_ids:
        # 1) Buscar produto
        product = prod_repo.get(pid)
        if not product:
            failed += 1
            results.append(
                BulkImportItemResult(
                    id_product=pid,
                    success=False,
                    error="Produto não encontrado",
                )
            )
            continue

        # 2) Skip se já importado
        if product.id_ecommerce:
            skipped += 1
            results.append(
                BulkImportItemResult(
                    id_product=pid,
                    success=True,
                    id_ecommerce=product.id_ecommerce,
                    error="Já importado",
                )
            )
            continue

        # 3) Determinar categoria PS
        id_ps_category = id_ps_category_override
        if not id_ps_category and product.id_category:
            category = cat_repo.get(product.id_category)
            if category and category.id_ps_category:
                id_ps_category = category.id_ps_category

        if not id_ps_category:
            failed += 1
            results.append(
                BulkImportItemResult(
                    id_product=pid,
                    success=False,
                    error="Categoria PS não mapeada",
                )
            )
            continue

        # 4) Importar usando o usecase existente
        try:
            result = import_to_prestashop.execute(
                uow,
                ps_client,
                id_product=pid,
                id_ps_category=id_ps_category,
            )
            imported += 1
            results.append(
                BulkImportItemResult(
                    id_product=pid,
                    success=True,
                    id_ecommerce=result.get("id_ecommerce"),
                )
            )
            log.info("Produto %d importado para PS (ID: %s)", pid, result.get("id_ecommerce"))

        except Exception as e:
            failed += 1
            results.append(
                BulkImportItemResult(
                    id_product=pid,
                    success=False,
                    error=str(e),
                )
            )
            log.warning("Falha ao importar produto %d: %s", pid, e)

    db.commit()

    return BulkImportOut(
        total=len(product_ids),
        imported=imported,
        failed=failed,
        skipped=skipped,
        results=results,
    )
