-- Migration: Add discount field to suppliers table
-- Run this manually against the PostgreSQL database

-- Add discount column (percentual, e.g., 0.10 = 10%)
-- Applied to offer cost: custo_final = custo × (1 - discount)
ALTER TABLE suppliers
    ADD COLUMN IF NOT EXISTS discount NUMERIC(5, 4) NOT NULL DEFAULT 0;

-- Add comment for documentation
COMMENT ON COLUMN suppliers.discount IS 'Desconto percentual do fornecedor aplicado às ofertas (0.10 = 10%)';
