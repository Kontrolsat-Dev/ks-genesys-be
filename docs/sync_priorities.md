# Prioridades de Sincronização - CatalogUpdateStream

Tabela de prioridades para eventos de sincronização com PrestaShop.

## Níveis de Prioridade

| Prioridade | Evento | Descrição |
|:----------:|--------|-----------|
| **10** | 🔴 Saída de Stock | Produto ficou sem stock (era >0, agora é 0) |
| **9** | 🟢 Reentrada de Stock | Produto voltou a ter stock (era ≤0, agora é >0) |
| **8** | 💰 Alteração de Preço | Preço/margem mudou, stock sem transição crítica |
| **5** | ⚪ Default | Outras alterações |

> **NOTA:** Valores menores = maior prioridade no processamento da queue.

## Implementação

Ficheiro: `app/domains/catalog/services/sync_events.py`

```python
# Prioridades (maior = mais urgente):
# 10 = saída de stock (produto ficou sem stock)
# 9 = reentrada de stock (produto voltou a ter stock)
# 8 = alteração de preço (com stock inalterado)
# 5 = default (outras alterações)

if old_stock_i > 0 and new_stock_i == 0:
    priority = 10  # ficou sem stock
elif old_stock_i <= 0 and new_stock_i > 0:
    priority = 9   # voltou a ter stock
elif old_price != new_price:
    priority = 8   # preço alterou
```

## Justificação

- **Stock-out (10)**: Urgentíssimo pois significa que o produto não deve ser vendido
- **Stock-in (9)**: Importante para reativar vendas de produtos que voltaram ao stock
- **Preço (8)**: Importante mas não crítico para operação
- **Default (5)**: Alterações menores sem impacto imediato nas vendas
