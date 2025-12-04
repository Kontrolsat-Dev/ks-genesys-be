BEGIN;

-- Limpar tudo o que depende de suppliers
TRUNCATE TABLE feed_mappers RESTART IDENTITY CASCADE;
TRUNCATE TABLE supplier_feeds RESTART IDENTITY CASCADE;
TRUNCATE TABLE suppliers RESTART IDENTITY CASCADE;

-- SUPPLIERS
INSERT INTO suppliers (id, name, active, logo_image, contact_name, contact_phone, contact_email,
                       margin, country,
                       ingest_enabled, ingest_interval_minutes, ingest_next_run_at,
                       created_at, updated_at)
VALUES (4, 'Globomatik', TRUE, 'https://patife.kontrolsat.com/static/suppliers/1622570369_fc8b1f0ef8bf32e77374.jpg',
        'Globalmatik', '91245678', 'global@globalmatik.com',
        0.1000, 'ES',
        TRUE, 60, '2025-12-04 03:15:29.117561',
        '2025-11-21 22:39:10.762503', '2025-12-04 02:15:29.120561');

INSERT INTO suppliers (id, name, active, logo_image, contact_name, contact_phone, contact_email,
                       margin, country,
                       ingest_enabled, ingest_interval_minutes, ingest_next_run_at,
                       created_at, updated_at)
VALUES (7, 'ALSO', TRUE, 'https://patife.kontrolsat.com/static/suppliers/1739186697_0da1664a7f4a3039f65c.png', 'Also',
        '22 999 39 00', 'info@jpdi.pt',
        0.1000, 'PT',
        FALSE, 80, '2025-11-29 20:57:18.701611',
        '2025-11-22 00:34:03.083152', '2025-11-29 22:31:46.554298');

INSERT INTO suppliers (id, name, active, logo_image, contact_name, contact_phone, contact_email,
                       margin, country,
                       ingest_enabled, ingest_interval_minutes, ingest_next_run_at,
                       created_at, updated_at)
VALUES (8, 'DMI', TRUE, 'https://patife.kontrolsat.com/static/suppliers/1639046298_20b7c1539d1c6def4dd4.png', 'DMI',
        '912345678', 'dmi@dmi.com',
        0.1000, 'PT',
        TRUE, 60, '2025-12-04 03:18:14.608033',
        '2025-11-22 00:43:36.327155', '2025-12-04 02:18:14.613044');

INSERT INTO suppliers (id, name, active, logo_image, contact_name, contact_phone, contact_email,
                       margin, country,
                       ingest_enabled, ingest_interval_minutes, ingest_next_run_at,
                       created_at, updated_at)
VALUES (9, 'Orima', TRUE, 'https://patife.kontrolsat.com/static/suppliers/1617126912_3d0ff4ab1f5d9b8dbfe2.jpg', 'Orima',
        '912345678', 'comercial@orima.pt',
        0.1000, 'PT',
        TRUE, 60, '2025-12-04 03:18:45.143001',
        '2025-11-22 00:51:30.731857', '2025-12-04 02:18:45.146999');

INSERT INTO suppliers (id, name, active, logo_image, contact_name, contact_phone, contact_email,
                       margin, country,
                       ingest_enabled, ingest_interval_minutes, ingest_next_run_at,
                       created_at, updated_at)
VALUES (13, 'Elektro3', TRUE, 'https://patife.kontrolsat.com/static/suppliers/1645637235_264222edcc14a5c230b9.jpg',
        'Elektro3', '912345678', 'v92@elektro3.com',
        0.1000, 'ES',
        TRUE, 60, '2025-12-04 02:41:00.526354',
        '2025-11-22 19:14:06.288143', '2025-12-04 01:41:00.530892');

INSERT INTO suppliers (id, name, active, logo_image, contact_name, contact_phone, contact_email,
                       margin, country,
                       ingest_enabled, ingest_interval_minutes, ingest_next_run_at,
                       created_at, updated_at)
VALUES (16, 'Expert', TRUE, 'https://patife.kontrolsat.com/static/suppliers/1624268766_ec945048189ea01dd2c7.png',
        'Expert', '960197688', 'Expert@mail.com',
        0.1000, 'PT',
        TRUE, 60, '2025-12-04 02:41:06.011278',
        '2025-12-03 20:00:12.88766', '2025-12-04 01:41:06.015787');


-- FEEDS
INSERT INTO supplier_feeds (id, id_supplier, kind, format, url, active,
                            headers_json, params_json, auth_kind, auth_json,
                            extra_json, csv_delimiter,
                            created_at, updated_at)
