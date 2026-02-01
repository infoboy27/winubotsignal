-- Trading History Tables
-- Stores trading data fetched from Binance API

-- Trading trades table
CREATE TABLE IF NOT EXISTS trading_trades (
    id SERIAL PRIMARY KEY,
    binance_trade_id VARCHAR(50) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
    amount DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    cost DECIMAL(20, 8),
    fee DECIMAL(20, 8),
    fee_currency VARCHAR(10),
    pnl DECIMAL(20, 8), -- Calculated PNL for closed trades
    trade_type VARCHAR(20) NOT NULL, -- 'spot' or 'futures'
    timestamp BIGINT NOT NULL, -- Binance timestamp
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Daily PNL summary table
CREATE TABLE IF NOT EXISTS daily_pnl_summary (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_pnl DECIMAL(20, 8) DEFAULT 0,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    total_volume DECIMAL(20, 8) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Account balance history table
CREATE TABLE IF NOT EXISTS account_balance_history (
    id SERIAL PRIMARY KEY,
    account_type VARCHAR(20) NOT NULL, -- 'spot' or 'futures'
    currency VARCHAR(10) NOT NULL,
    total_balance DECIMAL(20, 8) NOT NULL,
    free_balance DECIMAL(20, 8) NOT NULL,
    used_balance DECIMAL(20, 8) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Trading statistics table
CREATE TABLE IF NOT EXISTS trading_statistics (
    id SERIAL PRIMARY KEY,
    period_type VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly'
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_pnl DECIMAL(20, 8) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    avg_win DECIMAL(20, 8) DEFAULT 0,
    avg_loss DECIMAL(20, 8) DEFAULT 0,
    profit_factor DECIMAL(10, 4) DEFAULT 0,
    max_drawdown DECIMAL(10, 4) DEFAULT 0,
    sharpe_ratio DECIMAL(10, 4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(period_type, period_start, period_end)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_trading_trades_symbol ON trading_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_trades_timestamp ON trading_trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trading_trades_side ON trading_trades(side);
CREATE INDEX IF NOT EXISTS idx_trading_trades_type ON trading_trades(trade_type);
CREATE INDEX IF NOT EXISTS idx_trading_trades_created_at ON trading_trades(created_at);

CREATE INDEX IF NOT EXISTS idx_daily_pnl_date ON daily_pnl_summary(date);
CREATE INDEX IF NOT EXISTS idx_account_balance_timestamp ON account_balance_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_account_balance_type ON account_balance_history(account_type);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_trading_trades_updated_at BEFORE UPDATE ON trading_trades FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_daily_pnl_summary_updated_at BEFORE UPDATE ON daily_pnl_summary FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_trading_statistics_updated_at BEFORE UPDATE ON trading_statistics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();












