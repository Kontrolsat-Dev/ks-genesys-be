from __future__ import annotations
from typing import Any
from app.repositories.orders_dropshipping.write.dropshipping_order_write_repo import (
    DropshippingOrderWriteRepository,
    DropshippingOrderLineWriteRepository,
    SupplierOrderWriteRepository,
)
from app.repositories.orders_dropshipping.read.dropshipping_order_read_repo import (
    DropshippingOrderReadRepository,
    DropshippingOrderLineReadRepository,
    SupplierOrderReadRepository,
)
from sqlalchemy.orm import Session
from app.repositories.catalog.read.product_read_repo import ProductReadRepository
from app.repositories.catalog.read.brand_read_repo import BrandReadRepository
from app.repositories.catalog.read.category_read_repo import CategoryReadRepository
from app.repositories.catalog.read.product_meta_read_repo import ProductMetaReadRepository
from app.repositories.catalog.read.product_active_offer_read_repo import (
    ProductActiveOfferReadRepository,
)
from app.repositories.catalog.read.catalog_update_stream_read_repo import (
    CatalogUpdateStreamReadRepository,
)
from app.repositories.catalog.write.product_write_repo import ProductWriteRepository
from app.repositories.catalog.write.brand_write_repo import BrandWriteRepository
from app.repositories.catalog.write.category_write_repo import CategoryWriteRepository
from app.repositories.catalog.write.product_active_offer_write_repo import (
    ProductActiveOfferWriteRepository,
)
from app.repositories.catalog.write.catalog_update_stream_write_repo import (
    CatalogUpdateStreamWriteRepository,
)
from app.repositories.procurement.read.supplier_read_repo import SupplierReadRepository
from app.repositories.procurement.read.supplier_feed_read_repo import SupplierFeedReadRepository
from app.repositories.procurement.read.feed_run_read_repo import FeedRunReadRepository
from app.repositories.procurement.read.mapper_read_repo import MapperReadRepository
from app.repositories.procurement.read.supplier_item_read_repo import SupplierItemReadRepository
from app.repositories.procurement.read.product_event_read_repo import ProductEventReadRepository
from app.repositories.procurement.write.supplier_write_repo import SupplierWriteRepository
from app.repositories.procurement.write.supplier_feed_write_repo import SupplierFeedWriteRepository
from app.repositories.procurement.write.feed_run_write_repo import FeedRunWriteRepository
from app.repositories.procurement.write.mapper_write_repo import MapperWriteRepository
from app.repositories.procurement.write.supplier_item_write_repo import SupplierItemWriteRepository
from app.repositories.procurement.write.product_event_write_repo import ProductEventWriteRepository
from app.repositories.worker.read.worker_job_read_repo import WorkerJobReadRepository
from app.repositories.worker.read.worker_activity_read_repo import WorkerActivityReadRepository
from app.repositories.worker.write.worker_job_write_repo import WorkerJobWriteRepository
from app.repositories.worker.write.worker_activity_write_repo import WorkerActivityWriteRepository
from app.repositories.audit.read.audit_log_read_repo import AuditLogReadRepository
from app.repositories.audit.write.audit_log_write_repo import AuditLogWriteRepository
from app.repositories.config.read.platform_config_read_repo import PlatformConfigReadRepository
from app.repositories.config.write.platform_config_write_repo import PlatformConfigWriteRepository

# app/infra/uow.py
# Unit of Work para SQLAlchemy - Centraliza acesso a repositórios e gestão de transações


