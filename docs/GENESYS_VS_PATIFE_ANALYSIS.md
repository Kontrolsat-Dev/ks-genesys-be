# Análise Comparativa: Genesys vs Patife

**Data**: 12 de Dezembro de 2024
**Contexto**: Avaliação técnica das duas plataformas de gestão de catálogo
**Status**: Patife em produção | Genesys em desenvolvimento

---

## Resumo Executivo

| Aspecto | Patife | Genesys |
|---------|--------|---------|
| **Stack Backend** | PHP (CodeIgniter 4) | Python (FastAPI) |
| **Stack Frontend** | Server-side (Views PHP) | SPA (React + Vite + TypeScript) |
| **Arquitetura** | MVC Tradicional | DDD + CQRS + Clean Architecture |
| **Padrão de Dados** | Active Record via Models | Repository Pattern + Unit of Work |
| **Tipagem** | Dinâmica (PHP) | Estática (Python + TypeScript) |
| **Maturidade** | Concluído | Em desenvolvimento |

---

## Estrutura de Diretórios

### Patife (MVC Tradicional)

```
patife/
├── app/
│   ├── Controllers/     # 20+ controllers monolíticos
│   ├── Models/          # 24 models (Active Record)
│   ├── Views/           # 53 views (server-side rendering)
│   ├── Entities/        # 27 entidades (DTOs)
│   ├── Libraries/       # 66 bibliotecas auxiliares
│   ├── Helpers/
│   └── Config/
├── public/
└── tests/
```

### Genesys (Domain-Driven Design)

```
Genesys-Stock-Manager-Backend/
├── app/
│   ├── api/v1/          # 13 routers (thin layer)
│   ├── domains/         # Lógica de negócio por domínio
│   │   ├── auth/
│   │   ├── catalog/
│   │   │   ├── usecases/    # 22 usecases granulares
│   │   │   └── services/    # 6 services reutilizáveis
│   │   ├── procurement/
│   │   ├── prestashop/
│   │   ├── mapping/
│   │   └── worker/
│   ├── repositories/    # CQRS (read/ e write/)
│   │   ├── catalog/
│   │   │   ├── read/    # Query repositories
│   │   │   └── write/   # Command repositories
│   │   └── procurement/
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic validation
│   ├── core/
│   └── infra/           # UoW, Database
└── apps/                # CLI e scheduled jobs

Genesys-Stock-Manger-Frontend/
├── src/
│   ├── features/        # Feature-based architecture
│   │   ├── products/
│   │   ├── suppliers/
│   │   ├── prices/
│   │   └── system/
│   ├── api/
│   ├── components/      # Shared components
│   └── lib/
```

---

## Análise Detalhada

### 1. Separação de Responsabilidades

#### Patife
```php
// Controllers/Products.php - 562 linhas
class Products extends PresenterController {
    public function export($id) {
        // Validação + Lógica de negócio + Acesso a BD + Integração externa
        // Tudo no mesmo método (~100 linhas)
    }
}
```

Controllers com 500+ linhas que misturam apresentação, lógica de negócio e acesso a dados.

#### Genesys
```python
# api/v1/products.py - Router fino (~340 linhas para 10 endpoints)
@router.get("")
def list_products(uow: UowDep, ...):
    return list_products_usecase.execute(uow, ...)

# domains/catalog/usecases/products/list_products.py - 110 linhas
def execute(uow: UoW, *, page, page_size, ...):
    repo = ProductsReadRepository(uow.db)
    rows, total = repo.list_products(...)
    # Lógica de negócio isolada
```

Camadas bem definidas: Routes → Usecases → Services → Repositories → Models

---

### 2. Padrão Repository (CQRS)

#### Patife
```php
// Models usam Active Record directamente nos Controllers
$products = model('ProductsModel')->findAll();
$products->update($id, $data);
```

#### Genesys
```python
# Repositórios separados para leitura e escrita
repositories/
├── catalog/
│   ├── read/
│   │   ├── products_read_repo.py     # Queries complexas
│   │   ├── category_read_repo.py
│   │   └── brand_read_repo.py
│   └── write/
│       ├── products_write_repo.py    # Mutações
│       └── category_write_repo.py
```

CQRS (Command Query Responsibility Segregation) permite:
- Queries optimizadas para leitura com joins complexos
- Writes simples e focados
- Facilidade de escalar reads e writes independentemente

---

### 3. Gestão de Transações

#### Patife
```php
// Transações geridas manualmente ou pelo framework
$db->transStart();
// operações...
$db->transComplete();
```

