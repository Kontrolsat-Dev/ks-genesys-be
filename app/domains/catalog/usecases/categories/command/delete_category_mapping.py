# app/domains/catalog/usecases/categories/delete_category_mapping.py
"""
UseCase para remover o mapeamento PrestaShop de uma categoria.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.core.errors import NotFound
from app.models.category import Category
from app.domains.audit.services.audit_service import AuditService


def execute(uow: UoW, *, id_category: int) -> None:
    """
    Remove o mapeamento PrestaShop de uma categoria.

    Args:
        uow: Unit of Work
        id_category: ID da categoria

    Raises:
        NotFound: Se a categoria não existir
    """
    db = uow.db
    cat = db.get(Category, id_category)
    if not cat:
        raise NotFound(f"Category {id_category} not found")

    category_name = cat.name

    cat.id_ps_category = None
    cat.ps_category_name = None
    cat.auto_import = False
    cat.auto_import_since = None

    # Registar no audit log (antes do commit)
    AuditService(db).log_category_mapping_delete(
        category_id=id_category,
        category_name=category_name,
    )

    uow.commit()