class UoW:
    """
    Unit of Work - Centraliza acesso a repositórios e gestão de transações.

    Todos os repositórios partilham a mesma sessão de base de dados.
    As operações de commit/rollback afetam todas as alterações pendentes.
    """

    def __init__(self, db_session: Session) -> None:
        self._db = db_session
        self._committed = False
        self._repos = {}

    def _get_repo(self, name: str, repo_class: Any) -> Any:
        if name not in self._repos:
            self._repos[name] = repo_class(self._db)
        return self._repos[name]

    # ═══════════════════════════════════════════════
    # CATALOG - READ
    # ═══════════════════════════════════════════════

    @property
    def products(self) -> ProductReadRepository:
        return self._get_repo("products", ProductReadRepository)

    @property
    def brands(self) -> BrandReadRepository:
        return self._get_repo("brands", BrandReadRepository)

    @property
    def categories(self) -> CategoryReadRepository:
        return self._get_repo("categories", CategoryReadRepository)

    @property
    def product_meta(self) -> ProductMetaReadRepository:
        return self._get_repo("product_meta", ProductMetaReadRepository)

    @property
    def active_offers(self) -> ProductActiveOfferReadRepository:
        return self._get_repo("active_offers", ProductActiveOfferReadRepository)

    @property
    def catalog_events(self) -> CatalogUpdateStreamReadRepository:
        return self._get_repo("catalog_events", CatalogUpdateStreamReadRepository)

    # ═══════════════════════════════════════════════
    # CATALOG - WRITE
    # ═══════════════════════════════════════════════

    @property
    def products_w(self) -> ProductWriteRepository:
        return self._get_repo("products_w", ProductWriteRepository)

    @property
    def brands_w(self) -> BrandWriteRepository:
        return self._get_repo("brands_w", BrandWriteRepository)

    @property
    def categories_w(self) -> CategoryWriteRepository:
        return self._get_repo("categories_w", CategoryWriteRepository)

    @property
    def active_offers_w(self) -> ProductActiveOfferWriteRepository:
        return self._get_repo("active_offers_w", ProductActiveOfferWriteRepository)

    @property
    def catalog_events_w(self) -> CatalogUpdateStreamWriteRepository:
        return self._get_repo("catalog_events_w", CatalogUpdateStreamWriteRepository)

    # ═══════════════════════════════════════════════
    # PROCUREMENT - READ
    # ═══════════════════════════════════════════════

    @property
    def suppliers(self) -> SupplierReadRepository:
        return self._get_repo("suppliers", SupplierReadRepository)

    @property
    def feeds(self) -> SupplierFeedReadRepository:
        return self._get_repo("feeds", SupplierFeedReadRepository)

    @property
    def feed_runs(self) -> FeedRunReadRepository:
        return self._get_repo("feed_runs", FeedRunReadRepository)

    @property
    def mappers(self) -> MapperReadRepository:
        return self._get_repo("mappers", MapperReadRepository)

    @property
    def supplier_items(self) -> SupplierItemReadRepository:
        return self._get_repo("supplier_items", SupplierItemReadRepository)

    @property
    def product_events(self) -> ProductEventReadRepository:
        return self._get_repo("product_events", ProductEventReadRepository)

    # ═══════════════════════════════════════════════
    # PROCUREMENT - WRITE
    # ═══════════════════════════════════════════════

    @property
    def suppliers_w(self) -> SupplierWriteRepository:
        return self._get_repo("suppliers_w", SupplierWriteRepository)

    @property
    def feeds_w(self) -> SupplierFeedWriteRepository:
        return self._get_repo("feeds_w", SupplierFeedWriteRepository)

    @property
    def feed_runs_w(self) -> FeedRunWriteRepository:
        return self._get_repo("feed_runs_w", FeedRunWriteRepository)

    @property
    def mappers_w(self) -> MapperWriteRepository:
        return self._get_repo("mappers_w", MapperWriteRepository)

    @property
    def supplier_items_w(self) -> SupplierItemWriteRepository:
        return self._get_repo("supplier_items_w", SupplierItemWriteRepository)

    @property
    def product_events_w(self) -> ProductEventWriteRepository:
        return self._get_repo("product_events_w", ProductEventWriteRepository)

    # ═══════════════════════════════════════════════
    # WORKER - READ/WRITE
    # ═══════════════════════════════════════════════

    @property
    def worker_jobs(self) -> WorkerJobReadRepository:
        return self._get_repo("worker_jobs", WorkerJobReadRepository)

    @property
    def worker_jobs_w(self) -> WorkerJobWriteRepository:
        return self._get_repo("worker_jobs_w", WorkerJobWriteRepository)

    @property
    def worker_activity(self) -> WorkerActivityReadRepository:
        return self._get_repo("worker_activity", WorkerActivityReadRepository)

    @property
    def worker_activity_w(self) -> WorkerActivityWriteRepository:
        return self._get_repo("worker_activity_w", WorkerActivityWriteRepository)

    # ═══════════════════════════════════════════════
    # AUDIT - READ/WRITE
    # ═══════════════════════════════════════════════

    @property
    def audit_logs(self) -> AuditLogReadRepository:
        return self._get_repo("audit_logs", AuditLogReadRepository)

    @property
    def audit_logs_w(self) -> AuditLogWriteRepository:
        return self._get_repo("audit_logs_w", AuditLogWriteRepository)

    # ═══════════════════════════════════════════════
    # CONFIG - READ/WRITE
    # ═══════════════════════════════════════════════

    @property
    def platform_config(self) -> PlatformConfigReadRepository:
        return self._get_repo("platform_config", PlatformConfigReadRepository)

    @property
    def platform_config_w(self) -> PlatformConfigWriteRepository:
        return self._get_repo("platform_config_w", PlatformConfigWriteRepository)

    # ═══════════════════════════════════════════════
    # ORDERS DROPSHIPPING - READ/WRITE
    # ═══════════════════════════════════════════════

    @property
    def dropshipping_orders(self) -> DropshippingOrderReadRepository:
        return self._get_repo("dropshipping_orders", DropshippingOrderReadRepository)

    @property
    def dropshipping_order_lines(self) -> DropshippingOrderLineReadRepository:
        return self._get_repo("dropshipping_order_lines", DropshippingOrderLineReadRepository)

    @property
    def supplier_orders(self) -> SupplierOrderReadRepository:
        return self._get_repo("supplier_orders", SupplierOrderReadRepository)

    @property
    def dropshipping_orders_w(self) -> DropshippingOrderWriteRepository:
        return self._get_repo("dropshipping_orders_w", DropshippingOrderWriteRepository)

    @property
    def dropshipping_order_lines_w(self) -> DropshippingOrderLineWriteRepository:
        return self._get_repo("dropshipping_order_lines_w", DropshippingOrderLineWriteRepository)

    @property
    def supplier_orders_w(self) -> SupplierOrderWriteRepository:
        return self._get_repo("supplier_orders_w", SupplierOrderWriteRepository)

    @property
    def db(self) -> Session:
        """Acesso directo à sessão para casos especiais (evitar quando possível)."""
        return self._db

    def commit(self) -> None:
        """Confirma todas as alterações pendentes na base de dados."""
        self._db.commit()
        self._committed = True

    def rollback(self) -> None:
        """Reverte todas as alterações pendentes."""
        self._db.rollback()
        self._committed = True

    def __enter__(self) -> UoW:
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        if _exc_type or not self._committed:
            self.rollback()
