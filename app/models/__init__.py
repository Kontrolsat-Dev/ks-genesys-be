# app/models/__init__.py
from app.infra.base import Base  # re-export

from .audit_log import AuditLog
from .brand import Brand
from .category import Category
from .enums import FEED_FORMAT, FEED_KIND, RUN_STATUS
from .feed_mapper import FeedMapper
from .feed_run import FeedRun
from .product import Product
from .product_meta import ProductMeta
from .product_supplier_event import ProductSupplierEvent
from .supplier import Supplier
from .supplier_feed import SupplierFeed
from .supplier_item import SupplierItem
from .product_active_offer import ProductActiveOffer
from .catalog_update_stream import CatalogUpdateStream
from .worker_activity_config import WorkerActivityConfig
from .worker_job import WorkerJob
from .platform_config import PlatformConfig

__all__ = [
    "Base",
    "AuditLog",
    "Brand",
    "Category",
    "FEED_KIND",
    "FEED_FORMAT",
    "RUN_STATUS",
    "FeedMapper",
    "FeedRun",
    "Product",
    "ProductMeta",
    "ProductSupplierEvent",
    "Supplier",
    "SupplierFeed",
    "SupplierItem",
    "ProductActiveOffer",
    "CatalogUpdateStream",
    "WorkerActivityConfig",
    "WorkerJob",
    "PlatformConfig",
]


def create_db_and_tables(bind=None) -> None:
    """
    Cria todas as tabelas definidas pelos modelos.
    Se `bind` não for passado, usa o engine padrão.
    """
    if bind is None:
        from app.infra.session import engine as _engine

        bind = _engine
    Base.metadata.create_all(bind=bind)