#### Genesys
```python
# Unit of Work centralizado
class UoW:
    def __init__(self, db: Session):
        self.db = db

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

# Injectado automaticamente via Depends
def list_products(uow: UowDep, ...):
```

---

### 4. Validação e Tipagem

#### Patife
```php
protected $validationRules = [
    'id_prestashop' => 'permit_empty|integer',
    'name' => 'required|max_length[128]',
];
```

#### Genesys
```python
# Pydantic Schemas com tipagem estrita
class ProductListItemOut(BaseModel):
    id: int
    gtin: str
    name: str
    brand: str | None = None
    category: str | None = None
    offers: list[OfferOut] = []
    best_offer: OfferOut | None = None
```

FastAPI gera OpenAPI/Swagger automaticamente a partir dos schemas.

---

### 5. Frontend

#### Patife
- Server-side rendering com PHP views
- JavaScript inline ou jQuery
- Acoplamento forte entre backend e frontend

#### Genesys
- SPA com React + TypeScript + Vite
- Feature-based architecture organizada por domínio
- API-first: Backend RESTful + Pydantic → Frontend React Query + TypeScript
- Componentes reutilizáveis com Shadcn/UI

---

## Avaliação Comparativa

| Critério | Patife | Genesys |
|----------|:------:|:-------:|
| **Manutenibilidade** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Testabilidade** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Escalabilidade** | ⭐⭐ | ⭐⭐⭐⭐ |
| **Separação de Camadas** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Tipagem/Documentação** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Curva de Aprendizagem** | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Produção/Estabilidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## Métricas da Análise

| Métrica | Patife | Genesys Backend | Genesys Frontend |
|---------|--------|-----------------|------------------|
| **Ficheiros de código** | ~285 | ~183 | ~179 |
| **Controllers/Routes** | 27 | 13 | - |
| **Models** | 24 | 16 | - |
| **UseCases** | - | ~50+ | - |
| **Repositórios** | - | ~37 (read/write) | - |
| **Features (FE)** | - | - | 8 |

---

## Funcionalidades Implementadas

| Funcionalidade | Patife | Genesys | Notas |
|----------------|:------:|:-------:|-------|
| **Catálogo de Produtos** | ✅ | ✅ | Genesys tem facets dinâmicos e UI moderna |
| **Gestão de Marcas** | ✅ | ✅ | Similar em ambos |
| **Gestão de Categorias** | ✅ | ✅ | Genesys com mapeamento PrestaShop melhorado |
| **Importar para PrestaShop** | ✅ | ✅ | Genesys com auto-import |
| **Alterar Margens** | ✅ | ✅ | Genesys com histórico |
| **Histórico de Preços** | ❌ | ✅ | Exclusivo Genesys |
| **Best Offer Automático** | Parcial | ✅ | Genesys calcula automaticamente |
| **Price Change Alerts** | ❌ | ✅ | Exclusivo Genesys |
| **Gestão de Encomendas** | ✅ | ❌ | Exclusivo Patife |
| **Gestão de Pagamentos** | ✅ | ❌ | Exclusivo Patife |
| **Sistema de Tickets** | ✅ | ❌ | Exclusivo Patife |
| **Gestão de Shipping** | ✅ | ❌ | Exclusivo Patife |
| **Worker Jobs Visibility** | ❌ | ✅ | Exclusivo Genesys |
| **Comparação KuantoKusta** | ✅ | ❌ | Exclusivo Patife |

---

## Integrações de Fornecedores

| Patife | Genesys |
|--------|---------|
| **33 integrações hardcoded** (PHP) | **Feeds configuráveis** (XML/CSV/JSON) |
| Novo fornecedor = desenvolvimento | Novo fornecedor = configuração |
| 8-14KB código por fornecedor | Sem código adicional |

---

## Matriz de Decisão

| Critério | Peso | Patife | Genesys |
|----------|:----:|:------:|:-------:|
| **Gestão de Catálogo** | Alto | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Gestão de Preços** | Alto | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Gestão de Encomendas** | Crítico | ⭐⭐⭐⭐ | ❌ |
| **Pagamentos** | Alto | ⭐⭐⭐⭐ | ❌ |
| **UX/Interface** | Médio | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Extensibilidade** | Alto | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Maturidade** | Alto | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## Roadmap Sugerido para Genesys

1. **Fase 1** (Actual): Catálogo, Preços, Importação ✅
2. **Fase 2**: Sistema de Encomendas
3. **Fase 3**: Gestão de Pagamentos
4. **Fase 4**: Sistema de Tickets
5. **Fase 5**: Migração completa

