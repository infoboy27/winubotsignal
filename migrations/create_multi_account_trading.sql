-- Multi-Account Trading System - Database Schema
-- Run this migration to create the necessary tables

-- Table 1: User API Keys (Encrypted storage for Binance API credentials)
CREATE TABLE IF NOT EXISTS user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- API Key Info
    exchange VARCHAR(50) NOT NULL DEFAULT 'binance',
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    api_name VARCHAR(100) NOT NULL,  -- User-friendly name (e.g., "Main Trading Account")
    
    -- Account Type
    account_type VARCHAR(20) NOT NULL DEFAULT 'futures',  -- spot, futures, both
    test_mode BOOLEAN DEFAULT FALSE,  -- Testnet or live
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_verified_at TIMESTAMP,
    verification_error TEXT,
    
    -- Trading Settings (per account)
    auto_trade_enabled BOOLEAN DEFAULT FALSE,
    max_position_size_usd DECIMAL(12,2) DEFAULT 1000.00,
    max_daily_trades INTEGER DEFAULT 5,
    leverage DECIMAL(5,2) DEFAULT 10.0,
    
    -- Risk Management (per account)
    max_risk_per_trade DECIMAL(5,4) DEFAULT 0.02,  -- 2%
    max_daily_loss DECIMAL(5,4) DEFAULT 0.05,      -- 5%
    stop_trading_on_loss BOOLEAN DEFAULT TRUE,
    
    -- Position Sizing Strategy
    position_sizing_mode VARCHAR(20) DEFAULT 'fixed',  -- fixed, percentage, kelly
    position_size_value DECIMAL(12,2) DEFAULT 100.00,  -- USD or percentage
    
    -- Monitoring
    last_order_at TIMESTAMP,
    total_orders INTEGER DEFAULT 0,
    successful_orders INTEGER DEFAULT 0,
    failed_orders INTEGER DEFAULT 0,
    total_pnl DECIMAL(12,2) DEFAULT 0.00,
    current_balance DECIMAL(12,2),
    last_balance_update TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_user_api_name UNIQUE(user_id, api_name)
);

-- Indexes for user_api_keys
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_active ON user_api_keys(is_active, auto_trade_enabled);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_exchange ON user_api_keys(exchange, account_type);

-- Table 2: Multi-Account Orders (Track orders across all accounts)
CREATE TABLE IF NOT EXISTS multi_account_orders (
    id SERIAL PRIMARY KEY,
    
    -- Signal Reference
    signal_id INTEGER REFERENCES signals(id),
    signal_data JSONB,  -- Snapshot of signal data
    
    -- Order Group (same signal, multiple accounts)
    order_group_id UUID NOT NULL,
    
    -- Account Reference
    user_id INTEGER NOT NULL REFERENCES users(id),
    api_key_id INTEGER NOT NULL REFERENCES user_api_keys(id) ON DELETE CASCADE,
    account_name VARCHAR(100),
    
    -- Order Details
    exchange VARCHAR(50) DEFAULT 'binance',
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY, SELL
    order_type VARCHAR(20) NOT NULL DEFAULT 'MARKET',
    quantity DECIMAL(18,8) NOT NULL,
    price DECIMAL(18,8),
    
    -- Execution
    exchange_order_id VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, submitted, filled, cancelled, failed
    filled_quantity DECIMAL(18,8),
    average_price DECIMAL(18,8),
    
    -- Risk Management
    stop_loss DECIMAL(18,8),
    take_profit DECIMAL(18,8),
    leverage DECIMAL(5,2),
    position_size_usd DECIMAL(12,2),
    
    -- Results
    pnl DECIMAL(12,2),
    pnl_percentage DECIMAL(8,4),
    fees DECIMAL(12,6),
    
    -- Error Handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    filled_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for multi_account_orders
CREATE INDEX IF NOT EXISTS idx_multi_account_orders_group ON multi_account_orders(order_group_id);
CREATE INDEX IF NOT EXISTS idx_multi_account_orders_user ON multi_account_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_multi_account_orders_api_key ON multi_account_orders(api_key_id);
CREATE INDEX IF NOT EXISTS idx_multi_account_orders_status ON multi_account_orders(status);
CREATE INDEX IF NOT EXISTS idx_multi_account_orders_created ON multi_account_orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_multi_account_orders_signal ON multi_account_orders(signal_id);

-- Table 3: Account Daily Stats (Track daily performance per account)
CREATE TABLE IF NOT EXISTS account_daily_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    api_key_id INTEGER NOT NULL REFERENCES user_api_keys(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Trading Activity
    total_trades INTEGER DEFAULT 0,
    successful_trades INTEGER DEFAULT 0,
    failed_trades INTEGER DEFAULT 0,
    
    -- Performance
    daily_pnl DECIMAL(12,2) DEFAULT 0.00,
    daily_pnl_percentage DECIMAL(8,4) DEFAULT 0.0000,
    starting_balance DECIMAL(12,2),
    ending_balance DECIMAL(12,2),
    
    -- Risk Metrics
    max_drawdown DECIMAL(8,4),
    largest_loss DECIMAL(12,2),
    largest_win DECIMAL(12,2),
    
    -- Status
    stop_trading_triggered BOOLEAN DEFAULT FALSE,
    daily_loss_limit_hit BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_account_daily_stat UNIQUE(api_key_id, date)
);

-- Index for account_daily_stats
CREATE INDEX IF NOT EXISTS idx_account_daily_stats_api_key_date ON account_daily_stats(api_key_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_account_daily_stats_user ON account_daily_stats(user_id, date DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_api_keys_updated_at
BEFORE UPDATE ON user_api_keys
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_multi_account_orders_updated_at
BEFORE UPDATE ON multi_account_orders
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_account_daily_stats_updated_at
BEFORE UPDATE ON account_daily_stats
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE user_api_keys IS 'Stores encrypted Binance API keys for multi-account trading';
COMMENT ON TABLE multi_account_orders IS 'Tracks all orders executed across multiple accounts';
COMMENT ON TABLE account_daily_stats IS 'Daily performance statistics per trading account';
COMMENT ON COLUMN user_api_keys.api_key_encrypted IS 'Fernet-encrypted Binance API key';
COMMENT ON COLUMN user_api_keys.api_secret_encrypted IS 'Fernet-encrypted Binance API secret';
COMMENT ON COLUMN multi_account_orders.order_group_id IS 'UUID grouping orders from the same signal across accounts';



