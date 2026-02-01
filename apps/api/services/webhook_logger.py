"""
Webhook Logging Utility
Logs all incoming payment webhooks for debugging and monitoring
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import logging

logger = logging.getLogger(__name__)


async def log_webhook(
    db: AsyncSession,
    payment_method: str,
    webhook_type: str,
    webhook_data: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    signature: Optional[str] = None,
    signature_valid: Optional[bool] = None,
    user_id: Optional[int] = None,
    payment_id: Optional[str] = None,
    plan_id: Optional[str] = None
) -> int:
    """
    Log an incoming webhook to the database.
    
    Args:
        db: Database session
        payment_method: Payment method (coinbase_commerce, nowpayments, etc.)
        webhook_type: Type of webhook event
        webhook_data: Full webhook payload
        headers: HTTP headers from the webhook request
        signature: Webhook signature for validation
        signature_valid: Whether the signature was validated (None if not checked)
        user_id: User ID if extracted from webhook
        payment_id: Payment/transaction ID if available
        plan_id: Plan ID if available
        
    Returns:
        webhook_log_id: ID of the created webhook log entry
    """
    try:
        # Convert dicts to JSON strings
        webhook_data_json = json.dumps(webhook_data)
        headers_json = json.dumps(headers) if headers else None
        
        query = text("""
            INSERT INTO webhook_logs 
            (payment_method, webhook_type, webhook_data, headers, signature, 
             signature_valid, processing_status, user_id, payment_id, plan_id, created_at)
            VALUES 
            (:payment_method, :webhook_type, CAST(:webhook_data AS jsonb), CAST(:headers AS jsonb), :signature,
             :signature_valid, 'received', :user_id, :payment_id, :plan_id, NOW())
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "payment_method": payment_method,
            "webhook_type": webhook_type,
            "webhook_data": webhook_data_json,
            "headers": headers_json,
            "signature": signature,
            "signature_valid": signature_valid,
            "user_id": user_id,
            "payment_id": payment_id,
            "plan_id": plan_id
        })
        
        webhook_log_id = result.scalar_one()
        await db.commit()
        
        logger.info(f"📝 Webhook logged: {payment_method} - {webhook_type} - ID: {webhook_log_id}")
        return webhook_log_id
        
    except Exception as e:
        logger.error(f"❌ Error logging webhook: {e}")
        await db.rollback()
        raise


async def update_webhook_status(
    db: AsyncSession,
    webhook_log_id: int,
    status: str,
    error_message: Optional[str] = None
):
    """
    Update the processing status of a webhook log.
    
    Args:
        db: Database session
        webhook_log_id: ID of the webhook log entry
        status: New status (processing, completed, failed)
        error_message: Error message if status is 'failed'
    """
    try:
        query = text("""
            UPDATE webhook_logs
            SET processing_status = :status,
                error_message = :error_message
            WHERE id = :webhook_log_id
        """)
        
        await db.execute(query, {
            "status": status,
            "error_message": error_message,
            "webhook_log_id": webhook_log_id
        })
        
        await db.commit()
        
        status_emoji = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
        logger.info(f"{status_emoji} Webhook {webhook_log_id} status: {status}")
        
    except Exception as e:
        logger.error(f"❌ Error updating webhook status: {e}")
        await db.rollback()


async def get_recent_webhook_logs(
    db: AsyncSession,
    minutes: int = 30,
    payment_method: Optional[str] = None,
    status: Optional[str] = None
) -> list:
    """
    Get recent webhook logs for monitoring.
    
    Args:
        db: Database session
        minutes: How many minutes back to look
        payment_method: Filter by payment method (optional)
        status: Filter by processing status (optional)
        
    Returns:
        List of webhook log dictionaries
    """
    try:
        filters = ["created_at >= NOW() - INTERVAL ':minutes minutes'"]
        params = {"minutes": minutes}
        
        if payment_method:
            filters.append("payment_method = :payment_method")
            params["payment_method"] = payment_method
            
        if status:
            filters.append("processing_status = :status")
            params["status"] = status
        
        where_clause = " AND ".join(filters)
        
        query = text(f"""
            SELECT 
                id, payment_method, webhook_type, webhook_data,
                signature_valid, processing_status, error_message,
                user_id, payment_id, plan_id, created_at, processed_at
            FROM webhook_logs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        return [dict(row._mapping) for row in rows]
        
    except Exception as e:
        logger.error(f"❌ Error fetching webhook logs: {e}")
        return []


async def get_failed_webhooks(db: AsyncSession, hours: int = 24) -> list:
    """
    Get webhooks that failed processing.
    
    Args:
        db: Database session
        hours: How many hours back to look
        
    Returns:
        List of failed webhook log dictionaries
    """
    try:
        query = text("""
            SELECT 
                id, payment_method, webhook_type, webhook_data,
                error_message, user_id, payment_id, plan_id,
                created_at, processed_at
            FROM webhook_logs
            WHERE processing_status = 'failed'
            AND created_at >= NOW() - INTERVAL ':hours hours'
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query, {"hours": hours})
        rows = result.fetchall()
        
        return [dict(row._mapping) for row in rows]
        
    except Exception as e:
        logger.error(f"❌ Error fetching failed webhooks: {e}")
        return []

