# Genesys Stock Manager - Guia do Merchant

Bem-vindo ao **Genesys Stock Manager** - a plataforma de gestão de catálogo e sincronização com PrestaShop.

---

## 📦 Catálogo de Produtos

### Listagem de Produtos
- **Pesquisa avançada**: Pesquise por nome, GTIN, MPN ou descrição
- **Filtros combinados**:
  - Por marca
  - Por categoria
  - Por fornecedor
  - Com/sem stock
  - Importados/não importados
- **Ordenação**: Por data, nome ou preço mais baixo
- **Facets dinâmicos**: Os filtros mostram apenas opções relevantes

### Página de Produto
Visualize informação detalhada:
- Dados básicos (nome, descrição, imagens)
- GTIN, MPN, marca e categoria
- **Ofertas de fornecedores**: Todas as ofertas disponíveis com preço e stock
- **Best Offer**: A oferta mais barata
- **Gráficos de histórico**: Evolução de preços e stock ao longo do tempo
- **Metadados**: Informação adicional do produto

---

## 🏷️ Gestão de Categorias

### Listagem de Categorias
- Visualize todas as categorias do catálogo
- **Filtro por Auto-Import**: Ver apenas categorias com importação automática ativa
- Veja qual **fornecedor** criou cada categoria

### Mapeamento PrestaShop
Associe categorias do catálogo às categorias da sua loja:
1. Clique na categoria
2. Seleccione a categoria PrestaShop correspondente na árvore
3. Active o **Auto-Import** se quiser importação automática de novos produtos

---

## 🏢 Gestão de Marcas

- Listagem completa de marcas
- Pesquisa e filtragem
- Estatísticas por marca

---

## 📤 Importação para PrestaShop

### Importar Produto Individual
Na página do produto, clique **"Importar"**:

1. **Categoria já mapeada**: Importação directa
2. **Categoria não mapeada**:
   - Seleccione a categoria PrestaShop
   - (Opcional) Active Auto-Import para futuros produtos
   - O mapeamento fica guardado

### Dados Enviados
- Nome e descrição
- Categoria PrestaShop
- **Preço de venda** = Melhor preço × (1 + margem)
- Stock actual
- GTIN, MPN
- Imagem
- Peso

### Auto-Import
Quando uma categoria tem Auto-Import activo:
- Novos produtos dessa categoria são automaticamente importados
- Útil para categorias de alta rotação

---

## 💰 Preços e Margens

### Best Offer
O sistema selecciona automaticamente a **oferta mais barata** de todos os fornecedores.

### Margem do Produto
Cada produto tem uma margem configurável:
```
Preço de Venda = Custo (Best Offer) × (1 + Margem)
```

Exemplo: Custo €50, Margem 20% → Venda €60

### Movimentos de Preço
Acompanhe alterações de preço:
- **Catálogo**: Produtos não importados com alterações
- **Oferta Activa**: Produtos na loja com variações de preço
- Filtre por subidas, descidas ou ambos
- Defina thresholds mínimos (€ ou %)

---

## 🚛 Fornecedores

### Listagem de Fornecedores
- Nome, logo e contactos
- Número de feeds activos
- Data da última sincronização

### Feeds de Fornecedor
Cada fornecedor pode ter múltiplos feeds:
- XML, CSV, JSON
- Configurações de mapeamento de campos
- Histórico de ingestões

---

## ⚙️ Worker Jobs

### Sincronização Automática
O sistema executa periodicamente:
- **Ingestão de feeds**: Actualiza produtos e preços
- **Recálculo de best offer**: Determina a melhor oferta
- **Sincronização PrestaShop**: Actualiza preços/stock na loja

### Monitorização
Acompanhe o estado dos jobs:
- Pendentes, em execução, concluídos
- Logs de erros
- Estatísticas de processamento

---

## 🔐 Autenticação

### Login
Acesso via credenciais PrestaShop:
- Email e password
- Validação no módulo r_genesys da loja

### Sessão
- Tokens JWT com refresh automático
- Sessão persistente

---

## 📊 Dashboard

Visão geral do sistema:
- Total de produtos no catálogo
- Produtos importados vs não importados
- Fornecedores activos
- Últimas alterações de preço

---

## 🆘 Suporte

Para questões ou problemas:
- Consulte a documentação técnica
- Contacte a equipa de suporte

---

*Genesys Stock Manager v2.0*
