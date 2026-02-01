"""
Simple API endpoints for dashboard data without authentication
"""

from fastapi import FastAPI
import asyncpg
from datetime import datetime
import json

app = FastAPI(title="Simple Bot API")

@app.get("/api/data")
async def get_bot_data():
    """Get all bot data without authentication."""
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb',
            command_timeout=10
        )
        
        try:
            # Get positions
            positions = await conn.fetch("""
                SELECT id, symbol, side, entry_price, quantity, current_price, unrealized_pnl, 
                       stop_loss, take_profit, market_type, created_at, updated_at
                FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            position_list = []
            total_pnl = 0
            for pos in positions:
                pnl = float(pos['unrealized_pnl'])
                total_pnl += pnl
                position_list.append({
                    "id": pos['id'],
                    "symbol": pos['symbol'],
                    "side": pos['side'],
                    "entry_price": float(pos['entry_price']),
                    "current_price": float(pos['current_price']),
                    "quantity": float(pos['quantity']),
                    "unrealized_pnl": pnl,
                    "market_type": pos['market_type'],
                    "stop_loss": float(pos['stop_loss']) if pos['stop_loss'] else None,
                    "take_profit": float(pos['take_profit']) if pos['take_profit'] else None,
                    "created_at": pos['created_at'].isoformat(),
                    "updated_at": pos['updated_at'].isoformat()
                })
            
            # Get basic stats
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_trades,
                    COALESCE(SUM(CASE WHEN is_open = false THEN realized_pnl ELSE 0 END), 0) as total_realized_pnl,
                    COUNT(CASE WHEN is_open = false AND realized_pnl > 0 THEN 1 END) as winning_trades
                FROM paper_positions
            """)
            
            win_rate = 0
            if stats['total_trades'] > 0:
                win_rate = (stats['winning_trades'] / stats['total_trades']) * 100
            
            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "bot_status": "running",
                "positions": position_list,
                "total_positions": len(position_list),
                "total_unrealized_pnl": total_pnl,
                "stats": {
                    "total_trades": stats['total_trades'],
                    "total_realized_pnl": float(stats['total_realized_pnl']),
                    "win_rate": round(win_rate, 2)
                },
                "balances": {
                    "spot_balance": "96.56 USDT",  # From logs
                    "futures_balance": "Available",
                    "total_balance": "96.56+ USDT"
                }
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


















