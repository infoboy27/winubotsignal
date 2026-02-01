-- New Subscription System Migration
-- This migration adds support for the new 3-tier subscription system:
-- 1. Free Trial (7 days, 1 dashboard access)
-- 2. Professional ($14.99/month via Binance Pay)
-- 3. VIP Elite ($29.99/month via Binance Pay)

-- Add new columns to users table for trial and subscription management
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_start_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_used BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_dashboard_access_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free'; -- free, professional, vip_elite
ALTER TABLE users ADD COLUMN IF NOT EXISTS binance_pay_merchant_id VARCHAR(50) DEFAULT '287402909';
ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_due_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS access_revoked_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_renewal_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_payment_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) DEFAULT 'binance_pay'; -- binance_pay, stripe, etc.

-- Create subscription_events table for detailed billing tracking
CREATE TABLE IF NOT EXISTS subscription_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- trial_started, payment_due, payment_overdue, access_revoked, payment_success, etc.
    event_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_subscription_tier ON users(subscription_tier);
CREATE INDEX IF NOT EXISTS idx_users_trial_start_date ON users(trial_start_date);
CREATE INDEX IF NOT EXISTS idx_users_payment_due_date ON users(payment_due_date);
CREATE INDEX IF NOT EXISTS idx_users_access_revoked_at ON users(access_revoked_at);
CREATE INDEX IF NOT EXISTS idx_subscription_events_user_id ON subscription_events(user_id);
CREATE INDEX IF NOT EXISTS idx_subscription_events_event_type ON subscription_events(event_type);
CREATE INDEX IF NOT EXISTS idx_subscription_events_created_at ON subscription_events(created_at);

-- Create subscription_plans table to store plan configurations
CREATE TABLE IF NOT EXISTS subscription_plans (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price_usd DECIMAL(10,2) NOT NULL,
    price_usdt DECIMAL(10,2) NOT NULL,
    interval VARCHAR(20) NOT NULL, -- monthly, yearly
    duration_days INTEGER,
    dashboard_access_limit INTEGER,
    features JSONB NOT NULL,
    telegram_access BOOLEAN DEFAULT FALSE,
    support_level VARCHAR(20) DEFAULT 'none', -- none, priority, 24/7
    binance_pay_id VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert the new subscription plans
INSERT INTO subscription_plans (id, name, price_usd, price_usdt, interval, duration_days, dashboard_access_limit, features, telegram_access, support_level, binance_pay_id) VALUES
(
    'free_trial',
    'Free Trial',
    0.00,
    0.00,
    'trial',
    7,
    1,
    '["1-time dashboard access", "Basic signal preview", "Limited features"]',
    FALSE,
    'none',
    NULL
),
(
    'professional',
    'Professional',
    14.99,
    14.99,
    'monthly',
    30,
    -1, -- unlimited access
    '["Dashboard access", "Telegram group access", "Priority support", "Real-time signals", "Email alerts"]',
    TRUE,
    'priority',
    '287402909'
),
(
    'vip_elite',
    'VIP Elite',
    29.99,
    29.99,
    'monthly',
    30,
    -1, -- unlimited access
    '["All Professional features", "24/7 priority support", "Early access to new features", "Access to trading bot", "Custom alerts", "Access to airdrops", "Advanced analytics"]',
    TRUE,
    '24/7',
    '287402909'
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    price_usd = EXCLUDED.price_usd,
    price_usdt = EXCLUDED.price_usdt,
    interval = EXCLUDED.interval,
    duration_days = EXCLUDED.duration_days,
    dashboard_access_limit = EXCLUDED.dashboard_access_limit,
    features = EXCLUDED.features,
    telegram_access = EXCLUDED.telegram_access,
    support_level = EXCLUDED.support_level,
    binance_pay_id = EXCLUDED.binance_pay_id,
    updated_at = NOW();

-- Create payment_transactions table for tracking payments
CREATE TABLE IF NOT EXISTS payment_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL REFERENCES subscription_plans(id),
    amount_usd DECIMAL(10,2) NOT NULL,
    amount_usdt DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL, -- binance_pay, stripe, etc.
    transaction_id VARCHAR(255) UNIQUE, -- External transaction ID
    status VARCHAR(20) NOT NULL, -- pending, completed, failed, refunded
    payment_data JSONB, -- Store payment provider specific data
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for payment_transactions
CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_created_at ON payment_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_transaction_id ON payment_transactions(transaction_id);

-- Create telegram_group_access table for managing Telegram group memberships
CREATE TABLE IF NOT EXISTS telegram_group_access (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_user_id VARCHAR(100),
    telegram_username VARCHAR(100),
    group_name VARCHAR(100) NOT NULL, -- professional_group, vip_group
    access_granted_at TIMESTAMP DEFAULT NOW(),
    access_revoked_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for telegram_group_access
CREATE INDEX IF NOT EXISTS idx_telegram_group_access_user_id ON telegram_group_access(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_group_access_telegram_user_id ON telegram_group_access(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_group_access_is_active ON telegram_group_access(is_active);

-- Add comments for documentation
COMMENT ON COLUMN users.trial_start_date IS 'When the user started their free trial';
COMMENT ON COLUMN users.trial_used IS 'Whether the user has used their free trial';
COMMENT ON COLUMN users.trial_dashboard_access_count IS 'Number of times user accessed dashboard during trial (limit: 1)';
COMMENT ON COLUMN users.subscription_tier IS 'Current subscription tier: free, professional, vip_elite';
COMMENT ON COLUMN users.payment_due_date IS 'Next payment due date for active subscribers';
COMMENT ON COLUMN users.access_revoked_at IS 'When access was revoked due to overdue payment';

COMMENT ON TABLE subscription_events IS 'Tracks all subscription-related events for audit and billing';
COMMENT ON TABLE subscription_plans IS 'Defines available subscription plans and their features';
COMMENT ON TABLE payment_transactions IS 'Records all payment transactions';
COMMENT ON TABLE telegram_group_access IS 'Manages Telegram group memberships based on subscription';

-- Update existing users to have the default free tier
UPDATE users SET subscription_tier = 'free' WHERE subscription_tier IS NULL;

-- Create a function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_subscription_events_updated_at BEFORE UPDATE ON subscription_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscription_plans_updated_at BEFORE UPDATE ON subscription_plans FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payment_transactions_updated_at BEFORE UPDATE ON payment_transactions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_telegram_group_access_updated_at BEFORE UPDATE ON telegram_group_access FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial subscription event for existing users
INSERT INTO subscription_events (user_id, event_type, event_data)
SELECT 
    id,
    'migration_completed',
    jsonb_build_object(
        'old_subscription_status', COALESCE(subscription_status, 'inactive'),
        'migrated_at', NOW()
    )
FROM users
WHERE id NOT IN (SELECT user_id FROM subscription_events WHERE event_type = 'migration_completed');

COMMIT;













