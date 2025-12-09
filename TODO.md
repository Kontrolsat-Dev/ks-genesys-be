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

## Funcionalidades Pendentes

### Importação para PrestaShop
- [ ] Endpoint para importar produto para o PrestaShop
- [ ] Atribuir `id_ecommerce` após importação
- [ ] Sincronização inicial de categorias/marcas

### Dropshipping (Futuro)
- [ ] Modelo `Order` (encomenda do cliente)
- [ ] Modelo `SupplierOrder` (encomenda ao fornecedor)
- [ ] Gestão de tracking
- [ ] Pagamentos a fornecedores
- [ ] Notas de encomenda

---

## Notas

- Arquitetura atual: `Route → Schema → UseCase → Service/Repository`
- CQRS: Repos separados em `read/` e `write/`
- Domínios: `catalog`, `procurement`, `worker`, `mapping`, `auth`
