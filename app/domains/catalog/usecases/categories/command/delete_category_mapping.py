# app/domains/catalog/usecases/categories/delete_category_mapping.py
"""
UseCase para remover o mapeamento PrestaShop de uma categoria.
"""

from __future__ import annotations

from app.infra.uow import UoW
from app.domains.audit.services.audit_service import AuditService


def execute(uow: UoW, *, id_category: int) -> None:
    """
    Remove o mapeamento PrestaShop de uma categoria.

    Args:
        uow: Unit of Work
        id_category: ID da categoria

    Raises:
        NotFound: Se a categoria não existir (levantado pelo repo)
    """
    # get_required lança NotFound se não existir — sem precisar importar Category aqui
    cat = uow.categories.get_required(id_category)
    category_name = cat.name

    uow.categories_w.clear_ps_mapping(id_category)

    # Registar no audit log (antes do commit)
    AuditService(uow.db).log_category_mapping_delete(
        category_id=id_category,
        category_name=category_name,
    )

    uow.commit()
