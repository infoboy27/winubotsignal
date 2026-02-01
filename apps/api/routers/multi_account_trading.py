"""
Multi-Account Trading API Routes
Endpoints for managing user API keys and multi-account trading
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uuid

# Database and auth
from common.database import get_db, User
from routers.auth import get_current_active_user

# Services
import sys
sys.path.append('/app')
sys.path.append('/bot')

router = APIRouter(prefix="/api/bot/multi-account", tags=["Multi-Account Trading"])


# ===== Pydantic Models =====

class APIKeyCreate(BaseModel):
    """Model for creating a new API key."""
    api_key: str = Field(..., min_length=10, description="Binance API key")
    api_secret: str = Field(..., min_length=10, description="Binance API secret")
    api_name: str = Field(..., min_length=1, max_length=100, description="Friendly name")
    account_type: str = Field(default="futures", description="spot, futures, or both")
    test_mode: bool = Field(default=False)
    max_position_size_usd: float = Field(default=1000.0, ge=10, le=100000)
    leverage: float = Field(default=10.0, ge=1.0, le=125.0)
    max_daily_trades: int = Field(default=5, ge=1, le=50)
    max_risk_per_trade: float = Field(default=0.02, ge=0.001, le=0.10)
    max_daily_loss: float = Field(default=0.05, ge=0.01, le=0.20)
    stop_trading_on_loss: bool = Field(default=True)
    position_sizing_mode: str = Field(default="fixed")
    position_size_value: float = Field(default=100.0, ge=1.0)
    auto_trade_enabled: bool = Field(default=False)


class APIKeyUpdate(BaseModel):
    """Model for updating an existing API key."""
    api_name: Optional[str] = None
    max_position_size_usd: Optional[float] = None
    leverage: Optional[float] = None
    max_daily_trades: Optional[int] = None
    max_risk_per_trade: Optional[float] = None
    max_daily_loss: Optional[float] = None
    stop_trading_on_loss: Optional[bool] = None
    position_sizing_mode: Optional[str] = None
    position_size_value: Optional[float] = None
    auto_trade_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


# ===== API Key Management =====

@router.post("/api-keys")
async def create_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new Binance API key."""
    try:
        from services.api_key_encryption import get_encryption_service
        encryption = get_encryption_service()
        
        api_key_encrypted, api_secret_encrypted = encryption.encrypt_key_pair(
            data.api_key, data.api_secret
        )
        
        query = text("""
            INSERT INTO user_api_keys (
                user_id, exchange, api_key_encrypted, api_secret_encrypted, api_name,
                account_type, test_mode, auto_trade_enabled, max_position_size_usd,
                max_daily_trades, leverage, max_risk_per_trade, max_daily_loss,
                stop_trading_on_loss, position_sizing_mode, position_size_value
            ) VALUES (
                :user_id, 'binance', :api_key, :api_secret, :api_name,
                :account_type, :test_mode, :auto_trade, :max_position,
                :max_trades, :leverage, :max_risk, :max_loss,
                :stop_on_loss, :sizing_mode, :size_value
            ) RETURNING id
        """)
        
        result = await db.execute(query, {
            "user_id": current_user.id,
            "api_key": api_key_encrypted,
            "api_secret": api_secret_encrypted,
            "api_name": data.api_name,
            "account_type": data.account_type,
            "test_mode": data.test_mode,
            "auto_trade": data.auto_trade_enabled,
            "max_position": data.max_position_size_usd,
            "max_trades": data.max_daily_trades,
            "leverage": data.leverage,
            "max_risk": data.max_risk_per_trade,
            "max_loss": data.max_daily_loss,
            "stop_on_loss": data.stop_trading_on_loss,
            "sizing_mode": data.position_sizing_mode,
            "size_value": data.position_size_value
        })
        
        api_key_id = result.scalar_one()
        await db.commit()
        
        return {
            "success": True,
            "api_key_id": api_key_id,
            "api_key_masked": encryption.mask_api_key(data.api_key)
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all API keys for current user."""
    try:
        import sys
        import os
        print(f"DEBUG: sys.path = {sys.path}")
        print(f"DEBUG: cwd = {os.getcwd()}")
        print(f"DEBUG: /app/services exists = {os.path.exists('/app/services')}")
        print(f"DEBUG: /app/services/__init__.py exists = {os.path.exists('/app/services/__init__.py')}")
        print(f"DEBUG: /app/services/api_key_encryption.py exists = {os.path.exists('/app/services/api_key_encryption.py')}")
        
        from services.api_key_encryption import get_encryption_service
        encryption = get_encryption_service()
        
        query = text("SELECT * FROM user_api_keys WHERE user_id = :user_id ORDER BY created_at DESC")
        result = await db.execute(query, {"user_id": current_user.id})
        
        api_keys = []
        for row in result.fetchall():
            row_dict = dict(row._mapping)
            try:
                key = encryption.decrypt_api_key(row_dict['api_key_encrypted'])
                row_dict['api_key_masked'] = encryption.mask_api_key(key)
            except:
                row_dict['api_key_masked'] = "****"
            
            # Remove encrypted keys from response
            row_dict.pop('api_key_encrypted', None)
            row_dict.pop('api_secret_encrypted', None)
            
            api_keys.append(row_dict)
        
        return {"api_keys": api_keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api-keys/{api_key_id}")
async def update_api_key(
    api_key_id: int,
    data: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update API key settings."""
    try:
        updates = []
        params = {"api_key_id": api_key_id, "user_id": current_user.id}
        
        if data.api_name: updates.append("api_name = :api_name"); params["api_name"] = data.api_name
        if data.max_position_size_usd: updates.append("max_position_size_usd = :max_pos"); params["max_pos"] = data.max_position_size_usd
        if data.leverage: updates.append("leverage = :leverage"); params["leverage"] = data.leverage
        if data.max_daily_trades: updates.append("max_daily_trades = :max_trades"); params["max_trades"] = data.max_daily_trades
        if data.max_risk_per_trade: updates.append("max_risk_per_trade = :max_risk"); params["max_risk"] = data.max_risk_per_trade
        if data.max_daily_loss: updates.append("max_daily_loss = :max_loss"); params["max_loss"] = data.max_daily_loss
        if data.stop_trading_on_loss is not None: updates.append("stop_trading_on_loss = :stop_loss"); params["stop_loss"] = data.stop_trading_on_loss
        if data.position_sizing_mode: updates.append("position_sizing_mode = :sizing"); params["sizing"] = data.position_sizing_mode
        if data.position_size_value: updates.append("position_size_value = :size_val"); params["size_val"] = data.position_size_value
        if data.auto_trade_enabled is not None: updates.append("auto_trade_enabled = :auto"); params["auto"] = data.auto_trade_enabled
        if data.is_active is not None: updates.append("is_active = :active"); params["active"] = data.is_active
        
        if not updates:
            return {"success": True}
        
        query = text(f"UPDATE user_api_keys SET {', '.join(updates)}, updated_at = NOW() WHERE id = :api_key_id AND user_id = :user_id RETURNING id")
        result = await db.execute(query, params)
        
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="API key not found")
        
        await db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key."""
    try:
        query = text("DELETE FROM user_api_keys WHERE id = :api_key_id AND user_id = :user_id RETURNING id")
        result = await db.execute(query, {"api_key_id": api_key_id, "user_id": current_user.id})
        
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="API key not found")
        
        await db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys/{api_key_id}/verify")
async def verify_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify API key by testing connection."""
    try:
        from services.api_key_encryption import get_encryption_service
        import ccxt
        
        encryption = get_encryption_service()
        
        query = text("SELECT * FROM user_api_keys WHERE id = :api_key_id AND user_id = :user_id")
        result = await db.execute(query, {"api_key_id": api_key_id, "user_id": current_user.id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="API key not found")
        
        row_dict = dict(row._mapping)
        api_key = encryption.decrypt_api_key(row_dict['api_key_encrypted'])
        api_secret = encryption.decrypt_api_key(row_dict['api_secret_encrypted'])
        
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': row_dict['test_mode'],
            'enableRateLimit': True
        })
        
        balance = await exchange.fetch_balance()
        
        update_query = text("UPDATE user_api_keys SET is_verified = TRUE, last_verified_at = NOW(), verification_error = NULL WHERE id = :api_key_id")
        await db.execute(update_query, {"api_key_id": api_key_id})
        await db.commit()
        
        return {
            "success": True,
            "balance": balance.get('total', {}).get('USDT', 0)
        }
    except Exception as e:
        error_query = text("UPDATE user_api_keys SET is_verified = FALSE, verification_error = :error WHERE id = :api_key_id")
        await db.execute(error_query, {"api_key_id": api_key_id, "error": str(e)[:500]})
        await db.commit()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders")
