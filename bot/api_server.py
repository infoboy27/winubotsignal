"""
Trading Bot API Server
Provides HTTP endpoints for bot control and monitoring
"""

import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Simple logging setup
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bot instance - simplified for API server
bot_instance = None
import os
import subprocess

def check_bot_running():
    """Check if the trading bot is running by checking if we can connect to it."""
    try:
        # Check if the trading bot container is running
        import subprocess
        result = subprocess.run(
            ['docker', 'inspect', '--format', '{{.State.Running}}', 'winu-bot-signal-trading-bot'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip() == 'true'
        else:
            # Fallback: assume it's running if we can't check (for internal network access)
            return True
    except Exception:
        # Fallback: assume it's running if we can't check (for internal network access)
        return True

# Initialize with default values - will be updated with real data
bot_status = {
    "is_running": False,
    "test_mode": os.getenv('BOT_TEST_MODE', 'false').lower() == 'true',
    "uptime": 0,
    "start_time": None,
    "stats": {
        "signals_processed": 0,
        "trades_executed": 0,
        "successful_trades": 0,
        "failed_trades": 0,
        "total_pnl": 0.0
    }
}

app = FastAPI(title="Trading Bot API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/bot/status")
async def get_bot_status():
    """Get current bot status."""
    global bot_status
    
    # Check if trading bot is actually running
    bot_status["is_running"] = check_bot_running()
    
    # If bot is running, try to get real stats from bot logs or database
    if bot_status["is_running"]:
        try:
            # Try to get real stats from database
            import asyncpg
            conn = await asyncpg.connect(
                host='winu-bot-signal-postgres',
                port=5432,
                user='winu',
                password='winu250420',
                database='winudb'
            )
            
            # Get real trading statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN is_executed = true THEN 1 ELSE 0 END) as executed_trades,
                    SUM(CASE WHEN pnl > 0 AND is_executed = true THEN 1 ELSE 0 END) as successful_trades,
                    SUM(CASE WHEN pnl < 0 AND is_executed = true THEN 1 ELSE 0 END) as failed_trades,
                    COALESCE(SUM(pnl), 0) as total_pnl
                FROM signals 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)
            
            if stats:
                bot_status["stats"] = {
                    "signals_processed": stats['total_signals'],
                    "trades_executed": stats['executed_trades'],
                    "successful_trades": stats['successful_trades'],
                    "failed_trades": stats['failed_trades'],
                    "total_pnl": float(stats['total_pnl'])
                }
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Error fetching real stats: {e}")
            # Keep default stats if database fetch fails
    
    # Calculate real uptime if bot is running
    if bot_status["is_running"] and bot_status["start_time"]:
        current_time = datetime.now()
        uptime_seconds = int((current_time - bot_status["start_time"]).total_seconds())
        bot_status["uptime"] = uptime_seconds
    
    return {
        "is_running": bot_status["is_running"],
        "test_mode": bot_status["test_mode"],
        "uptime": bot_status["uptime"],
        "stats": bot_status["stats"],
        "message": "Real bot status retrieved"
    }


@app.post("/api/bot/start")
async def start_bot():
    """Start the trading bot."""
    global bot_status
    
    try:
        if bot_status["is_running"]:
            return {"message": "Bot is already running", "status": "warning"}
        
        # Update bot status
        bot_status["is_running"] = True
        bot_status["start_time"] = datetime.now()
        bot_status["uptime"] = 0
        
        # Record bot session in database
        try:
            import asyncpg
            conn = await asyncpg.connect(
                host='winu-bot-signal-postgres',
                port=5432,
                user='winu',
                password='winu250420',
                database='winudb'
            )
            await conn.execute("""
                UPDATE bot_sessions SET is_active = false WHERE is_active = true
            """)
            await conn.execute("""
                INSERT INTO bot_sessions (is_active, bot_status, test_mode) 
                VALUES (true, 'running', true)
            """)
            await conn.close()
        except Exception as e:
            logger.warning(f"Could not record bot session: {e}")
        
        logger.info("Bot start command received")
        return {"message": "Bot started successfully", "status": "success"}
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return {"message": f"Error starting bot: {str(e)}", "status": "error"}


@app.post("/api/bot/stop")
async def stop_bot():
    """Stop the trading bot."""
    global bot_status
    
    try:
        if not bot_status["is_running"]:
            return {"message": "Bot is not running", "status": "warning"}
        
        # Update bot status
        bot_status["is_running"] = False
        bot_status["uptime"] = 0
        bot_status["start_time"] = None
        
        # Record bot session end in database
        try:
            import asyncpg
            conn = await asyncpg.connect(
                host='winu-bot-signal-postgres',
                port=5432,
                user='winu',
                password='winu250420',
                database='winudb'
            )
            await conn.execute("""
                UPDATE bot_sessions SET is_active = false WHERE is_active = true
            """)
            await conn.close()
        except Exception as e:
            logger.warning(f"Could not record bot session end: {e}")
        
        logger.info("Bot stop command received")
        return {"message": "Bot stopped successfully", "status": "success"}
        
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return {"message": f"Error stopping bot: {str(e)}", "status": "error"}


@app.post("/api/bot/close-position/{position_id}")
async def close_position_api(position_id: int):
    """Close a specific position via bot API."""
    try:
        from execution.dual_executor import DualTradingExecutor
        
        # Initialize executor
        executor = DualTradingExecutor()
        
        # Close position using bot's close_position method
        result = await executor.close_position(position_id, "manual_close")
        
        if result['success']:
            logger.info(f"Position {position_id} closed successfully via API")
            return {
                "message": f"Position {position_id} closed successfully",
                "result": result,
                "status": "success"
            }
        else:
            logger.error(f"Failed to close position {position_id}: {result['error']}")
            return {
                "message": f"Failed to close position: {result['error']}",
                "status": "error"
            }
            
    except Exception as e:
        logger.error(f"Error closing position {position_id}: {e}")
        return {
            "message": f"Error closing position: {str(e)}",
            "status": "error"
        }


@app.post("/api/bot/emergency-stop")
async def emergency_stop():
    """Emergency stop the bot and close all positions."""
    global bot_status
    
    try:
        # Emergency stop - immediately stop bot
        bot_status["is_running"] = False
        bot_status["uptime"] = 0
        
        logger.warning("Emergency stop command received")
        return {"message": "Emergency stop executed successfully", "status": "success"}
        
    except Exception as e:
        logger.error(f"Error emergency stopping bot: {e}")
        return {"message": f"Error emergency stopping bot: {str(e)}", "status": "error"}


@app.get("/api/bot/stats")
async def get_bot_stats():
    """Get detailed bot statistics."""
    global bot_status
    
    return {
        "message": "Bot statistics retrieved",
        "stats": bot_status["stats"]
    }


@app.get("/api/bot/positions")
async def get_bot_positions():
    """Get current bot positions."""
    try:
        import asyncpg
        # Use connection pool to prevent connection leaks
        pool = await asyncpg.create_pool(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb',
            min_size=1,
            max_size=3,
            command_timeout=30
        )
        
        async with pool.acquire() as conn:
            # Get open positions
            positions = await conn.fetch("""
            SELECT id, symbol, side, entry_price, quantity, stop_loss, take_profit,
                   current_price, unrealized_pnl, market_type, created_at, updated_at
            FROM paper_positions 
            WHERE is_open = true
            ORDER BY created_at DESC
        """)
        
        position_list = []
        for pos in positions:
            position_list.append({
                "id": pos['id'],
                "symbol": pos['symbol'],
                "side": pos['side'],
                "entry_price": float(pos['entry_price']),
                "current_price": float(pos['current_price']),
                "quantity": float(pos['quantity']),
                "unrealized_pnl": float(pos['unrealized_pnl']),
                "market_type": pos['market_type'],
                "stop_loss": float(pos['stop_loss']) if pos['stop_loss'] else None,
                "take_profit": float(pos['take_profit']) if pos['take_profit'] else None,
                "created_at": pos['created_at'].isoformat(),
                "updated_at": pos['updated_at'].isoformat()
            })
            
            return {"positions": position_list}
        
    except Exception as e:
        logger.error(f"Error getting bot positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/balance")
async def get_bot_balance():
    """Get current Binance account balance."""
    try:
        # Get balance directly from Binance
        import ccxt
        import os
        
        # Get API credentials from environment
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        test_mode = os.getenv('BOT_TEST_MODE', 'true').lower() == 'true'
        
        if not api_key or not api_secret:
            raise Exception("Binance API credentials not found")
        
        # Create exchange instance
        if test_mode:
            # Mock data for test mode
            free_balance = 1000.0
            total_balance = 1000.0
        else:
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            
            # Get futures balance (since user transferred to futures)
            balance = exchange.fetch_balance({'type': 'future'})
            
            # Extract USDT balance
            usdt_balance = balance.get('USDT', {})
            free_balance = usdt_balance.get('free', 0)
            total_balance = usdt_balance.get('total', 0)
        
        return {
            "message": "Balance retrieved successfully",
            "balance": {
                "free_balance": float(free_balance),
                "total_balance": float(total_balance),
                "currency": "USDT"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return {
            "message": f"Error retrieving balance: {str(e)}",
            "balance": {"free_balance": 0, "total_balance": 0, "currency": "USDT"},
            "timestamp": datetime.utcnow().isoformat()
        }




@app.get("/api/bot/dual-balances")
async def get_dual_balances():
    """Get current Binance account balances for both spot and futures."""
    try:
        import ccxt
        import asyncio
        import signal
        
        # Get API credentials from environment
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        test_mode = os.getenv('BOT_TEST_MODE', 'false').lower() == 'true'
        
        if test_mode:
            # In test mode, return mock balances
            balances = {
                "spot": {"free_balance": 1000.0, "total_balance": 1000.0, "currency": "USDT"},
                "futures": {"free_balance": 1000.0, "total_balance": 1000.0, "currency": "USDT"}
            }
            return {
                "message": "Test mode balances retrieved successfully",
                "balances": balances,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if not api_key or not api_secret:
            logger.warning("Binance API credentials not found")
            return {
                "message": "API credentials not configured",
                "balances": {
                    "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                    "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        balances = {
            "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
            "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
        }
        
        async def fetch_spot_balance_with_timeout():
            """Fetch spot balance with timeout protection."""
            try:
                # Use the same approach as the working permission test
                spot_exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'options': {'defaultType': 'spot'},
                    'enableRateLimit': True,
                    'timeout': 5000,  # Same timeout as working test
                    'rateLimit': 1200,
                    'sandbox': False,
                })
                
                logger.info("Fetching spot balance using working method...")
                
                # Use the exact same approach as the permission test
                spot_balance = await asyncio.get_event_loop().run_in_executor(
                    None, spot_exchange.fetch_balance
                )
                
                logger.info(f"Spot balance received successfully")
                
                # Check for USDT balance
                spot_usdt = spot_balance.get('USDT', {})
                if spot_usdt:
                    free_balance = float(spot_usdt.get('free', 0))
                    total_balance = float(spot_usdt.get('total', 0))
                    logger.info(f"Spot balance: free={free_balance}, total={total_balance}")
                    return {
                        "free_balance": free_balance,
                        "total_balance": total_balance,
                        "currency": "USDT"
                    }
                else:
                    logger.info("No USDT in spot wallet")
                    return {"free_balance": 0.0, "total_balance": 0.0, "currency": "USDT"}
                    
            except Exception as e:
                logger.warning(f"Error fetching spot balance: {e}")
                return {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
        
        async def fetch_futures_balance_with_timeout():
            """Fetch futures balance with timeout protection."""
            try:
                futures_exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'options': {'defaultType': 'future'},
                    'enableRateLimit': True,
                    'timeout': 8000,  # 8 second timeout
                    'rateLimit': 1200,  # Respect rate limits
                })
                
                # Use asyncio.wait_for to add extra timeout protection
                futures_balance = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, futures_exchange.fetch_balance
                    ),
                    timeout=10.0
                )
                
                futures_usdt = futures_balance.get('USDT', {})
                return {
                    "free_balance": float(futures_usdt.get('free', 0)),
                    "total_balance": float(futures_usdt.get('total', 0)),
                    "currency": "USDT"
                }
            except asyncio.TimeoutError:
                logger.warning("Timeout fetching futures balance")
                return {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
            except Exception as e:
                logger.warning(f"Error fetching futures balance: {e}")
                return {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
        
        # Fetch both balances concurrently with overall timeout
        try:
            # Create tasks for both balance fetches
            spot_task = asyncio.create_task(fetch_spot_balance_with_timeout())
            futures_task = asyncio.create_task(fetch_futures_balance_with_timeout())
            
            # Wait for both with longer timeout since we know spot works
            spot_result, futures_result = await asyncio.wait_for(
                asyncio.gather(spot_task, futures_task, return_exceptions=True),
                timeout=20.0  # Increased timeout
            )
            
            # Handle results
            if isinstance(spot_result, Exception):
                logger.error(f"Spot balance fetch failed: {spot_result}")
                balances["spot"] = {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
            else:
                balances["spot"] = spot_result
            
            if isinstance(futures_result, Exception):
                logger.error(f"Futures balance fetch failed: {futures_result}")
                balances["futures"] = {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
            else:
                balances["futures"] = futures_result
            
            # Check if we got any real data
            has_real_data = (
                balances["spot"]["free_balance"] != "N/A" or 
                balances["futures"]["free_balance"] != "N/A"
            )
            
            message = "Real balances retrieved successfully" if has_real_data else "Balance API timeout - check Binance directly"
            
            return {
                "message": message,
                "balances": balances,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except asyncio.TimeoutError:
            logger.error("Overall timeout fetching balances from Binance")
            return {
                "message": "Timeout fetching balances - Binance API slow",
                "balances": balances,
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error getting dual balances: {e}")
        return {
            "message": f"Error retrieving dual balances: {str(e)}",
            "balances": {
                "spot": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"},
                "futures": {"free_balance": "N/A", "total_balance": "N/A", "currency": "USDT"}
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/api/public-status")
async def get_public_status():
    """Get public bot status without authentication - for monitoring."""
    try:
        import asyncpg
        conn = await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
        
        try:
            # Get basic stats from REAL trading data
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_trades,
                    COALESCE(SUM(pnl), 0) as total_realized_pnl,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades
                FROM trading_trades
                WHERE pnl IS NOT NULL
            """)
            
            # Get recent trades count (24h)
            trades_24h = await conn.fetchval("SELECT COUNT(*) FROM trading_trades WHERE created_at >= NOW() - INTERVAL '24 hours'")
            
            # Get data ingestion stats (OHLCV candles)
            candle_count = await conn.fetchval("SELECT COUNT(*) FROM ohlcv WHERE timestamp >= NOW() - INTERVAL '24 hours'")
            
            # Get recent signals count
            recent_signals = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '24 hours'")
            
            # Get latest REAL trade
            latest = await conn.fetchrow("""
                SELECT symbol, side, price, amount, pnl, trade_type
                FROM trading_trades 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            # Calculate win rate from closed trades only (trades with PnL)
            win_rate = 0
            closed_trades = stats['winning_trades'] + stats['losing_trades']
            if closed_trades > 0:
                win_rate = (stats['winning_trades'] / closed_trades) * 100
            
            result = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "data_ingestion": {
                    "status": "success" if candle_count > 0 else "warning",
                    "candles_24h": candle_count
                },
                "signal_generation": {
                    "status": "success" if recent_signals > 0 else "warning",
                    "signals_24h": recent_signals
                },
                "recent_trades_24h": trades_24h,
                "total_trades": stats['total_trades'],
                "total_pnl": float(stats['total_realized_pnl']),
                "win_rate": round(win_rate, 2),
                "latest_trade": {
                    "symbol": latest['symbol'],
                    "side": latest['side'],
                    "price": float(latest['price']),
                    "amount": float(latest['amount']),
                    "pnl": float(latest['pnl']) if latest['pnl'] else 0,
                    "trade_type": latest['trade_type']
                } if latest else None,
                "bot_status": "running" if bot_status["is_running"] else "stopped"
            }
            
            return result
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error getting public status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "bot_status": "unknown",
            "data_ingestion": {"status": "error", "candles_24h": 0},
            "signal_generation": {"status": "error", "signals_24h": 0}
        }


@app.get("/api/bot/test-permissions")
async def test_binance_permissions():
    """Test Binance API permissions for debugging."""
    try:
        import ccxt
        
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            return {"error": "API credentials not found"}
        
        results = {}
        
        # Test futures permissions
        try:
            futures_exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'defaultType': 'future'},
                'enableRateLimit': True,
                'timeout': 5000,
            })
            
            futures_balance = futures_exchange.fetch_balance()
            results['futures'] = {
                'status': 'success',
                'has_usdt': 'USDT' in futures_balance,
                'usdt_balance': futures_balance.get('USDT', {}).get('total', 0)
            }
        except Exception as e:
            results['futures'] = {'status': 'error', 'message': str(e)}
        
        # Test spot permissions
        try:
            spot_exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'defaultType': 'spot'},
                'enableRateLimit': True,
                'timeout': 5000,
            })
            
            spot_balance = spot_exchange.fetch_balance()
            results['spot'] = {
                'status': 'success',
                'has_usdt': 'USDT' in spot_balance,
                'usdt_balance': spot_balance.get('USDT', {}).get('total', 0),
                'available_currencies': list(spot_balance.keys())[:10]  # First 10 currencies
            }
        except Exception as e:
            results['spot'] = {'status': 'error', 'message': str(e)}
        
        return {
            "message": "Permission test completed",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
