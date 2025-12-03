app
├─ api
│ ├─ v1
│ │ ├─ auth.py
│ │ ├─ brands.py
│ │ ├─ catalog_update_stream.py
│ │ ├─ categories.py
│ │ ├─ feeds.py
│ │ ├─ mappers.py
│ │ ├─ products.py
│ │ ├─ runs.py
│ │ ├─ suppliers.py
│ │ ├─ system.py
│ │ ├─ worker_jobs.py
│ │ └─ **init**.py
│ └─ **init**.py
├─ background
│ ├─ job_handlers.py
│ └─ **init**.py
├─ core
│ ├─ deps
│ │ ├─ external
│ │ │ ├─ feeds.py
│ │ │ ├─ prestashop.py
│ │ │ └─ **init**.py
│ │ ├─ providers.py
│ │ ├─ security.py
│ │ ├─ uow.py
│ │ └─ **init**.py
│ ├─ config.py
│ ├─ deps.py
│ ├─ errors.py
│ ├─ http_errors.py
│ ├─ logging.py
│ ├─ middleware.py
│ ├─ normalize.py
│ └─ **init**.py
├─ domains
│ ├─ auth
│ │ ├─ usecases
│ │ │ ├─ login.py
│ │ │ └─ **init**.py
│ │ └─ **init**.py
│ ├─ catalog
│ │ ├─ services
│ │ │ ├─ active_offer.py
│ │ │ ├─ mappers.py
│ │ │ ├─ product_detail.py
│ │ │ ├─ series.py
│ │ │ ├─ sync_events.py
│ │ │ └─ **init**.py
│ │ ├─ usecases
│ │ │ ├─ brands
│ │ │ │ ├─ list_brands.py
│ │ │ │ └─ **init**.py
│ │ │ ├─ catalog_update_stream
│ │ │ │ ├─ ack_events.py
│ │ │ │ ├─ get_pending_events.py
│ │ │ │ ├─ list_events.py
│ │ │ │ └─ **init**.py
│ │ │ ├─ categories
│ │ │ │ ├─ list_categories.py
│ │ │ │ └─ **init**.py
│ │ │ ├─ products
│ │ │ │ ├─ get_product_by_gtin.py
│ │ │ │ ├─ get_product_detail.py
│ │ │ │ ├─ list_active_offer_price_changes.py
│ │ │ │ ├─ list_catalog_price_changes.py
│ │ │ │ ├─ list_products.py
│ │ │ │ ├─ update_margin.py
│ │ │ │ └─ **init**.py
│ │ │ └─ **init**.py
│ │ └─ **init**.py
│ ├─ mapping
│ │ ├─ engine.py
│ │ └─ **init**.py
│ ├─ procurement
│ │ ├─ services
│ │ │ ├─ active_offer_sync.py
│ │ │ ├─ feed_loader.py
│ │ │ ├─ row_ingest.py
│ │ │ └─ **init**.py
│ │ ├─ usecases
│ │ │ ├─ feeds
│ │ │ │ ├─ delete_supplier_feed.py
│ │ │ │ ├─ get_by_supplier.py
│ │ │ │ ├─ test_feed.py
│ │ │ │ ├─ upsert_supplier_feed.py
│ │ │ │ └─ **init**.py
│ │ │ ├─ mappers
│ │ │ │ ├─ get_by_supplier.py
│ │ │ │ ├─ get_mapper.py
│ │ │ │ ├─ put_mapper.py
│ │ │ │ ├─ validate_mapper.py
│ │ │ │ └─ **init**.py
│ │ │ ├─ runs
│ │ │ │ ├─ ingest_supplier.py
│ │ │ │ └─ **init**.py
│ │ │ ├─ suppliers
│ │ │ │ ├─ create_supplier.py
│ │ │ │ ├─ delete_supplier.py
│ │ │ │ ├─ get_supplier_detail.py
│ │ │ │ ├─ list_suppliers.py
│ │ │ │ ├─ update_bundle.py
│ │ │ │ └─ **init**.py
│ │ │ └─ **init**.py
│ │ └─ **init**.py
│ ├─ worker
│ │ ├─ usecases
│ │ │ ├─ list_worker_jobs.py
│ │ │ ├─ schedule_supplier_ingest_jobs.py
│ │ │ └─ **init**.py
│ │ └─ **init**.py
│ └─ **init**.py
├─ external
│ ├─ feed_downloader.py
│ ├─ ftp_downloader.py
│ ├─ http_downloader.py
│ ├─ prestashop_client.py
│ ├─ sftp_downloader.py
│ └─ **init**.py
├─ helpers
│ ├─ number_conversions.py
│ └─ **init**.py
├─ infra
│ ├─ base.py
│ ├─ bootstrap.py
│ ├─ session.py
│ ├─ uow.py
│ └─ **init**.py
├─ models
│ ├─ brand.py
│ ├─ catalog_update_stream.py
│ ├─ category.py
│ ├─ enums.py
│ ├─ feed_mapper.py
│ ├─ feed_run.py
│ ├─ product.py
│ ├─ product_active_offer.py
│ ├─ product_meta.py
│ ├─ product_supplier_event.py
│ ├─ supplier.py
│ ├─ supplier_feed.py
│ ├─ supplier_item.py
│ ├─ worker_activity_config.py
│ ├─ worker_job.py
│ └─ **init**.py
├─ repositories
│ ├─ catalog
│ │ ├─ read
│ │ │ ├─ brand_read_repo.py
│ │ │ ├─ catalog_update_stream_read_repo.py
│ │ │ ├─ category_read_repo.py
│ │ │ ├─ products_read_repo.py
│ │ │ ├─ product_active_offer_read_repo.py
│ │ │ ├─ product_meta_read_repo.py
│ │ │ └─ **init**.py
│ │ ├─ write
│ │ │ ├─ brand_write_repo.py
│ │ │ ├─ catalog_update_stream_write_repo.py
│ │ │ ├─ category_write_repo.py
│ │ │ ├─ product_active_offer_write_repo.py
│ │ │ ├─ product_write_repo.py
│ │ │ └─ **init**.py
│ │ └─ **init**.py
│ ├─ procurement
│ │ ├─ read
│ │ │ ├─ feed_run_read_repo.py
│ │ │ ├─ mapper_read_repo.py
│ │ │ ├─ product_event_read_repo.py
│ │ │ ├─ supplier_feed_read_repo.py
│ │ │ ├─ supplier_item_read_repo.py
│ │ │ ├─ supplier_read_repo.py
│ │ │ └─ **init**.py
│ │ ├─ write
│ │ │ ├─ feed_run_write_repo.py
│ │ │ ├─ mapper_write_repo.py
│ │ │ ├─ product_event_write_repo.py
│ │ │ ├─ supplier_feed_write_repo.py
│ │ │ ├─ supplier_item_write_repo.py
│ │ │ ├─ supplier_write_repo.py
│ │ │ └─ **init**.py
│ │ └─ **init**.py
│ ├─ worker
│ │ ├─ read
│ │ │ ├─ worker_activity_read_repo.py
│ │ │ ├─ worker_job_read_repo.py
│ │ │ └─ **init**.py
│ │ ├─ write
│ │ │ ├─ worker_activity_write_repo.py
│ │ │ ├─ worker_job_write_repo.py
│ │ │ └─ **init**.py
│ │ └─ **init**.py
│ └─ **init**.py
├─ schemas
│ ├─ auth.py
│ ├─ brands.py
│ ├─ catalog_update_stream.py
│ ├─ categories.py
│ ├─ feeds.py
│ ├─ mappers.py
│ ├─ products.py
│ ├─ suppliers.py
│ ├─ system.py
│ ├─ worker_jobs.py
│ └─ **init**.py
├─ shared
│ ├─ jwt.py
│ └─ **init**.py
└─ **init**.py
