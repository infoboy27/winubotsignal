"""
Multi-Account Manager
Manages trading across multiple Binance accounts simultaneously
"""

import sys
import asyncio
import asyncpg
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Add packages to path
sys.path.append('/packages')

from common.logging import get_logger
from services.api_key_encryption import get_encryption_service
from execution.account_executor import AccountExecutor
from services.trade_notifications import get_notification_service

logger = get_logger(__name__)


class MultiAccountManager:
    """Manages trading across multiple accounts."""
    
    def __init__(self):
        self.encryption = get_encryption_service()
        self.notification_service = get_notification_service()
        self.db_pool = None
    
    async def connect_db(self):
        """Connect to database."""
        if not self.db_pool:
            self.db_pool = await asyncpg.create_pool(
                host='winu-bot-signal-postgres',
                port=5432,
                user='winu',
                password='winu250420',
                database='winudb',
                min_size=1,
                max_size=10
            )
            logger.info("✅ Database pool created for Multi-Account Manager")
    
    async def close_db(self):
        """Close database connection."""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database pool closed")
    
    async def get_active_accounts(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        Get all active trading accounts.
        
        Args:
            user_id: Filter by specific user (optional)
            
        Returns:
            List of account configurations
        """
        try:
            async with self.db_pool.acquire() as conn:
                if user_id:
                    query = """
                        SELECT * FROM user_api_keys
                        WHERE user_id = $1 
                        AND is_active = TRUE 
                        AND auto_trade_enabled = TRUE
                        AND is_verified = TRUE
                        ORDER BY id
                    """
                    rows = await conn.fetch(query, user_id)
                else:
                    query = """
                        SELECT * FROM user_api_keys
                        WHERE is_active = TRUE 
                        AND auto_trade_enabled = TRUE
                        AND is_verified = TRUE
                        ORDER BY user_id, id
                    """
                    rows = await conn.fetch(query)
                
                accounts = [dict(row) for row in rows]
                logger.info(f"📊 Found {len(accounts)} active trading accounts")
                return accounts
        
        except Exception as e:
            logger.error(f"❌ Failed to get active accounts: {e}")
            return []
    
    async def create_account_executor(self, account_config: Dict) -> Optional[AccountExecutor]:
        """
        Create an AccountExecutor for a specific account.
        
        Args:
            account_config: Account configuration from database
            
        Returns:
            AccountExecutor instance or None if failed
        """
        try:
            # Decrypt API keys
            api_key = self.encryption.decrypt_api_key(account_config['api_key_encrypted'])
            api_secret = self.encryption.decrypt_api_key(account_config['api_secret_encrypted'])
            
            # Create executor
            executor = AccountExecutor(
                api_key=api_key,
                api_secret=api_secret,
                account_config=account_config,
                test_mode=account_config.get('test_mode', False)
            )
            
            return executor
        
        except Exception as e:
            logger.error(f"❌ Failed to create executor for account {account_config.get('api_name')}: {e}")
            return None
    
    async def execute_signal_on_account(
        self,
        account_config: Dict,
        signal: Dict,
        order_group_id: str
    ) -> Dict:
        """
        Execute a signal on a single account.
        
        Args:
            account_config: Account configuration
            signal: Trading signal
            order_group_id: UUID grouping this order with others
            
        Returns:
            Execution result
        """
        account_name = account_config.get('api_name', 'Unknown')
        
        try:
            logger.info(f"🔄 Executing signal on account: {account_name}")
            
            # Create executor
            executor = await self.create_account_executor(account_config)
            if not executor:
                return {
                    "success": False,
                    "error": "Failed to create executor",
                    "account_name": account_name,
                    "account_id": account_config['id'],
                    "user_id": account_config['user_id']
                }
            
            # Execute order
            result = await executor.execute_order(signal)
            
            # Store order in database
            order_id = await self.store_order(
                account_config=account_config,
                signal=signal,
                result=result,
                order_group_id=order_group_id
            )
            
            result['multi_account_order_id'] = order_id
            result['order_group_id'] = order_group_id
            
            # Send Discord notification
            status = "success" if result.get('success', False) else "failed"
            result['account_name'] = account_name  # Ensure account name is in result
            await self.notification_service.send_order_notification(result, status)
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Failed to execute on {account_name}: {e}")
            
            error_result = {
                "success": False,
                "error": str(e),
                "account_name": account_name,
                "account_id": account_config['id'],
                "user_id": account_config['user_id']
            }
            
            # Send error notification
            await self.notification_service.send_order_notification(error_result, "failed")
            
            return error_result
    
    async def execute_signal_on_all_accounts(self, signal: Dict) -> Dict:
        """
        Execute the same signal on all active accounts in parallel.
        
        Args:
            signal: Trading signal
            
        Returns:
            Dict with summary of execution results
        """
        try:
            logger.info(f"🚀 Executing signal on all accounts: {signal.get('symbol')} {signal.get('direction')}")
            
            # Get all active accounts
            accounts = await self.get_active_accounts()
            
            if not accounts:
                logger.warning("⚠️  No active accounts found for trading")
                return {
                    "success": False,
                    "message": "No active accounts",
                    "results": []
                }
            
            # Generate order group ID
            order_group_id = str(uuid.uuid4())
            
            # Execute on all accounts in parallel
            tasks = [
                self.execute_signal_on_account(account, signal, order_group_id)
                for account in accounts
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful = [r for r in results if isinstance(r, dict) and r.get('success', False)]
            failed = [r for r in results if not (isinstance(r, dict) and r.get('success', False))]
            
            logger.info(f"✅ Signal executed: {len(successful)}/{len(accounts)} accounts successful")
            
            # Send summary notification
            await self.notification_service.send_signal_summary(signal, results)
            
            return {
                "success": True,
                "order_group_id": order_group_id,
                "total_accounts": len(accounts),
                "successful_accounts": len(successful),
                "failed_accounts": len(failed),
                "results": results
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to execute signal on all accounts: {e}")
            
            # Send error notification
            await self.notification_service.send_error_notification(
                "Multi-Account Execution Failed",
                str(e),
                {"signal": signal.get('symbol'), "direction": signal.get('direction')}
            )
            
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    async def store_order(
        self,
        account_config: Dict,
        signal: Dict,
        result: Dict,
        order_group_id: str
    ) -> Optional[int]:
        """
        Store order in database.
        
        Args:
            account_config: Account configuration
            signal: Trading signal
            result: Execution result
            order_group_id: Order group UUID
            
        Returns:
            Order ID or None if failed
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    INSERT INTO multi_account_orders (
                        signal_id, signal_data, order_group_id,
                        user_id, api_key_id, account_name,
                        exchange, symbol, side, order_type,
                        quantity, price, exchange_order_id, status,
                        filled_quantity, average_price,
                        stop_loss, take_profit, leverage, position_size_usd,
                        error_message, created_at, submitted_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                        $21, NOW(), NOW()
                    ) RETURNING id
                """
                
                import json
                
                order_id = await conn.fetchval(
                    query,
                    signal.get('id'),  # signal_id
                    json.dumps(signal),  # signal_data
                    order_group_id,
                    account_config['user_id'],
                    account_config['id'],
                    account_config['api_name'],
                    'binance',
                    signal.get('symbol'),
                    result.get('side', 'BUY'),
                    'MARKET',
                    result.get('quantity', 0),
                    result.get('average_price', 0),
                    result.get('exchange_order_id'),
                    'filled' if result.get('success') else 'failed',
                    result.get('quantity', 0) if result.get('success') else 0,
                    result.get('average_price', 0),
                    result.get('stop_loss', 0),
                    result.get('take_profit', 0),
                    result.get('leverage', 1.0),
                    result.get('position_size_usd', 0),
                    result.get('error') if not result.get('success') else None
                )
                
                logger.info(f"✅ Order stored with ID: {order_id}")
                return order_id
        
        except Exception as e:
            logger.error(f"❌ Failed to store order: {e}")
            return None
    
    async def get_account_orders(
        self,
        user_id: int,
        api_key_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get orders for a user's accounts.
        
        Args:
            user_id: User ID
            api_key_id: Specific account (optional)
            limit: Number of orders to return
            
        Returns:
            List of orders
        """
        try:
            async with self.db_pool.acquire() as conn:
                if api_key_id:
                    query = """
                        SELECT * FROM multi_account_orders
                        WHERE user_id = $1 AND api_key_id = $2
                        ORDER BY created_at DESC
                        LIMIT $3
                    """
                    rows = await conn.fetch(query, user_id, api_key_id, limit)
                else:
                    query = """
                        SELECT * FROM multi_account_orders
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                    """
                    rows = await conn.fetch(query, user_id, limit)
                
                return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"❌ Failed to get account orders: {e}")
            return []


# Singleton instance
_multi_account_manager = None

async def get_multi_account_manager() -> MultiAccountManager:
    """Get or create the multi-account manager singleton."""
    global _multi_account_manager
    if _multi_account_manager is None:
        _multi_account_manager = MultiAccountManager()
        await _multi_account_manager.connect_db()
    return _multi_account_manager



