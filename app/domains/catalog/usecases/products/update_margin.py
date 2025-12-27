from __future__ import annotations

import logging
from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, InvalidArgument, NotFound
from app.domains.catalog.services.active_offer import (
    recalculate_active_offer_for_product,
)
from app.domains.catalog.services.product_detail import (
    DetailOptions,
    get_product_detail,
)
from app.domains.catalog.services.sync_events import emit_product_state_event
from app.infra.uow import UoW
from app.repositories.catalog.read.product_active_offer_read_repo import (
    ProductActiveOfferReadRepository,
)
from app.repositories.catalog.write.product_write_repo import ProductWriteRepository
from app.domains.audit.services.audit_service import AuditService

log = logging.getLogger("gsm.catalog.update_margin")


def execute(
    uow: UoW,
    *,
    id_product: int,
    margin: float,
    expand_meta: bool = True,
    expand_offers: bool = True,
    expand_events: bool = True,
    events_days: int | None = 90,
    events_limit: int | None = 2000,
    aggregate_daily: bool = True,
):
    """
    Atualiza a margin de um produto e, se aplicável, recalcula a ProductActiveOffer
    + emite evento de product_state_changed para o PrestaShop.

    Retorna o ProductDetailOut atualizado com as mesmas flags de expansão
    usadas no detalhe normal.
    """
    db = uow.db
    prod_w = ProductWriteRepository(db)
    pao_r = ProductActiveOfferReadRepository(db)

    try:
        # Garantir que o produto existe
        product = prod_w.get(id_product)
        if product is None:
            raise NotFound("Product not found")

        old_margin = product.margin

        # Normalizar/validar margin
        try:
            new_margin = float(margin)
        except (TypeError, ValueError) as err:
            raise InvalidArgument("Invalid margin value") from err

        if new_margin < 0:
            raise InvalidArgument("Margin must be >= 0")

        # Snapshot da oferta ativa ANTES do recálculo
        prev_active_snapshot: dict[str, object] | None = None
        pao = pao_r.get_by_product(id_product)
        if pao is not None:
            prev_active_snapshot = {
                "id_supplier": pao.id_supplier,
                "id_supplier_item": pao.id_supplier_item,
                "unit_price_sent": float(pao.unit_price_sent)
                if pao.unit_price_sent is not None
                else None,
                "stock_sent": int(pao.stock_sent or 0),
            }

        # Aplicar a nova margem
        prod_w.set_margin(id_product=id_product, margin=new_margin)

        # Só faz sentido recalcular/emitir se estiver ligado ao PrestaShop
        if product.id_ecommerce and product.id_ecommerce > 0:
            new_active = recalculate_active_offer_for_product(
                db,
                id_product=id_product,
            )

            emit_product_state_event(
                db,
                product=product,
                active_offer=new_active,
                reason="margin_update",
                prev_active_snapshot=prev_active_snapshot,
            )

        # Registar no audit log (antes do commit)
        AuditService(db).log_product_margin_update(
            product_id=id_product,
            product_name=product.name,
            old_margin=float(old_margin) if old_margin is not None else None,
            new_margin=new_margin,
        )

        uow.commit()

    except (NotFound, InvalidArgument):
        uow.rollback()
        raise
    except IntegrityError as err:
        uow.rollback()
        log.exception("Integrity error while updating margin for product id=%s", id_product)
        raise BadRequest("Could not update product margin") from err
    except Exception as err:
        uow.rollback()
        log.exception("Unexpected error while updating margin for product id=%s", id_product)
        raise BadRequest("Could not update product margin") from err

    # 6) Devolver o detalhe já com a margin aplicada e, se for o caso, a active_offer recalculada
    opts = DetailOptions(
        expand_meta=expand_meta,
        expand_offers=expand_offers,
        expand_events=expand_events,
        events_days=events_days,
        events_limit=events_limit,
        aggregate_daily=aggregate_daily,
    )
    return get_product_detail(uow, id_product=id_product, opts=opts)
