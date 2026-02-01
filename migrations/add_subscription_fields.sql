-- Migration to add subscription fields to users table
-- Run this migration to add subscription support

-- Add subscription fields to users table
ALTER TABLE users 
ADD COLUMN subscription_status VARCHAR(50) DEFAULT 'inactive' NOT NULL,
ADD COLUMN current_period_end TIMESTAMP,
ADD COLUMN plan_id VARCHAR(100),
ADD COLUMN stripe_customer_id VARCHAR(255) UNIQUE,
ADD COLUMN stripe_subscription_id VARCHAR(255) UNIQUE,
ADD COLUMN telegram_user_id VARCHAR(100),
ADD COLUMN subscription_created_at TIMESTAMP,
ADD COLUMN subscription_updated_at TIMESTAMP;

-- Create index on stripe_customer_id for faster lookups
CREATE INDEX idx_users_stripe_customer_id ON users(stripe_customer_id);

-- Create index on stripe_subscription_id for faster lookups
CREATE INDEX idx_users_stripe_subscription_id ON users(stripe_subscription_id);

-- Create subscription_events table for auditing
CREATE TABLE subscription_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    stripe_event_id VARCHAR(255) UNIQUE NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create indexes for subscription_events
CREATE INDEX idx_subscription_events_user_id ON subscription_events(user_id);
CREATE INDEX idx_subscription_events_stripe_event_id ON subscription_events(stripe_event_id);
CREATE INDEX idx_subscription_events_created_at ON subscription_events(created_at);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_subscription_events_updated_at 
    BEFORE UPDATE ON subscription_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update existing users to have proper subscription status
UPDATE users 
SET subscription_status = 'active' 
WHERE is_admin = true;

-- Add some sample subscription plans (these would be created in Stripe)
-- This is just for reference - actual plans should be created in Stripe dashboard
INSERT INTO subscription_events (user_id, event_type, stripe_event_id, event_data, processed)
SELECT 
    u.id,
    'subscription.created',
    'evt_sample_' || u.id,
    '{"object": {"id": "sub_sample_' || u.id || '", "status": "active", "customer": "cus_sample_' || u.id || '"}}'::jsonb,
    true
FROM users u 
WHERE u.is_admin = true
ON CONFLICT (stripe_event_id) DO NOTHING;

-- Create a view for subscription analytics
CREATE VIEW subscription_analytics AS
SELECT 
    subscription_status,
    COUNT(*) as user_count,
    AVG(EXTRACT(EPOCH FROM (subscription_updated_at - subscription_created_at))/86400) as avg_duration_days
FROM users 
WHERE subscription_status != 'inactive'
GROUP BY subscription_status;

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE ON subscription_events TO your_app_user;
-- GRANT SELECT ON subscription_analytics TO your_app_user;
