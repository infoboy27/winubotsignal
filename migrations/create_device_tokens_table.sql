-- Create device_tokens table for push notifications
-- This table stores device tokens for mobile app push notifications

CREATE TABLE IF NOT EXISTS device_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL,
    platform VARCHAR(10) NOT NULL CHECK (platform IN ('ios', 'android')),
    device_id VARCHAR(255),
    app_version VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, device_token)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON device_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_device_tokens_platform ON device_tokens(platform);
CREATE INDEX IF NOT EXISTS idx_device_tokens_active ON device_tokens(is_active) WHERE is_active = TRUE;

-- Add comment
COMMENT ON TABLE device_tokens IS 'Stores device tokens for mobile app push notifications';
COMMENT ON COLUMN device_tokens.device_token IS 'Push notification token from FCM (Android) or APNS (iOS)';
COMMENT ON COLUMN device_tokens.platform IS 'Platform: ios or android';
COMMENT ON COLUMN device_tokens.device_id IS 'Unique device identifier (optional)';
COMMENT ON COLUMN device_tokens.app_version IS 'App version for debugging';