async def get_orders(
    api_key_id: Optional[int] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get orders for current user."""
    try:
        if api_key_id:
            query = text("SELECT * FROM multi_account_orders WHERE user_id = :user_id AND api_key_id = :api_key_id ORDER BY created_at DESC LIMIT :limit")
            result = await db.execute(query, {"user_id": current_user.id, "api_key_id": api_key_id, "limit": limit})
        else:
            query = text("SELECT * FROM multi_account_orders WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit")
            result = await db.execute(query, {"user_id": current_user.id, "limit": limit})
        
        orders = [dict(row._mapping) for row in result.fetchall()]
        return {"orders": orders, "total": len(orders)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard stats."""
    try:
        accounts_query = text("SELECT * FROM user_api_keys WHERE user_id = :user_id ORDER BY created_at DESC")
        accounts_result = await db.execute(accounts_query, {"user_id": current_user.id})
        accounts = [dict(row._mapping) for row in accounts_result.fetchall()]
        
        # Mask API keys
        from services.api_key_encryption import get_encryption_service
        encryption = get_encryption_service()
        for account in accounts:
            try:
                key = encryption.decrypt_api_key(account['api_key_encrypted'])
                account['api_key_masked'] = encryption.mask_api_key(key)
            except:
                account['api_key_masked'] = "****"
            account.pop('api_key_encrypted', None)
            account.pop('api_secret_encrypted', None)
        
        today_query = text("SELECT COUNT(*) as total, COUNT(CASE WHEN status = 'filled' THEN 1 END) as success FROM multi_account_orders WHERE user_id = :user_id AND created_at >= CURRENT_DATE")
        today_result = await db.execute(today_query, {"user_id": current_user.id})
        today_stats = dict(today_result.fetchone()._mapping)
        
        return {
            "accounts": accounts,
            "today_stats": today_stats,
            "summary": {
                "total_accounts": len(accounts),
                "active_accounts": len([a for a in accounts if a['is_active'] and a['auto_trade_enabled']]),
                "total_balance": sum([float(a.get('current_balance') or 0) for a in accounts]),
                "total_pnl": sum([float(a.get('total_pnl') or 0) for a in accounts])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{api_key_id}/balance")
async def get_account_balance(
    api_key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current balance for account."""
    try:
        from services.api_key_encryption import get_encryption_service
        import ccxt
        
        encryption = get_encryption_service()
        
        query = text("SELECT * FROM user_api_keys WHERE id = :api_key_id AND user_id = :user_id")
        result = await db.execute(query, {"api_key_id": api_key_id, "user_id": current_user.id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="API key not found")
        
        row_dict = dict(row._mapping)
        api_key = encryption.decrypt_api_key(row_dict['api_key_encrypted'])
        api_secret = encryption.decrypt_api_key(row_dict['api_secret_encrypted'])
        
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': row_dict['test_mode'],
            'enableRateLimit': True
        })
        
        if row_dict['account_type'] in ['futures', 'both']:
            exchange.options['defaultType'] = 'future'
        
        balance = await exchange.fetch_balance()
        usdt = balance.get('USDT', {})
        total = float(usdt.get('total', 0))
        
        update_query = text("UPDATE user_api_keys SET current_balance = :balance, last_balance_update = NOW() WHERE id = :api_key_id")
        await db.execute(update_query, {"balance": total, "api_key_id": api_key_id})
        await db.commit()
        
        return {
            "account_name": row_dict['api_name'],
            "balance": {"total": total, "free": float(usdt.get('free', 0)), "used": float(usdt.get('used', 0))},
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
