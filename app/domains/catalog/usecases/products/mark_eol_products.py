# app/domains/catalog/usecases/products/mark_eol_products.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.infra.base import utcnow
from app.infra.uow import UoW
from app.core.config import settings
from app.repositories.catalog.read.products_read_repo import ProductsReadRepository
from app.repositories.catalog.write.product_write_repo import ProductWriteRepository
from app.repositories.procurement.read.product_event_read_repo import ProductEventReadRepository
from app.repositories.catalog.write.catalog_update_stream_write_repo import (
    CatalogUpdateStreamWriteRepository,
)

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
    db = uow.db
    now = as_of or utcnow()
    cutoff = now - timedelta(days=EOL_THRESHOLD_DAYS)

    events_r = ProductEventReadRepository(db)
    prod_r = ProductsReadRepository(db)
    prod_w = ProductWriteRepository(db)
    stream_w = CatalogUpdateStreamWriteRepository(db)

    candidate_ids = events_r.list_products_to_mark_eol(cutoff=cutoff)

    products_marked = 0
    events_enqueued = 0

    for id_product in candidate_ids:
        product = prod_r.get(id_product)
        if not product:
            continue

        if getattr(product, "is_eol", False):
            continue

        prod_w.set_eol(id_product, True)
        products_marked = products_marked + 1
        id_ecommerce = getattr(product, "id_ecommerce", None)

        # Caso produto esteja ligado ao Prestashop (id_ecommerce > 0) mandamos update
        if id_ecommerce and id_ecommerce > 0:
            stream_w.enqueue_product_state_change(
                product=product,
                active_offer=getattr(product, "active_offer", None),
                reason="eol_marked",
                priority=4,
            )
            events_enqueued = events_enqueued + 1

    uow.commit()

    return {
        "products_marked_eol": products_marked,
        "events_enqueued": events_enqueued,
        "cutoff_utc": cutoff.isoformat(),
        "threshold_days": EOL_THRESHOLD_DAYS,
    }
