-- Initialize TimescaleDB and create hypertables for Million Trader

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create the main database tables will be created by SQLAlchemy
-- This script sets up TimescaleDB-specific configurations

-- Function to create hypertables after tables are created
CREATE OR REPLACE FUNCTION setup_hypertables() RETURNS void AS $$
BEGIN
    -- Create hypertable for OHLCV data
    -- This will be called after SQLAlchemy creates the tables
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ohlcv') THEN
        PERFORM create_hypertable('ohlcv', 'timestamp', if_not_exists => TRUE);
        
        -- Create indexes for better query performance
        CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_timestamp 
        ON ohlcv (symbol, timeframe, timestamp DESC);
        
        -- Set compression policy (compress data older than 7 days)
        SELECT add_compression_policy('ohlcv', INTERVAL '7 days', if_not_exists => TRUE);
        
        -- Set retention policy (keep data for 2 years)
        SELECT add_retention_policy('ohlcv', INTERVAL '2 years', if_not_exists => TRUE);
    END IF;
    
    -- Create hypertable for market data cache
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'market_data_cache') THEN
        PERFORM create_hypertable('market_data_cache', 'timestamp', if_not_exists => TRUE);
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_market_data_symbol_type_timestamp 
        ON market_data_cache (symbol, data_type, timestamp DESC);
        
        -- Set retention policy (keep cache data for 30 days)
        SELECT add_retention_policy('market_data_cache', INTERVAL '30 days', if_not_exists => TRUE);
    END IF;
    
    -- Create hypertable for system metrics
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'system_metrics') THEN
        PERFORM create_hypertable('system_metrics', 'timestamp', if_not_exists => TRUE);
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_system_metrics_name_timestamp 
        ON system_metrics (metric_name, timestamp DESC);
        
        -- Set retention policy (keep metrics for 90 days)
        SELECT add_retention_policy('system_metrics', INTERVAL '90 days', if_not_exists => TRUE);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create materialized views for common queries
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_signal_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_signals,
    COUNT(*) FILTER (WHERE direction = 'LONG') as long_signals,
    COUNT(*) FILTER (WHERE direction = 'SHORT') as short_signals,
    AVG(score) as avg_score,
    COUNT(*) FILTER (WHERE score >= 0.8) as high_confidence_signals
FROM signals 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Create index on the materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_signal_stats_date ON daily_signal_stats (date);

-- Create a function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_signal_stats;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get asset performance metrics
CREATE OR REPLACE FUNCTION get_asset_performance(
    asset_symbol TEXT,
    days_back INTEGER DEFAULT 30
) RETURNS TABLE(
    symbol TEXT,
    total_signals INTEGER,
    avg_score NUMERIC,
    price_change_percent NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.symbol::TEXT,
        COUNT(*)::INTEGER as total_signals,
        AVG(s.score)::NUMERIC as avg_score,
        CASE 
            WHEN first_price.close > 0 THEN 
                ((last_price.close - first_price.close) / first_price.close * 100)::NUMERIC
            ELSE 0::NUMERIC
        END as price_change_percent
    FROM signals s
    LEFT JOIN (
        SELECT DISTINCT ON (symbol) symbol, close
        FROM ohlcv 
        WHERE symbol = asset_symbol 
        AND timeframe = '1d'
        AND timestamp >= CURRENT_DATE - INTERVAL '1 day' * days_back
        ORDER BY symbol, timestamp ASC
    ) first_price ON first_price.symbol = s.symbol
    LEFT JOIN (
        SELECT DISTINCT ON (symbol) symbol, close
        FROM ohlcv 
        WHERE symbol = asset_symbol 
        AND timeframe = '1d'
        AND timestamp >= CURRENT_DATE - INTERVAL '1 day'
        ORDER BY symbol, timestamp DESC
    ) last_price ON last_price.symbol = s.symbol
    WHERE s.symbol = asset_symbol
    AND s.created_at >= CURRENT_DATE - INTERVAL '1 day' * days_back
    GROUP BY s.symbol, first_price.close, last_price.close;
END;
$$ LANGUAGE plpgsql;

-- Create notification function for new signals
CREATE OR REPLACE FUNCTION notify_new_signal() RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('new_signal', json_build_object(
        'id', NEW.id,
        'symbol', NEW.symbol,
        'direction', NEW.direction,
        'score', NEW.score,
        'timeframe', NEW.timeframe
    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for signal notifications (will be created after table exists)
-- This will be handled by the application initialization

-- Grant permissions
GRANT USAGE ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;