VALUES (
    3, 4, 'ftp', 'csv', '.', TRUE,
    NULL, NULL, 'ftp_password',
    '{"host": "nv5.serverhs.org", "port": "21", "username": "globomatik@kontrolsat.com", "password": "Tribune9-Idly-Unsettled"}',
    '{"extra_fields": {"trigger_http_method": "GET", "trigger_http_url": "http://multimedia.globomatik.net/csv/import.php?username=27876&password=509043267&formato=api&type=api_PT&mode=all", "ftp_file_ext": "csv", "ftp_auto_latest": "1"}}',
    ';',
    '2025-11-21 22:43:11.970858', '2025-11-21 22:43:11.970858'
);

INSERT INTO supplier_feeds (id, id_supplier, kind, format, url, active,
                            headers_json, params_json, auth_kind, auth_json,
                            extra_json, csv_delimiter,
                            created_at, updated_at)
VALUES (
    6, 7, 'ftp', 'csv', 'sftp://paco.also.com/pricelist-1.csv.zip', TRUE,
    NULL, NULL, 'ftp_password',
    '{"host": "paco.also.com", "port": "22", "username": "nesofuwexawada", "password": "todi9taci6"}',
    '{"extra_fields": {"compression": "zip", "zip_entry_ext": "csv"}}',
    ';',
    '2025-11-22 00:35:24.063617', '2025-11-22 00:35:24.063617'
);

INSERT INTO supplier_feeds (id, id_supplier, kind, format, url, active,
                            headers_json, params_json, auth_kind, auth_json,
                            extra_json, csv_delimiter,
                            created_at, updated_at)
VALUES (
    7, 8, 'http', 'csv', 'https://www.dmi.es/catalogo.aspx', TRUE,
    NULL,
    '{"u": "CT074858", "p": "yhnadcjj"}',
    'none', NULL,
    '{"method": "GET"}',
    ';',
    '2025-11-22 00:44:10.377282', '2025-11-22 00:44:10.377282'
);

INSERT INTO supplier_feeds (id, id_supplier, kind, format, url, active,
                            headers_json, params_json, auth_kind, auth_json,
                            extra_json, csv_delimiter,
                            created_at, updated_at)
VALUES (
    8, 9, 'http', 'csv',
    'https://www.orima.pt/api/get/products/id/33098/username/suporte@kontrolsat.com/password/509043267/filetype/csv',
    TRUE,
    NULL, NULL, 'none', NULL,
    '{"method": "GET"}',
    ';',
    '2025-11-22 00:52:46.485177', '2025-11-22 00:52:46.485177'
);

INSERT INTO supplier_feeds (id, id_supplier, kind, format, url, active,
                            headers_json, params_json, auth_kind, auth_json,
                            extra_json, csv_delimiter,
                            created_at, updated_at)
VALUES (
    11, 13, 'http', 'json', 'https://api.elektro3.com/api/get-productos/', TRUE,
    NULL, NULL, 'oauth_password',
    '{"token_url": "https://api.elektro3.com/oauth/token", "client_id": "243", "client_secret": "BOT10OuYiTGA6S4ibT0b7suICSDZORZvKaKxqCQn", "username": "suporte@kontrolsat.com", "password": "7FACNIIrKO7zbHY5HDW3", "grant_type": "password", "scope": ""}',
    '{"method": "POST", "pagination": {"mode": "page", "page_field": "page", "size_field": "page_size", "start": 1, "max_pages": 1000, "concurrency": 10, "stop_on_empty": true}}',
    ',',
    '2025-11-22 19:18:30.822334', '2025-11-23 01:29:07.388403'
);

INSERT INTO supplier_feeds (id, id_supplier, kind, format, url, active,
                            headers_json, params_json, auth_kind, auth_json,
                            extra_json, csv_delimiter,
                            created_at, updated_at)
VALUES (
    14, 16, 'http', 'csv', 'https://experteletro.pt/webservice.php', TRUE,
    NULL,
    '{"key": "56b5a57b-3141-11ea-8026-a4bf011b03ee", "pass": "V2prNExLc2ZHYQ=="}',
    'none', NULL,
    '{"method": "GET"}',
    ';',
    '2025-12-03 20:01:57.588001', '2025-12-03 20:01:57.588001'
);


-- MAPPERS
INSERT INTO feed_mappers (id, id_feed, profile_json, version,
                          created_at, updated_at)
VALUES (
    3, 3,
    '{"input": "csv", "fields": {"name": {"source": "Desc. comercial", "required": true}, "gtin": {"source": "Ean", "required": true}, "partnumber": {"source": "Código", "required": true}, "price": {"source": "Preço do PV da Globomatik", "required": true}, "stock": {"source": "Estoque", "required": true}, "description": {"source": "Longa descrição"}, "brand": {"source": "Marca"}, "category": {"source": "Família"}, "mpn": {"source": "Número da peça"}, "image_url": {"source": "Imagem Hd"}}}',
    2,
    '2025-11-21 22:43:26.226547', '2025-11-21 22:43:44.916037'
);

INSERT INTO feed_mappers (id, id_feed, profile_json, version,
                          created_at, updated_at)
