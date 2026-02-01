"""
Push Notifications Router
Handles device token registration for mobile app push notifications
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

import sys
sys.path.append('/packages')

from common.database import User
from common.logging import get_logger
from routers.auth import get_current_active_user
from dependencies import get_db

router = APIRouter(prefix="/api/push", tags=["Push Notifications"])
logger = get_logger(__name__)


class DeviceTokenRegister(BaseModel):
    """Device token registration model."""
    device_token: str = Field(..., min_length=10, description="Device push token")
    platform: str = Field(..., pattern="^(ios|android)$", description="Platform: ios or android")
    device_id: Optional[str] = Field(None, description="Unique device identifier")
    app_version: Optional[str] = Field(None, description="App version")


class DeviceTokenUnregister(BaseModel):
    """Device token unregistration model."""
    device_token: str = Field(..., min_length=10, description="Device push token")


@router.post("/register")
async def register_device_token(
    device: DeviceTokenRegister,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register device token for push notifications.
    
    This endpoint stores the device token so the backend can send push notifications
    to the mobile app when new signals are generated.
    """
    try:
        # Check if device token already exists
        check_query = text("""
            SELECT id FROM device_tokens 
            WHERE user_id = :user_id AND device_token = :device_token
        """)
        result = await db.execute(
            check_query,
            {"user_id": current_user.id, "device_token": device.device_token}
        )
        existing = result.fetchone()
        
        if existing:
            # Update existing token
            update_query = text("""
                UPDATE device_tokens 
                SET platform = :platform,
                    device_id = :device_id,
                    app_version = :app_version,
                    updated_at = :updated_at
                WHERE id = :id
            """)
            await db.execute(
                update_query,
                {
                    "id": existing[0],
                    "platform": device.platform,
                    "device_id": device.device_id,
                    "app_version": device.app_version,
                    "updated_at": datetime.utcnow()
                }
            )
            logger.info(f"Updated device token for user {current_user.id}")
        else:
            # Create new device token entry
            # Note: You'll need to create the device_tokens table first
            insert_query = text("""
                INSERT INTO device_tokens 
                (user_id, device_token, platform, device_id, app_version, created_at, updated_at)
                VALUES 
                (:user_id, :device_token, :platform, :device_id, :app_version, :created_at, :updated_at)
            """)
            await db.execute(
                insert_query,
                {
                    "user_id": current_user.id,
                    "device_token": device.device_token,
                    "platform": device.platform,
                    "device_id": device.device_id,
                    "app_version": device.app_version,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            )
            logger.info(f"Registered new device token for user {current_user.id}")
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "Device token registered successfully",
            "platform": device.platform
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error registering device token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device token"
        )


@router.post("/unregister")
async def unregister_device_token(
    device: DeviceTokenUnregister,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unregister device token.
    
    Removes the device token from the database so the user stops receiving
    push notifications on this device.
    """
    try:
        delete_query = text("""
            DELETE FROM device_tokens 
            WHERE user_id = :user_id AND device_token = :device_token
        """)
        result = await db.execute(
            delete_query,
            {"user_id": current_user.id, "device_token": device.device_token}
        )
        await db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Unregistered device token for user {current_user.id}")
            return {
                "status": "success",
                "message": "Device token unregistered successfully"
            }
        else:
            return {
                "status": "not_found",
                "message": "Device token not found"
            }
            
    except Exception as e:
        await db.rollback()
        logger.error(f"Error unregistering device token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister device token"
        )


@router.get("/tokens")
async def get_user_device_tokens(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all device tokens for the current user.
    
    Useful for managing multiple devices.
    """
    try:
        query = text("""
            SELECT id, device_token, platform, device_id, app_version, created_at
            FROM device_tokens 
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)
        result = await db.execute(query, {"user_id": current_user.id})
        tokens = result.fetchall()
        
        return {
            "status": "success",
            "tokens": [
                {
                    "id": token[0],
                    "platform": token[2],
                    "device_id": token[3],
                    "app_version": token[4],
                    "created_at": token[5].isoformat() if token[5] else None
                }
                for token in tokens
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching device tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch device tokens"
        )
