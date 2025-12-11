-- ⚠️ Limpa TUDO excepto fornecedores (suppliers, supplier_feeds, feed_mappers)
-- Executar em ambiente de desenvolvimento apenas.

-- 1. Catalog Update Stream (eventos para PrestaShop)
TRUNCATE TABLE catalog_update_stream CASCADE;

-- 2. Ofertas ativas
TRUNCATE TABLE products_active_offers CASCADE;

-- 3. Eventos de supplier por produto
TRUNCATE TABLE products_suppliers_events CASCADE;

-- 4. Metadata de produtos
TRUNCATE TABLE product_meta CASCADE;

-- 5. Items de supplier (ofertas dos fornecedores - ligação feed<->produto)
TRUNCATE TABLE supplier_items CASCADE;

-- 6. Runs de feeds (histórico de execuções)
TRUNCATE TABLE feed_runs CASCADE;

-- 7. Produtos
TRUNCATE TABLE products CASCADE;

-- 8. Categorias e Marcas
TRUNCATE TABLE categories CASCADE;
TRUNCATE TABLE brands CASCADE;

-- 9. Worker jobs (opcional - limpa histórico de jobs)
TRUNCATE TABLE worker_jobs CASCADE;
