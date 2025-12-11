from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product_supplier_event import ProductSupplierEvent
from app.models.supplier_item import SupplierItem


@dataclass
class UnseenItemsStockResult:
    affected_products: list[int]
    items_total: int  # todos os unseen
    items_stock_zeroed: int  # quantos foram >0 -> 0
    items_already_zero: int  # quantos já estavam a 0


class ProductEventWriteRepository:
    def __init__(self, db: Session):
        self.db = db

    def record_from_item_change(
        self,
        *,
        id_product: int,
        id_supplier: int,
        gtin: str | None,
        new_price: str,
        new_stock: int,
        created: bool,
        changed: bool,
        id_feed_run: int,
    ) -> int:
        """
        Regista evento apenas se houve criação ou alteração do SupplierItem.
        Não faz flush/commit; o UoW decide.
        """
        if not (created or changed):
            return 0

        reason = "init" if created else "change"
        self.db.add(
            ProductSupplierEvent(
                id_product=id_product,
                id_supplier=id_supplier,
                gtin=gtin,
                price=new_price,
                stock=new_stock,
                id_feed_run=id_feed_run,
                reason=reason,
            )
        )
        return 1

    def mark_unseen_items_stock_zero(
        self, *, id_feed: int, id_supplier: int, id_feed_run: int
    ) -> UnseenItemsStockResult:
        unseen_items = self.db.scalars(
            select(SupplierItem).where(
                SupplierItem.id_feed == id_feed,
                SupplierItem.id_feed_run != id_feed_run,
            )
        ).all()

        affected_products: set[int] = set()
        items_total = 0
        items_stock_zeroed = 0
        items_already_zero = 0

        for it in unseen_items:
            items_total += 1

            if (it.stock or 0) == 0:
                # já estava a zero → apenas avança o run
                it.id_feed_run = id_feed_run
                items_already_zero += 1
            else:
                # transição >0 → 0 → evento "ficou sem stock neste feed"
                it.stock = 0
                it.id_feed_run = id_feed_run

                self.db.add(
                    ProductSupplierEvent(
                        id_product=it.id_product,
                        id_supplier=id_supplier,
                        gtin=it.gtin,
                        price=it.price,
                        stock=0,
                        id_feed_run=id_feed_run,
                        reason="feed_missing",
                    )
                )
                items_stock_zeroed += 1

            affected_products.add(it.id_product)

        return UnseenItemsStockResult(
            affected_products=list(affected_products),
            items_total=items_total,
            items_stock_zeroed=items_stock_zeroed,
            items_already_zero=items_already_zero,
        )
