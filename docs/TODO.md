# TODO - Genesys Backend

## Arquitetura & Refactoring

### 🔴 Alta Prioridade

- [x] **Fallback de margem Supplier → Produto** ✅
  - Decisão: Não implementar fallback — produtos só são criados via ingest e herdam margem do supplier
  - Documentado em: `products_read_repo.py` (`get_product_margin`)

- [x] **Incluir `margin` na listagem de produtos** ✅
  - Adicionado `Product.margin` à `_base_query()` em `products_read_repo.py`

### 🟡 Média Prioridade

- [x] **Mover `get()` de Write Repos para Read Repos** ✅
  - Decisão: Manter como "lookups auxiliares para writes" (CQRS pragmático)
  - Documentado em: `supplier_write_repo.py` e `product_write_repo.py`

- [x] **Remover `= None` desnecessário em parâmetros UoW** ✅
  - Corrigido em: `suppliers.py`, `runs.py`, `products.py`

### 🟢 Baixa Prioridade

- [x] **Adicionar Schema de output para `/mappers/ops`** ✅
  - Criado `MappingOpOut` e `MappingOpsOut` em `app/schemas/mappers.py`
  - Endpoint atualizado para usar `response_model=MappingOpsOut`

- [x] **Documentar padrão de UseCase a chamar UseCase** ✅
  - Exemplo: `update_bundle.py` chama `get_supplier_detail.py`
  - Decisão: Em CQRS puro seria separado, mas para UX é mais prático
  - Documentado em: `app/domains/procurement/usecases/suppliers/update_bundle.py`

---

## Importação PrestaShop

> Ver algoritmos de implementação: [prestashop_import_plan.md](./prestashop_import_plan.md)

### Phase 0: EOL Feature (Time-Based)

- [x] Índice parcial `ix_pse_stock_positive` em `ProductSupplierEvent`
- [x] UseCase `mark_eol_products.py`
- [x] Query `list_products_to_mark_eol()` em `ProductEventReadRepo`
- [x] Job kind `JOB_KIND_PRODUCT_EOL_CHECK` em `job_handlers.py`
- [x] Reverter `is_eol = False` quando stock > 0 durante ingest
- [x] Enfileirar evento PS quando produto marcado EOL
- [x] Configurar scheduling diário do job EOL em `worker_main.py`

### Phase 1: Category Mapping

- [x] Adicionar campos ao modelo `Category`: `id_ps_category`, `ps_category_name`, `auto_import`
- [x] Atualizar schemas em `app/schemas/categories.py`
- [x] Criar endpoints de mapeamento: `PUT /{id}/mapping`, `DELETE /{id}/mapping`, `GET /mapped`
- [x] Criar usecase `update_category_mapping.py`
- [x] Atualizar frontend `/categories` com UI de mapeamento

### Phase 1.5: Bulk Import Manual (UI)

- [x] Criar schemas `BulkImportIn`, `BulkImportOut` ✅
- [x] Criar endpoint `POST /products/bulk-import` ✅
- [x] Criar usecase `bulk_import.py` ✅
- [x] Adicionar checkboxes na tabela de produtos (frontend) ✅
- [x] Adicionar botão "Importar Selecionados" (frontend) ✅
- [x] Criar modal de confirmação com preview ✅
- [x] Suporte a margens por categoria (`category_margins`) ✅

### Phase 2: Auto-Import Worker

- [x] Adicionar `JOB_KIND_PRODUCT_AUTO_IMPORT` em `job_handlers.py` ✅
- [x] Criar usecase `auto_import_new_products.py` ✅
- [x] Registar novo job kind no `worker_main.py` ✅
- [x] Configurar scheduling (4h intervalo) ✅
- [x] Lógica `auto_import_since` para importar só produtos novos ✅

### Phase 3: Stock/Price Sync

- [x] **Refatorar ProductActiveOffer sync** ✅
  - `ProductActiveOffer` só atualizada quando `/ack` recebe `status=done`
  - Corrigido cálculo de margem (removido `/100` desnecessário)
  - Adicionado `get_by_ids()` ao `CatalogUpdateStreamReadRepository`
  - `active_offer_sync.py` usa `select_best_offer_for_import()` sem persistir
  - `sync_events.py` modificado para aceitar `BestOfferResult`
  - `ack_events.py` atualiza `ProductActiveOffer` com dados do payload

- [x] **Frontend: Fixed active offer display** ✅
  - `product-stats.tsx` usa `unit_price_sent` do backend, não calcula dinamicamente

- [x] **Filtro imported** ✅
  - Adicionado `imported=true|false` ao endpoint `/products`
  - Filtra por `id_ecommerce IS NOT NULL AND > 0`

- [ ] Integrar sync no processamento do `CatalogUpdateStream` (cronjob PS)

### Phase 4: Relatórios (Futuro)

- [ ] Gerar relatório após ciclo de importação
- [ ] Registar campos em falta (marca, peso, etc.)
- [ ] UI para visualizar relatórios

---
## Configurações de plataforma
- [ ] Guardar configurações de plataforma em banco de dados
- [ ] UI para visualizar configurações de plataforma
---
## Notificações por utilizador
- [ ] Implementar notificações de stock
- [ ] Implementar notificações de preço
- [ ] Implementar notificações de importação
- [ ] Implementar notificações de EOL
- [ ] Outras notificações que sejam pretinentes para o utilizador

---

## Dropshipping (Futuro)

- [ ] Modelo `Order` (encomenda do cliente)
- [ ] Modelo `SupplierOrder` (encomenda ao fornecedor)
- [ ] Gestão de tracking
- [ ] Pagamentos a fornecedores
- [ ] Notas de encomenda

---

## Notas

- Arquitetura atual: `Route → Schema → UseCase → Service/Repository`
- CQRS: Repos separados em `read/` e `write/`
- Domínios: `catalog`, `procurement`, `worker`, `mapping`, `auth`, `prestashop`
- PrestaShop 1.7.6.7: Campo `upc` determina stock físico vs virtual


- Arredondamentos
[x] Produtos com preço arredondado para .40 ou .90 (c/ IVA) ✅
 - Implementado em: `price_rounding.py`
 - Integrado em: `active_offer.py`, `catalog_update_stream_write_repo.py`
 - Frontend: `margin-preview-card.tsx` com preview visual
