from __future__ import annotations
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

        # ═══════════════════════════════════════════════
        # CATALOG - READ
        # ═══════════════════════════════════════════════
        self.products = ProductReadRepository(db_session)
        self.brands = BrandReadRepository(db_session)
        self.categories = CategoryReadRepository(db_session)
        self.product_meta = ProductMetaReadRepository(db_session)
        self.active_offers = ProductActiveOfferReadRepository(db_session)
        self.catalog_events = CatalogUpdateStreamReadRepository(db_session)

        # ═══════════════════════════════════════════════
        # CATALOG - WRITE
        # ═══════════════════════════════════════════════
        self.products_w = ProductWriteRepository(db_session)
        self.brands_w = BrandWriteRepository(db_session)
        self.categories_w = CategoryWriteRepository(db_session)
        self.active_offers_w = ProductActiveOfferWriteRepository(db_session)
        self.catalog_events_w = CatalogUpdateStreamWriteRepository(db_session)

        # ═══════════════════════════════════════════════
        # PROCUREMENT - READ
        # ═══════════════════════════════════════════════
        self.suppliers = SupplierReadRepository(db_session)
        self.feeds = SupplierFeedReadRepository(db_session)
        self.feed_runs = FeedRunReadRepository(db_session)
        self.mappers = MapperReadRepository(db_session)
        self.supplier_items = SupplierItemReadRepository(db_session)
        self.product_events = ProductEventReadRepository(db_session)

        # ═══════════════════════════════════════════════
        # PROCUREMENT - WRITE
        # ═══════════════════════════════════════════════
        self.suppliers_w = SupplierWriteRepository(db_session)
        self.feeds_w = SupplierFeedWriteRepository(db_session)
        self.feed_runs_w = FeedRunWriteRepository(db_session)
        self.mappers_w = MapperWriteRepository(db_session)
        self.supplier_items_w = SupplierItemWriteRepository(db_session)
        self.product_events_w = ProductEventWriteRepository(db_session)

        # ═══════════════════════════════════════════════
        # WORKER - READ/WRITE
        # ═══════════════════════════════════════════════
        self.worker_jobs = WorkerJobReadRepository(db_session)
        self.worker_jobs_w = WorkerJobWriteRepository(db_session)
        self.worker_activity = WorkerActivityReadRepository(db_session)
        self.worker_activity_w = WorkerActivityWriteRepository(db_session)

        # ═══════════════════════════════════════════════
        # AUDIT - READ/WRITE
        # ═══════════════════════════════════════════════
        self.audit_logs = AuditLogReadRepository(db_session)
        self.audit_logs_w = AuditLogWriteRepository(db_session)

        # ═══════════════════════════════════════════════
        # CONFIG - READ/WRITE
        # ═══════════════════════════════════════════════
        self.platform_config = PlatformConfigReadRepository(db_session)
        self.platform_config_w = PlatformConfigWriteRepository(db_session)

        # ═══════════════════════════════════════════════
        # ORDERS DROPSHIPPING - READ/WRITE
        # ═══════════════════════════════════════════════
        self.dropshipping_orders = DropshippingOrderReadRepository(db_session)
        self.dropshipping_order_lines = DropshippingOrderLineReadRepository(db_session)
        self.supplier_orders = SupplierOrderReadRepository(db_session)
        self.dropshipping_orders_w = DropshippingOrderWriteRepository(db_session)
        self.dropshipping_order_lines_w = DropshippingOrderLineWriteRepository(db_session)
        self.supplier_orders_w = SupplierOrderWriteRepository(db_session)

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

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc or not self._committed:
            self.rollback()
