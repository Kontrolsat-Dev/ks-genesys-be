# app/domains/catalog/usecases/products/mark_eol_products.py
# Marca produtos como EOL (End of Life) quando sem stock há muito tempo

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.infra.base import utcnow
from app.infra.uow import UoW
from app.core.config import settings
from app.domains.audit.services.audit_service import AuditService

EOL_THRESHOLD_DAYS = settings.EOL_THRESHOLD_DAYS


def execute(uow: UoW, *, as_of: datetime | None = None) -> dict[str, Any]:
    """
    Marca produtos como EOL quando:

    - Produto criado há mais de EOL_THRESHOLD_DAYS (6 meses)
    - E uma destas condições:
        * Nunca teve evento com stock > 0
        * O último evento com stock > 0 foi há mais de 6 meses
    - Ainda não está marcado como is_eol = True

    Se o produto tiver id_ecommerce definido (>0), enfileira um
    product_state_changed no CatalogUpdateStream para o Prestashop o desativar.
    """
    now = as_of or utcnow()
    cutoff = now - timedelta(days=EOL_THRESHOLD_DAYS)

    candidate_ids = uow.product_events.list_products_to_mark_eol(cutoff=cutoff)

    products_marked = 0
    events_enqueued = 0

    for id_product in candidate_ids:
        product = uow.products.get(id_product)
        if not product:
            continue

        if getattr(product, "is_eol", False):
            continue

        uow.products_w.set_eol(id_product, True)
        products_marked = products_marked + 1
        id_ecommerce = getattr(product, "id_ecommerce", None)

        # Caso produto esteja ligado ao Prestashop (id_ecommerce > 0) mandamos update
        if id_ecommerce and id_ecommerce > 0:
            uow.catalog_events_w.enqueue_product_state_change(
                product=product,
                active_offer=getattr(product, "active_offer", None),
                reason="eol_marked",
                priority=4,
            )
            events_enqueued = events_enqueued + 1

    # Registar no audit log (antes do commit, se houve produtos marcados)
    if products_marked > 0:
        AuditService(uow.db).log_product_eol_marked(
            products_marked=products_marked,
            events_enqueued=events_enqueued,
        )

    uow.commit()

    return {
        "products_marked_eol": products_marked,
        "events_enqueued": events_enqueued,
        "cutoff_utc": cutoff.isoformat(),
        "threshold_days": EOL_THRESHOLD_DAYS,
    }
