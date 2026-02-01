-- Webhook Logging Table for Payment Monitoring
-- Run this migration to create the webhook_logs table

CREATE TABLE IF NOT EXISTS webhook_logs (
    id SERIAL PRIMARY KEY,
    payment_method VARCHAR(50) NOT NULL,
    webhook_type VARCHAR(50),  -- coinbase_commerce, nowpayments, stripe, binance_pay
    webhook_data JSONB NOT NULL,
    headers JSONB,
    signature VARCHAR(500),
    signature_valid BOOLEAN DEFAULT NULL,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'received',  -- received, processing, completed, failed
    error_message TEXT,
    user_id INTEGER,
    payment_id VARCHAR(255),
    plan_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for faster querying
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_payment_method ON webhook_logs(payment_method);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_processing_status ON webhook_logs(processing_status);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_user_id ON webhook_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_payment_id ON webhook_logs(payment_id);

-- Add a trigger to automatically update processed_at when status changes to completed/failed
CREATE OR REPLACE FUNCTION update_webhook_processed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.processing_status IN ('completed', 'failed') AND OLD.processing_status NOT IN ('completed', 'failed') THEN
        NEW.processed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER webhook_logs_update_processed_at
BEFORE UPDATE ON webhook_logs
FOR EACH ROW
EXECUTE FUNCTION update_webhook_processed_at();

COMMENT ON TABLE webhook_logs IS 'Logs all incoming payment webhooks for debugging and monitoring';
COMMENT ON COLUMN webhook_logs.signature_valid IS 'NULL if signature not checked, TRUE/FALSE if validated';
COMMENT ON COLUMN webhook_logs.processing_status IS 'received -> processing -> completed/failed';



