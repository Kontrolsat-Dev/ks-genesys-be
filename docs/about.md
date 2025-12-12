1. Contexto de negócio

Tens uma loja PrestaShop (Kontrolsat) que vende eletrodomésticos / eletrónica.

O Genesys Stock Manager é o backend “cérebro”:

centraliza produtos de vários fornecedores,

lê feeds de stock/preço,

decide qual é a melhor oferta (ProductActiveOffer),

e fala com o PrestaShop para criar/atualizar/desativar produtos.

2. Arquitetura geral
Backend (Genesys v2)

Stack: FastAPI + SQLAlchemy + Pydantic v2.

Estilo: monólito organizado por domínios:

auth

catalog (produtos, brands, categories, ofertas ativas)

procurement (suppliers, feeds, mappers, ingest)

worker (fila de jobs & scheduler)

prestashop (integrações específicas com a loja)

Há uma Unit of Work (UoW) que dá acesso aos repositórios e gere a transação.

Convenções importantes

Usecases (em domains/*/usecases) NÃO importam models diretamente.

Falam apenas com UoW + repositórios (ports).

Repositórios de leitura (*ReadRepository) fazem queries mais ricas com joins.

Repositórios de escrita (*WriteRepository) alteram estado (insert/update/delete).

Os models SQLAlchemy (app/models/*) só são usados dentro de repositórios/infra.

3. Domínio Procurement: ingest de feeds

Objetivo: transformar feeds de fornecedores em produtos + ofertas no catálogo.

Entidades principais

Supplier: fornecedor (nome, margin, flags de ingest, intervalo de ingest, etc.).

SupplierFeed: configuração do feed (URL, formato CSV/JSON, headers, auth, etc.).

FeedMapper: profile JSON para mapear colunas do feed → campos canónicos.

FeedRun: registo de cada execução de ingest (status, métricas).

SupplierItem: “oferta do fornecedor” (id_feed, id_product, sku, price, stock…).

Product: produto canónico do catálogo (gtin, brand, partnumber, margin, etc.).

ProductMeta: key/value extra por produto.

ProductSupplierEvent: histórico de eventos por produto + supplier

(reason: init/change/feed_missing/eol futuramente, etc.).

ProductActiveOffer: oferta “eleita” por produto (melhor custo/stock para vender).

CatalogUpdateStream: fila de eventos product_state_changed para PrestaShop.

WorkerJob / WorkerActivityConfig: fila e configuração do worker.

Fluxo de ingest (ingest_supplier)

Job supplier_ingest → usecase ingest_supplier faz:

Valida Supplier + SupplierFeed, cria FeedRun.

Faz download do feed via FeedDownloader (CSV/JSON, com suporte a paginação).

Usa IngestEngine + mapper do feed para transformar cada linha numa estrutura:

product_payload (gtin, mpn/partnumber, name, description, image_url, weight…)

offer_payload (price, stock, sku, gtin, partnumber)

meta_payload (resto dos campos).

Para cada linha, process_row:

Resolve/Cria Product:

se tiver GTIN → GTIN manda;

senão → tenta dedupe por (brand + partnumber);

se não tiver nenhuma chave → linha inválida.

Preenche campos canónicos vazios do Product (fill_canonicals_if_empty).

Cria/associa Brand e Category se ainda não existirem (fill_brand_category_if_empty).

Adiciona entradas em ProductMeta para campos extra.

Faz upsert de SupplierItem (oferta do fornecedor) com price/stock/sku.

Se a oferta foi criada/alterada → regista ProductSupplierEvent (reason=init/change).

No fim de processar o feed:

Chama mark_unseen_items_stock_zero:

todos os SupplierItem daquele feed que não apareceram nesta run:

se stock já era 0 → só atualiza id_feed_run;

se stock > 0 → mete stock=0 e cria ProductSupplierEvent (reason="feed_missing").

Isto não é EOL de produto, é apenas “este fornecedor deixou de listar esta oferta neste feed”.

Junta todos os id_product afetados (linhas processadas + unseen items).

Para esses produtos:

Recalcula ProductActiveOffer (melhor oferta disponível).

Compara snapshot anterior vs novo:

se houve mudança relevante (supplier, preço enviado, stock enviado)
→ enfileira evento em CatalogUpdateStream com reason="ingest_supplier".

4. Worker: jobs e scheduler
Job kinds atuais

supplier_ingest: corre ingest de um fornecedor.

(Estamos a introduzir) product_eol_check: corre lógica de EOL de produtos.

Funcionamento do worker (apps/worker_main.py)

Loop infinito que faz:

Garante que existe uma configuração base por job_kind em WorkerActivityConfig
(max_concurrency, backoff, stale_after_seconds, poll_interval_seconds, etc.).

Watchdog:

marca jobs running demasiados tempo como failed,

aplica backoff e tentativa seguinte.

Scheduler de supplier_ingest:

schedule_supplier_ingest_jobs:

para cada Supplier com ingest_enabled = TRUE,

se não existir job ativo (pending/running) para aquele supplier,

cria job supplier_ingest com job_key = "supplier_ingest:{id_supplier}".

Atualiza supplier.ingest_next_run_at (campo apenas para UI).

Depois de cada run terminar, _schedule_next_for_supplier_after_run:

calcula próxima data de ingest com base em ingest_interval_minutes,

cria novo job para esse supplier com not_before = finished_at + intervalo.

Execução de jobs:

Vai buscar jobs pending por job_kind até ao limite de max_concurrency.

Para cada job:

chama dispatch_job(job_kind, payload_json, uow).

se correr bem → mark_done.

se falhar → mark_failed com backoff e controlo de tentativas.

5. Distinção importante: “produto não visto” vs EOL verdadeiro

Nós acabámos de limpar a confusão aqui:

“Produto não visto no feed” (per-feed):

Implementado por mark_unseen_items_stock_zero.

Apenas significa: esta oferta específica deste fornecedor não apareceu nesta run.

Efeito:

stock da oferta daquele fornecedor vai a 0,

regista ProductSupplierEvent com reason="feed_missing",

recalcula ProductActiveOffer e pode disparar evento para PrestaShop se isso afetar o produto.

Não mexe no product.is_eol.

“Produto EOL” (nível de catálogo, verdadeiro end-of-life):

Regra de negócio que definiste:

Se um produto está no catálogo há ≥ 180 dias
e:

nunca teve stock > 0
ou

o último evento de stock > 0 é anterior ao cutoff (hoje - 180 dias)

→ então é considerado EOL → product.is_eol = True.

Isto é independente de apenas “não aparecer num feed”; é uma visão global do produto no tempo.

6. Worker de EOL (product_eol_check)

Estamos agora a introduzir:

Um novo job kind: product_eol_check.

Um usecase mark_eol_products no domínio catalog que:

usa repos de leitura (eventos + produtos) para encontrar candidatos a EOL:

Product.created_at < cutoff (180 dias),

Product.is_eol = False,

e:

nunca teve ProductSupplierEvent com stock > 0, ou

o último stock > 0 é anterior ao cutoff.

marca product.is_eol = True via ProductWriteRepository.set_eol.

se o produto tiver id_ecommerce (já está ligado ao PrestaShop):

enfileira um evento em CatalogUpdateStream com reason="eol_marked",

para o consumidor Prestashop desativar o produto.

Além disso:

No process_row da ingest, sempre que uma oferta entra com stock > 0, estamos a implementar a reversão:

product.is_eol = False (via ProductWriteRepository.set_eol ou semelhante)

e consequentemente será emitido um novo product_state_changed para reativar no PrestaShop.

7. Integração com PrestaShop
Lado Genesys

CatalogUpdateStream:

é a fila interna onde enfileiramos eventos product_state_changed.

o payload inclui:

product (gtin, partnumber, name, margin, is_enabled, is_eol, etc.)

active_offer (id_supplier, id_supplier_item, unit_cost, unit_price_sent, stock_sent)

reason (ex: "ingest_supplier", "margin_changed", "eol_marked", etc.).

Repositório CatalogUpdateStreamWriteRepository cuida de:

deduplicar: no máximo 1 pending por produto/ecommerce,

juntar prioridades (stock 0→>0 mais prioritário, etc.).

O consumer (worker ou outro processo) vai ler esta fila e chamar o PrestaShop via módulo r_genesys.

Lado PrestaShop

Tens um módulo custom r_genesys que já expõe endpoints como:

/r_genesys/getcategories (sem categoria “Todos os Produtos”)

/r_genesys/getbrands

Estão planeados/implementados endpoints para:

criar produtos no PrestaShop a partir do Genesys (import inicial),

atualizar stock/preço/estado (active) com base no CatalogUpdateStream.

Os próximos passos (que já temos em checklist):

Category mapping:

extender Category com campos:

id_ps_category, ps_category_name, auto_import.

endpoints de mapeamento,

UI no frontend para ligar categorias Genesys → categorias PrestaShop.

Auto-import worker:

job product_auto_import que:

encontra produtos sem id_ecommerce em categorias com auto_import=True,

com ProductActiveOffer válido (preço, stock),

cria o produto no PrestaShop desativado (active=0),

guarda id_ecommerce.

Sync stock/preço:

consumer de CatalogUpdateStream que:

para produtos com id_ecommerce,

chama endpoints no PrestaShop para atualizar preço, stock e active (quando EOL, etc.).

8. Estado atual (dev)

Limpaste o catálogo em dev com um script SQL que fez TRUNCATE a:

catalog_update_stream, products_active_offers,

products_suppliers_events, product_meta,

supplier_items, feed_runs,

products, categories, brands,

worker_jobs.

Re-seedaste os worker_jobs chamando a API:

POST /api/v1/worker/jobs/supplier-ingests/schedule

(e ajustámos o usecase para não depender de ingest_next_run_at IS NULL como gate).

O ingest de fornecedores já voltou a correr e:

recriou produtos, offers, eventos e active_offers,

voltou a preencher o catálogo.

Estamos agora a implementar:

separação clara entre “stock zero por desaparecimento no feed” e “EOL real”,

worker product_eol_check + usecase mark_eol_products,

emissão de product_state_changed com reason="eol_marked" para desativar produtos EOL no PrestaShop.