---

# Análise de Performance e Processamento de Catálogos

## Arquitectura de Ingestão

### Patife - Round-Robin com php spark

```
┌─────────────────────────────────────────────────────┐
│              php spark (orquestrador)               │
│         Navega tarefa em tarefa (round-robin)       │
└────────────────────────┬────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼
┌────────────┐    ┌────────────┐    ┌────────────┐
│ Supplier A │    │ Supplier B │    │ Supplier C │
│   10s max  │ →  │   10s max  │ →  │   10s max  │ → ...
└────────────┘    └────────────┘    └────────────┘
      │
      ▼
┌─────────────────────────────────────────────────┐
│  Dentro dos 10s por tarefa:                     │
│  1. Retoma de current_line (onde parou)         │
│  2. Lê ofertas linha-a-linha                    │
│  3. Actualiza produtos/preços/stock             │
│  4. Guarda current_line antes de sair           │
│  5. Passa para próxima tarefa                   │
└─────────────────────────────────────────────────┘
```

**Vantagem**: Todos os fornecedores são processados de forma justa
**Problema**: Catálogos grandes demoram várias rondas a completar. Com 33 fornecedores e catálogos grandes, a actualização de preços e stock fica demasiado lenta.

### Genesys - Worker Async com Job Queue

```
┌─────────────────────────────────────────────────────┐
│               Worker Loop (asyncio)                 │
│            worker_main.py (300 linhas)              │
└────────────────────────┬────────────────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌────────────────┐
│  Scheduler   │ │   Watchdog   │ │  Job Executor  │
│  (criar jobs)│ │(stale→failed)│ │ (processar)    │
└──────────────┘ └──────────────┘ └────────────────┘
                                           │
                   ┌───────────────────────┘
                   ▼
          ┌────────────────────────────────────────┐
          │     ingest_supplier.py (261 linhas)    │
          │                                        │
          │  1. Cria FeedRun (tracking)            │
          │  2. Download + parse (CSV/JSON/XML)    │
          │  3. Suporte a paginação                │
          │  4. Batch processing (500 rows/log)    │
          │  5. Transacções por job                │
          │  6. mark_unseen_items_stock_zero       │
          │  7. sync_active_offer                  │
          │  8. Finaliza FeedRun (ok/error)        │
          └────────────────────────────────────────┘
```

---

## Comparação Técnica

| Aspecto | Patife | Genesys |
|---------|--------|---------|
| **Execução** | Síncrona (PHP) | Async (Python asyncio) |
| **Timeout** | 10 segundos | Configurável (1-2 horas) |
| **Recovery** | Manual via current_line | Automático (watchdog + retry) |
| **Retry** | Nenhum | Backoff exponencial |
| **Throttle** | usleep(100) hardcoded | Sem throttle artificial |
| **Concorrência** | Nenhuma (sequencial) | Configurável por job_kind |
| **Logging** | Mínimo | Progress a cada 500 rows |
| **Tracking** | Nenhum | FeedRun completo |
| **Formatos** | Hardcoded por supplier | Configurável (CSV/JSON/XML) |
| **Paginação** | Não suportado | Suportado nativamente |

---

## Limitações do Patife

### 1. Timeout de 10 Segundos
```php
const TIMEOUT = 10;  // BaseTask.php linha 12

// Resultado: feeds grandes = múltiplas execuções
if (time() >= $timeout) {
    $meta['current_line']->value = $currentLine;
    return;  // Interrompe e guarda posição
}
```

Um catálogo com 10.000 produtos e timeout de 10s precisa de dezenas de execuções para completar.

### 2. Delay Artificial Entre Linhas
```php
usleep(100);  // 0.1ms por linha
// 10.000 linhas = 1 segundo de delay total
```

### 3. Sem Recovery Automático
- Se a task falhar, precisa de intervenção manual
- Não há retry com backoff
- Sem watchdog para jobs stale

### 4. Código Duplicado por Fornecedor
- 33 ficheiros PHP (8-14KB cada)
- Mapeamento hardcoded por fornecedor
- Adicionar novo fornecedor = desenvolvimento

### 5. Sem Logging de Comunicação ao PrestaShop
- Não há registo do que foi enviado
- Não há confirmação de sucesso/falha
- Impossível auditar o que foi comunicado

### 6. Sem Sistema de Prioridades
- Todas as alterações têm a mesma prioridade
- Updates críticos (stock zero) podem ficar em fila

