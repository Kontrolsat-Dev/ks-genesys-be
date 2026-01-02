-- Migration: Add product tax fields (ecotax, extra_fees)
-- Date: 2026-01-02
-- Description: Adds ecotax and extra_fees to products table,
--              and default_ecotax and default_extra_fees to categories table

-- ============================================
-- PRODUCTS TABLE
-- ============================================

-- Add ecotax column (sent separately to PrestaShop)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS ecotax NUMERIC(10, 4) NOT NULL DEFAULT 0;

-- Add extra_fees column (DAF, copyright, etc. - added to product price)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS extra_fees NUMERIC(10, 4) NOT NULL DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN products.ecotax IS 'Ecotax value in EUR - sent as separate field to PrestaShop';
COMMENT ON COLUMN products.extra_fees IS 'Additional fees (DAF, copyright, etc.) in EUR - added to base price before margin';

-- ============================================
-- CATEGORIES TABLE
-- ============================================

-- Add default_ecotax column (inherited by products during import)
ALTER TABLE categories
ADD COLUMN IF NOT EXISTS default_ecotax NUMERIC(10, 4) NOT NULL DEFAULT 0;

-- Add default_extra_fees column (inherited by products during import)
ALTER TABLE categories
ADD COLUMN IF NOT EXISTS default_extra_fees NUMERIC(10, 4) NOT NULL DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN categories.default_ecotax IS 'Default ecotax for products in this category';
COMMENT ON COLUMN categories.default_extra_fees IS 'Default extra fees for products in this category';

-- ============================================
-- VERIFICATION QUERY
-- ============================================

-- Run this to verify the migration:
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name IN ('products', 'categories')
--   AND column_name IN ('ecotax', 'extra_fees', 'default_ecotax', 'default_extra_fees');
