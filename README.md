
```
Backend
├─ .pre-commit-config.yaml
├─ app
│  ├─ api
│  │  ├─ v1
│  │  │  ├─ auth.py
│  │  │  ├─ brands.py
│  │  │  ├─ catalog_update_stream.py
│  │  │  ├─ categories.py
│  │  │  ├─ feeds.py
│  │  │  ├─ mappers.py
│  │  │  ├─ products.py
│  │  │  ├─ runs.py
│  │  │  ├─ suppliers.py
│  │  │  ├─ system.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ core
│  │  ├─ config.py
│  │  ├─ deps
│  │  │  ├─ external
│  │  │  │  ├─ feeds.py
│  │  │  │  ├─ prestashop.py
│  │  │  │  └─ __init__.py
│  │  │  ├─ providers.py
│  │  │  ├─ security.py
│  │  │  ├─ uow.py
│  │  │  └─ __init__.py
│  │  ├─ deps.py
│  │  ├─ errors.py
│  │  ├─ http_errors.py
│  │  ├─ logging.py
│  │  ├─ middleware.py
│  │  ├─ normalize.py
│  │  └─ __init__.py
│  ├─ domains
│  │  ├─ auth
│  │  │  ├─ usecases
│  │  │  │  ├─ login.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  ├─ catalog
│  │  │  ├─ services
│  │  │  │  ├─ active_offer.py
│  │  │  │  ├─ mappers.py
│  │  │  │  ├─ product_detail.py
│  │  │  │  ├─ series.py
│  │  │  │  ├─ sync_events.py
│  │  │  │  └─ __init__.py
│  │  │  ├─ usecases
│  │  │  │  ├─ brands
│  │  │  │  │  ├─ list_brands.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ catalog_update_stream
│  │  │  │  │  ├─ ack_events.py
│  │  │  │  │  ├─ get_pending_events.py
│  │  │  │  │  ├─ list_events.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ categories
│  │  │  │  │  ├─ list_categories.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ products
│  │  │  │  │  ├─ get_product_by_gtin.py
│  │  │  │  │  ├─ get_product_detail.py
│  │  │  │  │  ├─ list_products.py
│  │  │  │  │  ├─ update_margin.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  ├─ mapping
│  │  │  ├─ engine.py
│  │  │  └─ __init__.py
│  │  ├─ procurement
│  │  │  ├─ usecases
│  │  │  │  ├─ feeds
│  │  │  │  │  ├─ delete_supplier_feed.py
│  │  │  │  │  ├─ get_by_supplier.py
│  │  │  │  │  ├─ test_feed.py
│  │  │  │  │  ├─ upsert_supplier_feed.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ mappers
│  │  │  │  │  ├─ get_by_supplier.py
│  │  │  │  │  ├─ get_mapper.py
│  │  │  │  │  ├─ put_mapper.py
│  │  │  │  │  ├─ validate_mapper.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ runs
│  │  │  │  │  ├─ ingest_supplier.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ suppliers
│  │  │  │  │  ├─ create_supplier.py
│  │  │  │  │  ├─ delete_supplier.py
│  │  │  │  │  ├─ get_supplier_detail.py
│  │  │  │  │  ├─ list_suppliers.py
│  │  │  │  │  ├─ update_bundle.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ external
│  │  ├─ feed_downloader.py
│  │  ├─ ftp_downloader.py
│  │  ├─ http_downloader.py
│  │  ├─ prestashop_client.py
│  │  ├─ sftp_downloader.py
│  │  └─ __init__.py
│  ├─ helpers
│  │  ├─ number_conversions.py
│  │  └─ __init__.py
│  ├─ infra
│  │  ├─ base.py
│  │  ├─ bootstrap.py
│  │  ├─ session.py
│  │  ├─ uow.py
│  │  └─ __init__.py
│  ├─ models
│  │  ├─ brand.py
│  │  ├─ catalog_update_stream.py
│  │  ├─ category.py
│  │  ├─ enums.py
│  │  ├─ feed_mapper.py
│  │  ├─ feed_run.py
│  │  ├─ product.py
│  │  ├─ product_active_offer.py
│  │  ├─ product_meta.py
│  │  ├─ product_supplier_event.py
│  │  ├─ supplier.py
│  │  ├─ supplier_feed.py
│  │  ├─ supplier_item.py
│  │  └─ __init__.py
│  ├─ repositories
│  │  ├─ catalog
│  │  │  ├─ read
│  │  │  │  ├─ brand_read_repo.py
│  │  │  │  ├─ catalog_update_stream_read_repo.py
│  │  │  │  ├─ category_read_repo.py
│  │  │  │  ├─ products_read_repo.py
│  │  │  │  ├─ product_active_offer_read_repo.py
│  │  │  │  ├─ product_meta_read_repo.py
│  │  │  │  └─ __init__.py
│  │  │  ├─ write
│  │  │  │  ├─ brand_write_repo.py
│  │  │  │  ├─ catalog_update_stream_write_repo.py
│  │  │  │  ├─ category_write_repo.py
│  │  │  │  ├─ product_active_offer_write_repo.py
│  │  │  │  ├─ product_write_repo.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  ├─ procurement
│  │  │  ├─ read
│  │  │  │  ├─ feed_run_read_repo.py
│  │  │  │  ├─ mapper_read_repo.py
│  │  │  │  ├─ product_event_read_repo.py
│  │  │  │  ├─ supplier_feed_read_repo.py
│  │  │  │  ├─ supplier_item_read_repo.py
│  │  │  │  ├─ supplier_read_repo.py
│  │  │  │  └─ __init__.py
│  │  │  ├─ write
│  │  │  │  ├─ feed_run_write_repo.py
│  │  │  │  ├─ mapper_write_repo.py
│  │  │  │  ├─ product_event_write_repo.py
│  │  │  │  ├─ supplier_feed_write_repo.py
│  │  │  │  ├─ supplier_item_write_repo.py
│  │  │  │  ├─ supplier_write_repo.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ schemas
│  │  ├─ auth.py
│  │  ├─ brands.py
│  │  ├─ catalog_update_stream.py
│  │  ├─ categories.py
│  │  ├─ feeds.py
│  │  ├─ mappers.py
│  │  ├─ products.py
│  │  ├─ suppliers.py
│  │  ├─ system.py
│  │  └─ __init__.py
│  ├─ shared
│  │  ├─ jwt.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ apps
│  ├─ api_main.py
│  └─ __init__.py
├─ docs
│  └─ elektro3_mapper.md
├─ Makefile
├─ pyproject.toml
├─ README.md
└─ requirements.txt

```
