from __future__ import annotations

import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Any

from app.models.catalog_update_stream import CatalogUpdateStream
from app.models.product import Product
from app.models.product_active_offer import ProductActiveOffer

log = logging.getLogger("gsm.catalog.update_stream")


class CatalogUpdateStreamWriteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _build_payload(
        self,
        product: Product,
        active_offer: ProductActiveOffer | None,
        reason: str,
    ) -> dict[str, Any]:
        """
        Snapshot minimal para o módulo do PrestaShop:
        - product: dados semânticos (margin incluída)
        - active_offer: custo, preço com margem e stock
        - shipping: hint de supplier para portes/etc.
        """
        margin = 0.0
        if product.margin is not None:
            try:
                margin = float(product.margin)
            except (TypeError, ValueError):
                margin = 0.0
        if margin < 0:
            margin = 0.0

        # por defeito vem da DB; se vier None, recalculamos
        unit_price_sent: float | None = None
        if active_offer is not None:
            unit_price_sent = active_offer.unit_price_sent

            if unit_price_sent is None and active_offer.unit_cost is not None:
                from app.domains.catalog.services.price_rounding import round_to_pretty_price

                raw_price = active_offer.unit_cost * (1 + margin)
                unit_price_sent = round_to_pretty_price(raw_price)

        return {
            "reason": reason,
            "product": {
                "gtin": product.gtin,
                "partnumber": product.partnumber,
                "name": product.name,
                "margin": margin,
                "is_enabled": product.is_enabled,
                "is_eol": product.is_eol,
            },
            "active_offer": (
                {
                    "id_supplier": active_offer.id_supplier,
                    "id_supplier_item": active_offer.id_supplier_item,
                    "unit_cost": active_offer.unit_cost,
                    "unit_price_sent": unit_price_sent,
                    "stock_sent": active_offer.stock_sent,
                }
                if active_offer is not None
                else None
            ),
            "shipping": {"id_supplier": active_offer.id_supplier if active_offer else None},
        }

    def enqueue_product_state_change(
        self,
        *,
        product: Product,
        active_offer: ProductActiveOffer | None,
        reason: str,
        priority: int,
    ) -> CatalogUpdateStream:
        """
        Enfileira um evento de `product_state_changed`, **deduplicando**:

        - Se já existir um evento `pending` para este produto/ecommerce,
          atualiza esse evento com o novo payload + prioridade agregada.
        - Caso contrário, cria um novo.

        Resultado: no máximo 1 evento `pending` por produto.
        """
        payload_dict = self._build_payload(product, active_offer, reason=reason)
        now = datetime.utcnow()

        # Procura um evento pendente existente para este produto/ecommerce
        existing = (
            self.db.query(CatalogUpdateStream)
            .filter(
                CatalogUpdateStream.id_product == product.id,
                CatalogUpdateStream.id_ecommerce == product.id_ecommerce,
                CatalogUpdateStream.event_type == "product_state_changed",
                CatalogUpdateStream.status == "pending",
            )
            .order_by(CatalogUpdateStream.created_at.desc())
            .first()
        )

        payload_json = json.dumps(payload_dict, ensure_ascii=False)

        if existing:
            old_priority = existing.priority or 0
            new_priority = max(old_priority, priority)

            existing.priority = new_priority
            existing.payload = payload_json
            existing.available_at = now
            # opcional: limpar erro/attempts, porque é um "novo" pedido lógico
            existing.last_error = None

            log.info(
                "catalog_update_stream: dedupe pending event "
                "id=%s product=%s ecommerce=%s old_priority=%s new_priority=%s reason=%s",
                existing.id,
                product.id,
                product.id_ecommerce,
                old_priority,
                new_priority,
                reason,
            )
            return existing

        # Não havia pending → cria novo
        evt = CatalogUpdateStream(
            id_product=product.id,
            id_ecommerce=product.id_ecommerce,
            event_type="product_state_changed",
            priority=priority,
            status="pending",
            payload=payload_json,
            available_at=now,
        )
        self.db.add(evt)

        log.info(
            "catalog_update_stream: enqueue new pending event "
            "product=%s ecommerce=%s priority=%s reason=%s",
            product.id,
            product.id_ecommerce,
            priority,
            reason,
        )

        return evt

    def claim_pending_batch(
        self,
        *,
        limit: int = 50,
        min_priority: int | None = None,
    ) -> list[CatalogUpdateStream]:
        """
        Vai buscar um batch de eventos `pending` e marca-os como `processing`.
        Não fazemos SKIP LOCKED por agora – 1 consumidor chega e sobra.
        """
        now = datetime.utcnow()

        q = self.db.query(CatalogUpdateStream).filter(
            CatalogUpdateStream.status == "pending",
            CatalogUpdateStream.available_at <= now,
        )
        if min_priority is not None:
            q = q.filter(CatalogUpdateStream.priority >= min_priority)

        q = q.order_by(
            CatalogUpdateStream.priority.desc(),
            CatalogUpdateStream.created_at.asc(),
            CatalogUpdateStream.id.asc(),
        )

        events = q.limit(limit).all()

        for evt in events:
            evt.status = "processing"
            evt.attempts += 1

        log.info(
            "catalog_update_stream: claim_pending_batch " "claimed=%s limit=%s min_priority=%s",
            len(events),
            limit,
            min_priority,
        )

        # commit é responsabilidade do chamador (UoW)
        return events

    def ack_batch(
        self,
        *,
        ids: list[int],
        status: str,
        error: str | None = None,
    ) -> int:
        """
        Marca um conjunto de eventos como concluídos (done|failed).
        """
        now = datetime.utcnow()
        q = self.db.query(CatalogUpdateStream).filter(CatalogUpdateStream.id.in_(ids))

        count = 0
        for evt in q.all():
            evt.status = status
            evt.last_error = error
            evt.processed_at = now
            count += 1

        log.info(
            "catalog_update_stream: ack_batch status=%s count=%s error=%s",
            status,
            count,
            error,
        )

        return count

    def mark_batch_processing(self, *, ids: list[int]) -> int:
        """
        Marca um conjunto de eventos como `processing`.

        A seleção dos eventos a processar deve ser feita por um repositório
        de leitura (CatalogUpdateStreamReadRepository). Aqui apenas aplicamos
        a alteração de estado.
        """
        if not ids:
            return 0

        now = datetime.utcnow()

        q = self.db.query(CatalogUpdateStream).filter(
            CatalogUpdateStream.id.in_(ids),
            CatalogUpdateStream.status == "pending",
        )

        count = 0
        for evt in q.all():
            evt.status = "processing"
            evt.processed_at = now
            count += 1

        log.info(
            "catalog_update_stream: mark_batch_processing ids=%s count=%s",
            ids,
            count,
        )

        return count
