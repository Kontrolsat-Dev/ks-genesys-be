-- Adicionar coluna para tracking de quando auto_import foi ativado
ALTER TABLE categories
ADD COLUMN auto_import_since TIMESTAMP NULL;

-- Criar índice para otimizar a query de auto-import
CREATE INDEX ix_categories_auto_import_since
ON categories (auto_import_since)
WHERE auto_import = true AND auto_import_since IS NOT NULL;