---

## Vantagens do Genesys

### 1. Watchdog para Jobs Stale
```python
# Se job está "running" há mais de 1-2 horas → failed
stale_count = job_w.mark_stale_running_jobs_as_failed(
    job_kind=job_kind,
    now=now,
    stale_after=timedelta(seconds=stale_after_seconds),
    max_attempts=max_attempts,
    backoff_seconds=backoff_seconds,
)
```

### 2. Retry Automático com Backoff
```python
job_w.mark_failed(
    job.id_job,
    finished_at=finished_at,
    error_message=err_msg,
    max_attempts=cfg.max_attempts,
    backoff_seconds=cfg.backoff_seconds,
)
```

### 3. FeedRun Tracking
- `start()` → cria run com timestamp
- `finalize_ok()` → rows_total, rows_changed, rows_failed
- `finalize_error()` → guarda mensagem de erro
- Histórico completo de todas as runs

### 4. Itens Não Vistos → Stock Zero
```python
# Produtos que não vieram no feed = stock 0
unseen_res = ev_w.mark_unseen_items_stock_zero(
    id_feed=feed.id,
    id_supplier=id_supplier,
    id_feed_run=id_run,
)
```

### 5. Active Offer Sync
```python
# Recalcula melhor oferta para produtos afectados
sync_active_offer_for_products(
    db, prod_r,
    affected_products=affected_products,
    reason="ingest_supplier",
)
```

---

## Performance Estimada

| Cenário | Patife | Genesys |
|---------|--------|---------|
| **10.000 produtos** | Várias rondas (10s/ronda) | 1-3 minutos |
| **Erro a meio** | Retoma na próxima ronda | Retry automático |
| **Novo fornecedor** | 1-2 dias dev | 30 min config |
| **Catálogo paginado** | Não suportado | Suportado |
| **Logging envios PS** | Não disponível | Disponível |

---

## Funcionalidades Avançadas do Genesys

### 1. Workers Dinâmicos
- Criação de workers com base na quantidade de tarefas pendentes
- Scale automático para picos de processamento

### 2. Sistema de Prioridades (CatalogUpdateStream)

| Prioridade | Evento | Exemplo |
|:----------:|--------|---------|
| **Alta** | Entrada de stock | Stock 0 → 5 (produto volta a estar disponível) |
| **Alta** | Remoção de stock | Stock 5 → 0 (produto indisponível) |
| **Alta** | Mudança de preço | Preço alterou significativamente |
| **Baixa** | Pequena variação stock | Stock 2 → 3 (não afecta disponibilidade) |
| **Baixa** | EOL de produto | Produto marcado como end-of-life |

Após importação, só comunicamos **stock** e **preço** ao PrestaShop. Dados do produto (nome, descrição, imagens) não são actualizados.

### 3. Consumer PrestaShop Inteligente
- Adapta workload à quantidade de eventos pendentes
- Aproveita baixo movimento de madrugada para processar mais dados
- Balanceamento automático carga/hora

| Horário | Workload Consumer PS |
|---------|----------------------|
| Dia (9h-21h) | Conservador (não sobrecarregar) |
| Noite (21h-9h) | Agressivo (processar backlog) |

---

# Adaptabilidade a Integrações Futuras

## Comparação de Stacks

| Aspecto | Patife (PHP/CI4) | Genesys (Python/FastAPI) |
|---------|------------------|--------------------------|
| **AI/ML Libraries** | Limitado (PHP-ML básico) | Excelente (PyTorch, TensorFlow, LangChain, etc) |
| **MCP (Model Context Protocol)** | Sem suporte | Nativamente Python |
| **Kafka/Message Queues** | Possível mas complexo | Fácil (kafka-python, aiokafka) |
| **Async/Event-Driven** | Limitado (Swoole/ReactPHP) | Nativo (asyncio, aiohttp) |
| **API Schemas** | Manual | Auto-gerado (OpenAPI/Pydantic) |
| **Type Safety** | Dinâmico | Estático (typing, Pydantic) |
| **Microservices** | Difícil | Natural (FastAPI é leve) |

---

## Preparação para AI

### Patife
```php
// PHP não é ecossistema natural para AI/ML
// Teria que fazer calls a serviços externos Python
$response = file_get_contents('http://ai-service/predict?data=...');
```

### Genesys
```python
# Python é a linguagem de AI/ML
from langchain import LLMChain
from openai import OpenAI

# Integração directa no código
async def ai_categorize_product(product: Product) -> str:
    chain = LLMChain(...)
    return await chain.arun(product.description)
```

