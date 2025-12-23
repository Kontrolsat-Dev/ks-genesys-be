# app/domains/catalog/usecases/categories/update_category_mapping.py
from __future__ import annotations

from datetime import datetime, UTC

from app.infra.uow import UoW
from app.core.errors import NotFound
from app.models.category import Category


def execute(
    uow: UoW,
    *,
    id_category: int,
    id_ps_category: int,
    ps_category_name: str,
    auto_import: bool,
) -> Category:
    """
    Mapeia uma categoria Genesys para uma categoria PrestaShop.

    Quando auto_import é ativado, define auto_import_since com a data atual
    para que apenas produtos criados a partir desse momento sejam auto-importados.
    """
    db = uow.db
    cat = db.get(Category, id_category)
    if not cat:
        raise NotFound(f"Category {id_category} not found")

    # Detetar transição de auto_import
    was_auto_import = cat.auto_import

    cat.id_ps_category = id_ps_category
    cat.ps_category_name = ps_category_name
    cat.auto_import = auto_import

    # Se auto_import foi ativado agora, definir auto_import_since
    if auto_import and not was_auto_import:
        cat.auto_import_since = datetime.now(UTC)
    # Se auto_import foi desativado, limpar auto_import_since
    elif not auto_import and was_auto_import:
        cat.auto_import_since = None

    uow.commit()
    return cat
