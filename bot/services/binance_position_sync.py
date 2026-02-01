"""
Automatic Binance Position Sync Service
Periodically checks Binance for open positions and syncs them to database
"""

import ccxt
import asyncpg
import asyncio
from datetime import datetime
from typing import Dict, List
import sys
sys.path.append('/packages')

from common.config import get_settings
from common.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class BinancePositionSync:
    """Syncs Binance positions to database automatically."""
    
    def __init__(self):
        self.exchange = None
        self.running = False
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialize Binance futures exchange."""
        try:
            self.exchange = ccxt.binance({
                'apiKey': settings.exchange.binance_api_key,
                'secret': settings.exchange.binance_api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            logger.info("✅ Binance position sync initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Binance sync: {e}")
    
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def fetch_binance_positions(self) -> List[Dict]:
        """Fetch open positions from Binance."""
        try:
            positions = self.exchange.fetch_positions()
            open_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
            return open_positions
        except Exception as e:
            logger.error(f"Error fetching Binance positions: {e}")
            return []
    
    async def get_db_positions(self, conn) -> List[str]:
        """Get list of symbols with open positions in database."""
        try:
            result = await conn.fetch("""
                SELECT DISTINCT symbol 
                FROM paper_positions 
                WHERE is_open = true
            """)
            return [row['symbol'] for row in result]
        except Exception as e:
            logger.error(f"Error fetching DB positions: {e}")
            return []
    
    async def import_position(self, conn, position: Dict) -> bool:
        """Import a single position to database."""
        try:
            symbol = position['symbol']
            side = 'LONG' if position['side'] == 'long' else 'SHORT'
            entry_price = float(position.get('entryPrice', 0))
            contracts = abs(float(position.get('contracts', 0)))
            unrealized_pnl = float(position.get('unrealizedPnl', 0))
            mark_price = float(position.get('markPrice', 0))
            leverage = float(position.get('leverage', 1))
            
            # Insert position
            await conn.execute("""
                INSERT INTO paper_positions (
                    symbol, side, entry_price, quantity, current_price,
                    unrealized_pnl, market_type, is_open,
                    opened_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                symbol, side, entry_price, contracts, mark_price,
                unrealized_pnl, 'futures', True,
                datetime.utcnow(), datetime.utcnow(), datetime.utcnow()
            )
            
            logger.info(f"📥 Auto-imported: {symbol} {side} @ ${entry_price} ({contracts} contracts)")
            return True
            
        except Exception as e:
            logger.error(f"Error importing position {position.get('symbol')}: {e}")
            return False
    
    async def sync_once(self) -> Dict:
        """Perform one sync cycle."""
        conn = None
        try:
            # Fetch from Binance
            binance_positions = await self.fetch_binance_positions()
            
            # Connect to DB
            conn = await self.connect_db()
            
            # Get existing positions in DB
            db_symbols = await self.get_db_positions(conn)
            
            # Get symbols currently on Binance
            binance_symbols = [p['symbol'] for p in binance_positions]
            
            # Close positions in DB that are no longer on Binance
            closed_count = 0
            for db_symbol in db_symbols:
                if db_symbol not in binance_symbols:
                    # Position is in DB but not on Binance - close it
                    await conn.execute("""
                        UPDATE paper_positions 
                        SET is_open = false, 
                            closed_at = NOW(), 
                            updated_at = NOW(),
                            close_reason = 'binance_sync_closed'
                        WHERE symbol = $1 AND is_open = true
                    """, db_symbol)
                    closed_count += 1
                    logger.info(f"✅ Closed position {db_symbol} (no longer on Binance)")
            
            # Find new positions to import
            new_count = 0
            for position in binance_positions:
                symbol = position['symbol']
                
                # Skip if already in database
                if symbol in db_symbols:
                    continue
                
                # Import new position
                success = await self.import_position(conn, position)
                if success:
                    new_count += 1
            
            return {
                "new_positions": new_count,
                "closed_positions": closed_count,
                "existing": len(db_symbols),
                "binance_total": len(binance_positions)
            }
            
        except Exception as e:
            logger.error(f"Error in sync cycle: {e}")
            return {"error": str(e)}
        
        finally:
            if conn:
                await conn.close()
    
    async def run_continuous_sync(self, interval_seconds: int = 300):
        """Run continuous sync every N seconds (default 5 minutes)."""
        self.running = True
        logger.info(f"🔄 Starting continuous position sync (every {interval_seconds}s)")
        
        while self.running:
            try:
                result = await self.sync_once()
                
                if 'error' in result:
                    logger.warning(f"⚠️ Sync error: {result['error']}")
                elif result.get('new_positions', 0) > 0 or result.get('closed_positions', 0) > 0:
                    logger.info(f"✅ Sync complete: {result.get('new_positions', 0)} new, {result.get('closed_positions', 0)} closed")
                else:
                    logger.debug(f"✓ Sync complete: No changes")
                
                # Wait before next sync
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop the sync service."""
        self.running = False
        logger.info("⏹️ Position sync stopped")


# For standalone testing
if __name__ == "__main__":
    async def test_sync():
        sync = BinancePositionSync()
        result = await sync.sync_once()
        print(f"Sync result: {result}")
    
    asyncio.run(test_sync())

