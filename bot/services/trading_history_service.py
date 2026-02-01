"""
Trading History Service
Fetches trading history from Binance and stores it in the database
"""

import sys
import asyncio
import asyncpg
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import time

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class TradingHistoryService:
    """Service for fetching and storing trading history from Binance."""
    
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.spot_exchange = None
        self.futures_exchange = None
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize exchange connections."""
        try:
            # Always use production since we're trading on production
            self.spot_exchange = ccxt.binance({
                'apiKey': settings.exchange.binance_api_key,
                'secret': settings.exchange.binance_api_secret,
                'sandbox': False,  # Production mode
                'enableRateLimit': True,
            })
            
            self.futures_exchange = ccxt.binance({
                'apiKey': settings.exchange.binance_api_key,
                'secret': settings.exchange.binance_api_secret,
                'sandbox': False,  # Production mode
                'options': {'defaultType': 'future'},
                'enableRateLimit': True,
            })
            logger.info("🚀 Initialized PRODUCTION connections for trading history service")
                
        except Exception as e:
            logger.error(f"Failed to initialize exchanges for trading history service: {e}")
            raise
    
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def fetch_and_store_futures_trades(self, days: int = 7) -> Dict:
        """Fetch futures trades from Binance and store in database."""
        try:
            if not self.futures_exchange:
                return {"error": "Futures exchange not initialized"}
            
            conn = await self.connect_db()
            
            # Get recent trades - need to fetch for each symbol
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            all_trades = []
            
            # Get list of symbols from positions or use common trading pairs
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT', 'MATICUSDT', 'AVAXUSDT']
            
            for symbol in symbols:
                try:
                    # Try without time limit first to see if we get any trades
                    trades = self.futures_exchange.fetch_my_trades(symbol=symbol, limit=100)
                    logger.info(f"Fetched {len(trades)} futures trades for {symbol} (no time limit)")
                    
                    # Filter trades by time if we got any
                    if trades:
                        filtered_trades = [t for t in trades if t['timestamp'] >= since]
                        logger.info(f"Filtered to {len(filtered_trades)} trades within {days} days")
                        all_trades.extend(filtered_trades)
                    else:
                        all_trades.extend(trades)
                        
                except Exception as e:
                    logger.warning(f"Error fetching futures trades for {symbol}: {e}")
                    continue
            
            stored_count = 0
            skipped_count = 0
            
            for trade in all_trades:
                try:
                    # Check if trade already exists
                    existing = await conn.fetchrow(
                        "SELECT id FROM trading_trades WHERE binance_trade_id = $1",
                        str(trade['id'])
                    )
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Extract PNL from Binance futures trade info
                    pnl = None
                    if 'info' in trade and 'realizedPnl' in trade['info']:
                        try:
                            pnl = float(trade['info']['realizedPnl'])
                        except (ValueError, TypeError):
                            pnl = None
                    
                    # Insert trade into database
                    await conn.execute(
                        """
                        INSERT INTO trading_trades 
                        (binance_trade_id, symbol, side, amount, price, cost, fee, 
                         fee_currency, pnl, trade_type, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                        str(trade['id']),
                        trade['symbol'],
                        trade['side'],
                        trade['amount'],
                        trade['price'],
                        trade.get('cost'),
                        trade.get('fee', {}).get('cost'),
                        trade.get('fee', {}).get('currency'),
                        pnl,
                        'futures',
                        trade['timestamp']
                    )
                    
                    stored_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error storing trade {trade['id']}: {e}")
                    continue
            
            await conn.close()
            
            return {
                "success": True,
                "stored_trades": stored_count,
                "skipped_trades": skipped_count,
                "total_fetched": len(all_trades),
                "days_period": days
            }
            
        except Exception as e:
            logger.error(f"Error fetching and storing futures trades: {e}")
            return {"error": str(e)}
    
    async def fetch_and_store_spot_trades(self, days: int = 7) -> Dict:
        """Fetch spot trades from Binance and store in database."""
        try:
            if not self.spot_exchange:
                return {"error": "Spot exchange not initialized"}
            
            conn = await self.connect_db()
            
            # Get recent trades - need to fetch for each symbol
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            all_trades = []
            
            # Get list of symbols from positions or use common trading pairs
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT', 'MATICUSDT', 'AVAXUSDT']
            
            for symbol in symbols:
                try:
                    trades = self.spot_exchange.fetch_my_trades(symbol=symbol, since=since, limit=100)
                    all_trades.extend(trades)
                except Exception as e:
                    logger.warning(f"Error fetching spot trades for {symbol}: {e}")
                    continue
            
            stored_count = 0
            skipped_count = 0
            
            for trade in all_trades:
                try:
                    # Check if trade already exists
                    existing = await conn.fetchrow(
                        "SELECT id FROM trading_trades WHERE binance_trade_id = $1",
                        str(trade['id'])
                    )
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Insert trade into database
                    await conn.execute(
                        """
                        INSERT INTO trading_trades 
                        (binance_trade_id, symbol, side, amount, price, cost, fee, 
                         fee_currency, pnl, trade_type, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                        str(trade['id']),
                        trade['symbol'],
                        trade['side'],
                        trade['amount'],
                        trade['price'],
                        trade.get('cost'),
                        trade.get('fee', {}).get('cost'),
                        trade.get('fee', {}).get('currency'),
                        None,  # PNL not applicable for spot
                        'spot',
                        trade['timestamp']
                    )
                    
                    stored_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error storing spot trade {trade['id']}: {e}")
                    continue
            
            await conn.close()
            
            return {
                "success": True,
                "stored_trades": stored_count,
                "skipped_trades": skipped_count,
                "total_fetched": len(all_trades),
                "days_period": days
            }
            
        except Exception as e:
            logger.error(f"Error fetching and storing spot trades: {e}")
            return {"error": str(e)}
    
    async def store_account_balance(self) -> Dict:
        """Store current account balances."""
        try:
            conn = await self.connect_db()
            
            # Get spot balance
            if self.spot_exchange:
                try:
                    spot_account = self.spot_exchange.fetch_balance()
                    for currency, balance in spot_account['total'].items():
                        if balance > 0:  # Only store non-zero balances
                            await conn.execute(
                                """
                                INSERT INTO account_balance_history 
                                (account_type, currency, total_balance, free_balance, used_balance)
                                VALUES ($1, $2, $3, $4, $5)
                                """,
                                'spot',
                                currency,
                                balance,
                                spot_account['free'].get(currency, 0),
                                spot_account['used'].get(currency, 0)
                            )
                except Exception as e:
                    logger.warning(f"Error fetching spot balance: {e}")
            
            # Get futures balance
            if self.futures_exchange:
                try:
                    futures_account = self.futures_exchange.fetch_balance()
                    for currency, balance in futures_account['total'].items():
                        if balance > 0:  # Only store non-zero balances
                            await conn.execute(
                                """
                                INSERT INTO account_balance_history 
                                (account_type, currency, total_balance, free_balance, used_balance)
                                VALUES ($1, $2, $3, $4, $5)
                                """,
                                'futures',
                                currency,
                                balance,
                                futures_account['free'].get(currency, 0),
                                futures_account['used'].get(currency, 0)
                            )
                except Exception as e:
                    logger.warning(f"Error fetching futures balance: {e}")
            
            await conn.close()
            
            return {"success": True, "timestamp": datetime.now().isoformat()}
            
        except Exception as e:
            logger.error(f"Error storing account balance: {e}")
            return {"error": str(e)}
    
    async def calculate_spot_pnl(self) -> Dict:
        """Calculate PNL for spot trades by matching buy/sell pairs."""
        try:
            conn = await self.connect_db()
            
            # Get all spot trades ordered by symbol and timestamp
            trades = await conn.fetch(
                """
                SELECT * FROM trading_trades 
                WHERE trade_type = 'spot' 
                ORDER BY symbol, timestamp
                """
            )
            
            # Group trades by symbol and calculate PNL
            symbol_trades = {}
            for trade in trades:
                symbol = trade['symbol']
                if symbol not in symbol_trades:
                    symbol_trades[symbol] = {'buys': [], 'sells': []}
                
                # Convert record to dict for modification
                trade_dict = dict(trade)
                
                if trade['side'] == 'buy':
                    symbol_trades[symbol]['buys'].append(trade_dict)
                else:
                    symbol_trades[symbol]['sells'].append(trade_dict)
            
            # Calculate PNL for each symbol
            total_pnl = 0.0
            processed_trades = 0
            
            for symbol, trade_groups in symbol_trades.items():
                buys = trade_groups['buys']
                sells = trade_groups['sells']
                
                # Simple FIFO matching
                for sell_trade in sells:
                    remaining_amount = float(sell_trade['amount'])
                    
                    for buy_trade in buys:
                        if remaining_amount <= 0:
                            break
                        
                        if float(buy_trade['amount']) > 0:  # Still has unprocessed amount
                            # Calculate how much of this buy we're using
                            use_amount = min(remaining_amount, float(buy_trade['amount']))
                            
                            # Calculate PNL for this portion
                            buy_price = float(buy_trade['price'])
                            sell_price = float(sell_trade['price'])
                            pnl = (sell_price - buy_price) * float(use_amount)
                            
                            # Update the buy trade record with PNL
                            await conn.execute(
                                """
                                UPDATE trading_trades 
                                SET pnl = $1 
                                WHERE id = $2
                                """,
                                pnl, buy_trade['id']
                            )
                            
                            # Update the sell trade record with PNL
                            await conn.execute(
                                """
                                UPDATE trading_trades 
                                SET pnl = $1 
                                WHERE id = $2
                                """,
                                pnl, sell_trade['id']
                            )
                            
                            total_pnl += pnl
                            processed_trades += 1
                            
                            # Reduce the amounts
                            remaining_amount -= float(use_amount)
                            buy_trade['amount'] = float(buy_trade['amount']) - float(use_amount)
            
            await conn.close()
            
            return {
                "success": True,
                "total_pnl": total_pnl,
                "processed_trades": processed_trades
            }
            
        except Exception as e:
            logger.error(f"Error calculating spot PNL: {e}")
            return {"error": str(e)}

    async def calculate_daily_pnl(self, date: datetime = None) -> Dict:
        """Calculate and store daily PNL summary."""
        try:
            if date is None:
                date = datetime.now().date()
            
            conn = await self.connect_db()
            
            # Get all futures trades for the day
            start_timestamp = int(datetime.combine(date, datetime.min.time()).timestamp() * 1000)
            end_timestamp = int(datetime.combine(date, datetime.max.time()).timestamp() * 1000)
            
            trades = await conn.fetch(
                """
                SELECT * FROM trading_trades 
                WHERE trade_type = 'futures' 
                AND timestamp BETWEEN $1 AND $2
                ORDER BY timestamp
                """,
                start_timestamp, end_timestamp
            )
            
            # Calculate PNL and statistics
            total_pnl = 0.0
            winning_trades = 0
            losing_trades = 0
            total_volume = 0.0
            
            for trade in trades:
                if trade['pnl'] is not None:
                    total_pnl += trade['pnl']
                    if trade['pnl'] > 0:
                        winning_trades += 1
                    elif trade['pnl'] < 0:
                        losing_trades += 1
                
                total_volume += trade['amount'] * trade['price']
            
            total_trades = len(trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Store or update daily PNL summary
            await conn.execute(
                """
                INSERT INTO daily_pnl_summary 
                (date, total_pnl, realized_pnl, total_trades, winning_trades, losing_trades, win_rate, total_volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (date) DO UPDATE SET
                total_pnl = EXCLUDED.total_pnl,
                realized_pnl = EXCLUDED.realized_pnl,
                total_trades = EXCLUDED.total_trades,
                winning_trades = EXCLUDED.winning_trades,
                losing_trades = EXCLUDED.losing_trades,
                win_rate = EXCLUDED.win_rate,
                total_volume = EXCLUDED.total_volume,
                updated_at = NOW()
                """,
                date, total_pnl, total_pnl, total_trades, winning_trades, losing_trades, win_rate, total_volume
            )
            
            await conn.close()
            
            return {
                "success": True,
                "date": date.isoformat(),
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_volume": total_volume
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily PNL: {e}")
            return {"error": str(e)}
    
    async def get_stored_pnl_summary(self, days: int = 30) -> Dict:
        """Get PNL summary from stored data."""
        try:
            conn = await self.connect_db()
            
            # Get daily PNL summary
            daily_pnl = await conn.fetch(
                """
                SELECT * FROM daily_pnl_summary 
                WHERE date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY date DESC
                """,
                days
            )
            
            # Get recent trades
            recent_trades = await conn.fetch(
                """
                SELECT * FROM trading_trades 
                WHERE trade_type = 'futures' AND pnl IS NOT NULL
                ORDER BY timestamp DESC 
                LIMIT 50
                """
            )
            
            # Get current balances
            current_balances = await conn.fetch(
                """
                SELECT * FROM account_balance_history 
                WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                ORDER BY timestamp DESC
                """
            )
            
            # Calculate totals
            total_realized_pnl = sum(day['total_pnl'] for day in daily_pnl)
            total_trades = sum(day['total_trades'] for day in daily_pnl)
            total_winning = sum(day['winning_trades'] for day in daily_pnl)
            total_losing = sum(day['losing_trades'] for day in daily_pnl)
            overall_win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0
            
            await conn.close()
            
            return {
                "success": True,
                "summary": {
                    "total_realized_pnl": total_realized_pnl,
                    "total_trades": total_trades,
                    "winning_trades": total_winning,
                    "losing_trades": total_losing,
                    "overall_win_rate": overall_win_rate,
                    "days_analyzed": len(daily_pnl)
                },
                "daily_pnl": [dict(day) for day in daily_pnl],
                "recent_trades": [dict(trade) for trade in recent_trades],
                "current_balances": [dict(balance) for balance in current_balances]
            }
            
        except Exception as e:
            logger.error(f"Error getting stored PNL summary: {e}")
            return {"error": str(e)}
