"""
Simple status endpoint that doesn't overload the database
"""

from fastapi import APIRouter
import asyncio
import asyncpg
from datetime import datetime

router = APIRouter()

@router.get("/api/simple-status")
async def get_simple_status():
    """Get simple bot status without complex queries."""
    try:
        # Simple connection with immediate cleanup
        conn = await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb',
            command_timeout=5
        )
        
        try:
            # Get basic position count
            position_count = await conn.fetchval("SELECT COUNT(*) FROM paper_positions WHERE is_open = true")
            
            # Get latest position if exists
            latest_position = await conn.fetchrow("""
                SELECT symbol, side, entry_price, current_price, unrealized_pnl, market_type 
                FROM paper_positions 
                WHERE is_open = true 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            position_data = None
            if latest_position:
                position_data = {
                    "symbol": latest_position['symbol'],
                    "side": latest_position['side'],
                    "entry_price": float(latest_position['entry_price']),
                    "current_price": float(latest_position['current_price']),
                    "unrealized_pnl": float(latest_position['unrealized_pnl']),
                    "market_type": latest_position['market_type']
                }
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "open_positions": position_count,
                "latest_position": position_data,
                "bot_status": "running"
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "bot_status": "unknown"
        }


















