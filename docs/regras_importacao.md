# Regras de importação/atualização de produtos

## Regras de atualização

### Cenario 1

Produto X

1. Fornecedor A: 10 unidades, 5€
2. Fornecedor B: 5 unidades, 6€

> Vencedor: Fornecedor A - Menor preço com Stock

### Cenario 2

Produto X

1. Fornecedor A: 1 unidades, 5€
2. Fornecedor B: 5 unidades, 6€

> Vencedor: Fornecedor A - Menor preço com Stock

### Cenario 3

Produto X

1. Fornecedor A: 0 unidades, 5€
2. Fornecedor B: 5 unidades, 6€

> Vencedor: Fornecedor B - Menor preço com Stock - Temos stock

### Cenario 4

Produto X

1. Fornecedor A: 0 unidades, 5€
2. Fornecedor B: 0 unidades, 2€

> Vencedor: Fornecedor B - Menor preço sem stock - SEO

## Cenario 5

1. Sem ofertas

> Comunicamos o ultimo preco em registo com 0 unidades em stock

## Regras de importação

### Cenario 1

1. Fornecedor A: 0 unidades, 5€
2. Fornecedor B: 5 unidades, 6€

> Vencedor: Fornecedor B - Menor preço com Stock

### Cenario 2

1. Fornecedor A: 0 unidades, 5€

> Vencedor: Fornecedor A - Unico fornecedor

# Como devem ser tratados os preços

1. Preco de custo de fornecedor
2. Margem de venda
3. Desconto de fornecedor
4. Taxas de produto - Apenas aplicadas se fornecedor != Portugal (PT)
   4.1 - Se nao existir taxas de produto, existe taxas de categoria
5. Aplicar arredondamentos ao valor com IVA
   5.1. - Preços tem de terminar 0.40 ou 0.90
   5.2. - Produtos com menos de 5€ arrendondar para cima:
   5.2.1. - 2.41€ > 2.90€
   5.2.2. - 2.49€ > 2.90€
   5.2.3. - 12.45€ > 12.40€
