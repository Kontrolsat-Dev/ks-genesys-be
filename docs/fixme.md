# FIXME - Refinação do Cálculo de Preços

## 1. Extra Fees vs Fornecedores PT

Atualmente, no usecase `import_to_prestashop.py`, as `extra_fees` são zeradas se o fornecedor for de Portugal (PT).
**Correção necessária:** Apenas a `ecotax` deve ser sensível ao país. As `extra_fees` (taxas administrativas, etc.) devem ser aplicadas independentemente da origem do produto.

## 2. Unificação da Fórmula de Venda

Existe uma discrepância entre o botão "Import" (Manual/Bulk) e o Worker de Background.

- **Import Manual:** Aplica `Custo + Margem + Ecotax + Extra Fees + Rounding`.
- **Worker (active_offer.py):** Aplica apenas `Custo + Margem + Rounding`.

**Objetivo:** Centralizar o cálculo num `PriceService` e garantir que o Worker de background use a mesma fórmula completa que o processo manual usa, mantendo a consistência dos preços na loja.

## 3. Manter Raw Price no Sync

Confirmado que o Ingest (sync com fornecedor) deve manter sempre o preço bruto original na tabela `SupplierItem`. O cálculo de taxas só ocorre no momento de determinar o preço de venda para o PrestaShop.