VALUES (
    5, 6,
    '{"input": "csv", "fields": {"name": {"source": "Description", "required": true}, "stock": {"source": "AvailableQuantity", "required": true}, "mpn": {"source": "ManufacturerPartNumber"}, "category": {"source": "CategoryText1"}, "brand": {"source": "ManufacturerName"}, "price": {"source": "NetPrice", "required": true}, "weight": {"source": "GrossMass"}, "gtin": {"source": "EuropeanArticleNumber", "required": true}, "ProductID": {"source": "ManufacturerPartNumber"}, "partnumber": {"source": "ManufacturerPartNumber", "required": true}}}',
    2,
    '2025-11-22 00:36:58.214361', '2025-11-22 00:38:11.613031'
);

INSERT INTO feed_mappers (id, id_feed, profile_json, version,
                          created_at, updated_at)
VALUES (
    6, 7,
    '{"input": "csv", "fields": {"name": {"source": "DENOMINA", "required": true}, "gtin": {"source": "EAN", "required": true}, "partnumber": {"source": "ARTICULO", "required": true}, "price": {"source": "COMPRA", "required": true}, "stock": {"source": "STOCK", "required": true}, "description": {"source": "LONGDESC"}, "brand": {"source": "MARCA"}, "category": {"source": "FAMILIA"}, "weight": {"source": "PESO"}, "mpn": {"source": "CODIGO_FABRICANTE"}, "image_url": {"source": "IMAGEN"}, "volume": {"source": "VOLUMEN"}}}',
    1,
    '2025-11-22 00:48:14.645043', '2025-11-22 00:48:14.645043'
);

INSERT INTO feed_mappers (id, id_feed, profile_json, version,
                          created_at, updated_at)
VALUES (
    7, 8,
    '{"input": "csv", "fields": {"name": {"source": "description", "required": true}, "gtin": {"source": "ean13", "required": true}, "partnumber": {"source": "reference", "required": true}, "price": {"source": "wholesale_price", "required": true}, "stock": {"source": "stock", "required": true, "trim": true, "value_map": {"e": "0", "f": "0"}}, "description": {"source": "details"}, "brand": {"source": "brand"}, "category": {"source": "family"}, "weight": {"source": "reference"}, "mpn": {"source": "reference"}, "image_url": {"source": "image"}, "energy_class": {"source": "energy_class_string"}, "dimensions": {"source": "dimensions"}, "specs": {"source": "specs"}, "volume": {"source": "volume"}}}',
    1,
    '2025-11-22 00:56:09.759518', '2025-11-22 00:56:09.759518'
);

INSERT INTO feed_mappers (id, id_feed, profile_json, version,
                          created_at, updated_at)
VALUES (
    10, 11,
    '{"input": "json", "fields": {"name": {"source": "nombre", "required": true}, "gtin": {"source": "ean13", "required": true}, "partnumber": {"source": "codigo", "required": true}, "price": {"source": "precio", "required": true}, "stock": {"source": "stock", "required": true}, "description": {"source": "descripcion", "required": false}, "brand": {"source": "marca", "required": false}, "category": {"source": "categoria", "required": false}, "weight": {"source": "peso", "required": false}, "mpn": {"source": "codigo", "required": false}, "image_url": {"source": "imagen", "required": false}, "descatalogado": {"source": "descatalogado", "required": false}, "destacado": {"source": "destacado", "required": false}, "outlet": {"source": "outlet", "required": false, "value_map": {"0": "False", "1": "True"}}}, "rules": [{"when": [{"eq": ["$descatalogado", 1]}], "set": {"stock": "0"}}]}',
    2,
    '2025-11-22 19:19:02.709', '2025-11-22 19:34:57.126639'
);

INSERT INTO feed_mappers (id, id_feed, profile_json, version,
                          created_at, updated_at)
VALUES (
    11, 14,
    '{"input": "csv", "fields": {"name": {"source": "nome", "required": true}, "gtin": {"source": "ean", "required": true}, "partnumber": {"source": "referencia", "required": true}, "price": {"source": "preco", "required": true}, "stock": {"source": "disponibilidade", "trim": true, "lowercase": true, "value_map": {"indisponivel": "0", "limitado": "1", "disponivel": "2", "Limitado": "1", "Disponivel": "2"}, "required": true}, "description": {"source": "resumo"}, "brand": {"source": "marcas"}, "category": {"source": "familia"}, "mpn": {"source": "partnumber"}, "image_url": {"source": "galeria"}}}',
    2,
    '2025-12-03 20:01:59.568433', '2025-12-03 20:02:26.453069'
);

-- ajustar sequences
SELECT setval('suppliers_id_seq',       (SELECT COALESCE(MAX(id), 1) FROM suppliers),       true);
SELECT setval('supplier_feeds_id_seq',  (SELECT COALESCE(MAX(id), 1) FROM supplier_feeds),  true);
SELECT setval('feed_mappers_id_seq',    (SELECT COALESCE(MAX(id), 1) FROM feed_mappers),    true);

COMMIT;
