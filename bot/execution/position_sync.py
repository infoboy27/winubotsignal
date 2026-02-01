"""
Position Synchronization Module
Detects when positions are manually closed on Binance but not reflected in database
"""

import sys
import asyncio
import asyncpg
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Add packages to path
sys.path.append('/packages')

try:
    from common.config import get_settings
    from common.logging import get_logger
    settings = get_settings()
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone execution
    import os
    settings = type('Settings', (), {
        'binance_api_key': os.getenv('BINANCE_API_KEY', ''),
        'binance_secret_key': os.getenv('BINANCE_SECRET_KEY', '')
    })()
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class PositionSync:
    """Synchronizes database positions with actual Binance positions."""
    
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.spot_exchange = None
        self.futures_exchange = None
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize exchange connections."""
        if not self.test_mode:
            try:
                # Initialize spot exchange
                self.spot_exchange = ccxt.binance({
                    'apiKey': settings.binance_api_key,
                    'secret': settings.binance_secret_key,
                    'sandbox': False,
                    'enableRateLimit': True,
                })
                
                # Initialize futures exchange
                self.futures_exchange = ccxt.binance({
                    'apiKey': settings.binance_api_key,
                    'secret': settings.binance_secret_key,
                    'sandbox': False,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'}
                })
                
                logger.info("✅ Exchange connections initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize exchanges: {e}")
        else:
            logger.info("🧪 Test mode: Exchange connections disabled")
    
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def sync_positions(self) -> Dict:
        """Sync database positions with actual Binance positions."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get all open positions from database
            db_positions = await conn.fetch("""
                SELECT id, symbol, side, entry_price, quantity, market_type, created_at
                FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            if not db_positions:
                return {"synced": 0, "closed_manually": 0, "errors": 0}
            
            synced_count = 0
            closed_manually_count = 0
            error_count = 0
            
            for position in db_positions:
                try:
                    # Check if position still exists on Binance
                    still_exists = await self._check_position_exists(position)
                    
                    if not still_exists:
                        # Position was manually closed on Binance
                        await self._close_position_in_db(conn, position['id'], "manual_close_detected")
                        closed_manually_count += 1
                        logger.warning(f"🔍 Position {position['id']} ({position['symbol']}) was manually closed on Binance")
                    else:
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing position {position['id']}: {e}")
                    error_count += 1
            
            return {
                "synced": synced_count,
                "closed_manually": closed_manually_count,
                "errors": error_count,
                "total_checked": len(db_positions)
            }
            
        except Exception as e:
            logger.error(f"Error in position sync: {e}")
            return {"synced": 0, "closed_manually": 0, "errors": 1}
        finally:
            if conn:
                await conn.close()
    
    async def _check_position_exists(self, position: Dict) -> bool:
        """Check if position still exists on Binance."""
        if self.test_mode:
            # In test mode, assume all positions exist
            return True
        
        try:
            symbol = position['symbol'].replace('/', '')
            market_type = position['market_type']
            side = position['side']
            quantity = float(position['quantity'])
            
            if market_type == 'futures':
                # Check futures positions
                if self.futures_exchange:
                    positions = self.futures_exchange.fetch_positions([symbol])
                    for pos in positions:
                        if pos['symbol'] == symbol and pos['contracts'] > 0:
                            # Check if side matches
                            if (side == 'LONG' and pos['side'] == 'long') or \
                               (side == 'SHORT' and pos['side'] == 'short'):
                                return True
                    return False
            else:
                # Check spot balances
                if self.spot_exchange:
                    balance = self.spot_exchange.fetch_balance()
                    base_currency = symbol.replace('USDT', '')
                    free_balance = balance.get(base_currency, {}).get('free', 0)
                    
                    if side == 'LONG' and free_balance >= quantity:
                        return True
                    elif side == 'SHORT':
                        # For short positions, check if we have USDT to cover
                        usdt_balance = balance.get('USDT', {}).get('free', 0)
                        required_usdt = quantity * float(position['entry_price'])
                        return usdt_balance >= required_usdt
                    return False
            
            return True  # Default to existing if can't check
            
        except Exception as e:
            logger.error(f"Error checking position existence: {e}")
            return True  # Default to existing if error
    
    async def _close_position_in_db(self, conn, position_id: int, reason: str):
        """Close position in database."""
        try:
            # Get current price for PnL calculation
            position = await conn.fetchrow("""
                SELECT symbol, side, entry_price, current_price, quantity
                FROM paper_positions WHERE id = $1
            """, position_id)
            
            if not position:
                return
            
            # Calculate realized PnL
            entry_price = float(position['entry_price'])
            current_price = float(position['current_price'])
            quantity = float(position['quantity'])
            
            if position['side'] == 'LONG':
                realized_pnl = (current_price - entry_price) * quantity
            else:  # SHORT
                realized_pnl = (entry_price - current_price) * quantity
            
            # Update position
            await conn.execute("""
                UPDATE paper_positions 
                SET is_open = false, closed_at = $1, realized_pnl = $2, updated_at = $3, close_reason = $4
                WHERE id = $5
            """, datetime.utcnow(), realized_pnl, datetime.utcnow(), reason, position_id)
            
            logger.info(f"🔒 Position {position_id} closed in DB: {realized_pnl:.2f} USDT PnL - Reason: {reason}")
            
        except Exception as e:
            logger.error(f"Error closing position in DB: {e}")
    
    async def get_sync_status(self) -> Dict:
        """Get current sync status."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get position counts
            open_positions = await conn.fetchval("SELECT COUNT(*) FROM paper_positions WHERE is_open = true")
            closed_positions = await conn.fetchval("SELECT COUNT(*) FROM paper_positions WHERE is_open = false")
            
            # Get recent manual closures
            recent_manual = await conn.fetchval("""
                SELECT COUNT(*) FROM paper_positions 
                WHERE is_open = false AND close_reason LIKE '%manual%' 
                AND closed_at > NOW() - INTERVAL '1 hour'
            """)
            
            return {
                "open_positions": open_positions,
                "closed_positions": closed_positions,
                "recent_manual_closures": recent_manual,
                "last_sync": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                await conn.close()


async def main():
    """Test the position sync."""
    sync = PositionSync(test_mode=True)
    
    print("🔄 Testing Position Sync...")
    
    # Test sync
    result = await sync.sync_positions()
    print(f"📊 Sync Result: {result}")
    
    # Test status
    status = await sync.get_sync_status()
    print(f"📈 Status: {status}")


if __name__ == "__main__":
    asyncio.run(main())