---

## Preparação para MCP (Model Context Protocol)

| Aspecto | Patife | Genesys |
|---------|--------|---------|
| **SDK Oficial** | Não existe para PHP | Python SDK oficial |
| **Integração** | Teria que criar wrapper | Plug-and-play |
| **Tools/Resources** | N/A | Pode expor como MCP server |

---

## Preparação para Kafka/Event Streaming

### Patife
- Requer extensão PHP-RdKafka
- Documentação limitada
- Comunidade pequena

### Genesys
```python
# Async Kafka consumer nativo
from aiokafka import AIOKafkaConsumer

async def consume_events():
    consumer = AIOKafkaConsumer('catalog-updates')
    async for msg in consumer:
        await process_update(msg)
```

---

## Arquitectura para Futuro

### Patife (Monolítico)
```
┌─────────────────────────────────┐
│     CodeIgniter 4 (PHP)         │
│  ┌───────────────────────────┐  │
│  │ Controllers + Views + DB  │  │ ← Tudo acoplado
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### Genesys (Preparado para Microservices)
```
┌─────────────────────────────────────────────────────┐
│                    API Gateway                       │
└─────────────────────┬───────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌──────────┐
│ Catalog │    │ Procurement │    │  Worker  │
│ Service │    │   Service   │    │ Service  │
└─────────┘    └─────────────┘    └──────────┘
    │                 │                 │
    └─────────────────┼─────────────────┘
                      ▼
              ┌─────────────┐
              │ Kafka/Redis │  ← Event Bus
              └─────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌──────────┐
│   AI    │    │     MCP     │    │ External │
│ Service │    │   Server    │    │   APIs   │
└─────────┘    └─────────────┘    └──────────┘
```

---

## Integrações Futuras - Resumo

| Tecnologia | Patife | Genesys |
|------------|:------:|:-------:|
| **AI/ML** | ⭐ | ⭐⭐⭐⭐⭐ |
| **MCP** | ❌ | ⭐⭐⭐⭐⭐ |
| **Kafka** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Microservices** | ⭐⭐ | ⭐⭐⭐⭐ |
| **OpenAPI** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Async** | ⭐⭐ | ⭐⭐⭐⭐⭐ |

Python é a linguagem do ecossistema AI/ML. O Genesys está posicionado para integrar com LLMs, embeddings, vector databases, e o ecossistema MCP.

---

# Conclusão Geral

## Limitações Actuais do Patife

O Patife apresenta **bottlenecks críticos** que afectam as operações:

- **Lentidão na actualização de produtos**: O sistema round-robin com timeout de 10 segundos por tarefa não escala com o aumento de fornecedores e produtos.
- **Não aguenta muitos fornecedores**: Com 33 fornecedores e catálogos grandes, a actualização de preços e stock fica demasiado lenta.
- **Sem logging de comunicação**: Impossível auditar o que foi enviado ao PrestaShop ou diagnosticar falhas de sincronização.
- **Inconsistências temporárias**: Enquanto o catálogo está a ser processado em múltiplas rondas, podem existir dados desactualizados na loja.

Apesar de incluir funcionalidades completas (encomendas, pagamentos, tickets), estas limitações de performance tornam o sistema inadequado para as necessidades actuais de sincronização.

## Vantagens do Genesys

O Genesys resolve directamente os bottlenecks do Patife:

- **10.000 produtos em 1-3 minutos** vs múltiplas rondas no Patife
- **Workers dinâmicos** que escalam com a carga
- **Sistema de prioridades** para updates críticos (stock zero, mudança de preço)
- **Consumer inteligente** que adapta workload à hora do dia
- **Logging completo** e auditável
- **Arquitectura preparada** para AI, MCP, Kafka e microservices

## Considerações para Decisão

1. **Para gestão de catálogo e sincronização**: O Genesys é a escolha adequada. A performance e resiliência são significativamente superiores.

2. **Para encomendas e pagamentos**: Desenvolvimento adicional necessário no Genesys antes de substituir completamente o Patife.

3. **Estratégia de transição**: Usar o Genesys para catálogo/preços enquanto mantém-se o Patife apenas para operações de encomendas até estas serem migradas.

## Próximos Passos

1. Completar funcionalidades de catálogo no Genesys
2. Desenvolver módulo de Encomendas no Genesys
3. Desenvolver módulo de Pagamentos no Genesys
4. Migração gradual com período de coexistência
