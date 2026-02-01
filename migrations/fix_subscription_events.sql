-- Fix subscription_events table to handle the existing structure
-- Insert initial subscription event for existing users with proper structure

INSERT INTO subscription_events (user_id, event_type, event_data, processed)
SELECT 
    id,
    'migration_completed',
    jsonb_build_object(
        'old_subscription_status', COALESCE(subscription_status, 'inactive'),
        'migrated_at', NOW()
    ),
    true
FROM users
WHERE id NOT IN (
    SELECT user_id 
    FROM subscription_events 
    WHERE event_type = 'migration_completed'
);

-- Update existing users to have the default free tier
UPDATE users SET subscription_tier = 'free' WHERE subscription_tier IS NULL;













