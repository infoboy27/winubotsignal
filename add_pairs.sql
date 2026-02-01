-- Add NEAR/USDT, SUI/USDT, and TRX/USDT to the assets table
-- This script ensures the pairs are active in the database

-- NEAR/USDT
INSERT INTO assets (symbol, name, base, quote, exchange, active, created_at, updated_at)
VALUES ('NEAR/USDT', 'NEAR Protocol', 'NEAR', 'USDT', 'binance', true, NOW(), NOW())
ON CONFLICT (symbol) DO UPDATE 
SET active = true, name = 'NEAR Protocol', updated_at = NOW();

-- SUI/USDT
INSERT INTO assets (symbol, name, base, quote, exchange, active, created_at, updated_at)
VALUES ('SUI/USDT', 'Sui', 'SUI', 'USDT', 'binance', true, NOW(), NOW())
ON CONFLICT (symbol) DO UPDATE 
SET active = true, name = 'Sui', updated_at = NOW();

-- TRX/USDT
INSERT INTO assets (symbol, name, base, quote, exchange, active, created_at, updated_at)
VALUES ('TRX/USDT', 'TRON', 'TRX', 'USDT', 'binance', true, NOW(), NOW())
ON CONFLICT (symbol) DO UPDATE 
SET active = true, name = 'TRON', updated_at = NOW();

-- Verify the pairs were added/updated
SELECT symbol, name, active, exchange FROM assets 
WHERE symbol IN ('NEAR/USDT', 'SUI/USDT', 'TRX/USDT')
ORDER BY symbol;
