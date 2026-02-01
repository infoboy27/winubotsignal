"""
Trading History Fetcher for Binance
Fetches PNL, closed orders, and trading statistics
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


class TradingHistoryFetcher:
    """Fetches trading history, PNL, and closed orders from Binance."""
    
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.spot_exchange = None
        self.futures_exchange = None
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize exchange connections."""
        try:
            if self.test_mode:
                # Testnet configuration
                self.spot_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': True,
                    'enableRateLimit': True,
                })
                
                self.futures_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': True,
                    'options': {'defaultType': 'future'},
                    'enableRateLimit': True,
                })
                logger.info("🔧 Initialized TESTNET connections for trading history")
            else:
                # Live trading configuration
                self.spot_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': False,
                    'enableRateLimit': True,
                })
                
                self.futures_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': False,
                    'options': {'defaultType': 'future'},
                    'enableRateLimit': True,
                })
                logger.info("🚀 Initialized LIVE connections for trading history")
                
        except Exception as e:
            logger.error(f"Failed to initialize exchanges for trading history: {e}")
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
    
    async def get_futures_pnl(self, days: int = 7) -> Dict:
        """Get futures trading PNL from Binance."""
        try:
            if not self.futures_exchange:
                return {"error": "Futures exchange not initialized"}
            
            # Get account info to calculate PNL
            account = await self.futures_exchange.fetch_balance()
            
            # Get recent trades (closed orders)
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            trades = await self.futures_exchange.fetch_my_trades(since=since, limit=1000)
            
            # Calculate PNL from trades
            total_pnl = 0.0
            winning_trades = 0
            losing_trades = 0
            total_trades = len(trades)
            
            trade_details = []
            
            for trade in trades:
                if trade['side'] == 'sell':  # Only count sell trades for PNL
                    pnl = trade['amount'] * trade['price'] - (trade['cost'] or 0)
                    total_pnl += pnl
                    
                    if pnl > 0:
                        winning_trades += 1
                    elif pnl < 0:
                        losing_trades += 1
                    
                    trade_details.append({
                        'id': trade['id'],
                        'symbol': trade['symbol'],
                        'side': trade['side'],
                        'amount': trade['amount'],
                        'price': trade['price'],
                        'cost': trade['cost'],
                        'pnl': pnl,
                        'timestamp': trade['timestamp'],
                        'datetime': trade['datetime']
                    })
            
            # Get current positions
            positions = await self.futures_exchange.fetch_positions()
            open_positions = [pos for pos in positions if pos['contracts'] > 0]
            
            # Calculate unrealized PNL
            unrealized_pnl = sum(pos['unrealizedPnl'] or 0 for pos in open_positions)
            
            return {
                'total_pnl': total_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                'open_positions': len(open_positions),
                'trades': trade_details[-20:],  # Last 20 trades
                'account_balance': account['USDT']['total'] if 'USDT' in account else 0,
                'days_period': days
            }
            
        except Exception as e:
            logger.error(f"Error fetching futures PNL: {e}")
            return {"error": str(e)}
    
    async def get_spot_trades(self, days: int = 7) -> Dict:
        """Get spot trading history from Binance."""
        try:
            if not self.spot_exchange:
                return {"error": "Spot exchange not initialized"}
            
            # Get recent trades
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            trades = await self.spot_exchange.fetch_my_trades(since=since, limit=1000)
            
            # Calculate statistics
            total_trades = len(trades)
            total_volume = sum(trade['amount'] * trade['price'] for trade in trades)
            
            trade_details = []
            for trade in trades:
                trade_details.append({
                    'id': trade['id'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'amount': trade['amount'],
                    'price': trade['price'],
                    'cost': trade['cost'],
                    'fee': trade['fee'],
                    'timestamp': trade['timestamp'],
                    'datetime': trade['datetime']
                })
            
            return {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'trades': trade_details[-20:],  # Last 20 trades
                'days_period': days
            }
            
        except Exception as e:
            logger.error(f"Error fetching spot trades: {e}")
            return {"error": str(e)}
    
    async def get_account_summary(self) -> Dict:
        """Get comprehensive account summary."""
        try:
            spot_balance = {}
            futures_balance = {}
            
            # Get spot balance
            if self.spot_exchange:
                spot_account = await self.spot_exchange.fetch_balance()
                spot_balance = {
                    'total': spot_account['total'],
                    'free': spot_account['free'],
                    'used': spot_account['used']
                }
            
            # Get futures balance
            if self.futures_exchange:
                futures_account = await self.futures_exchange.fetch_balance()
                futures_balance = {
                    'total': futures_account['total'],
                    'free': futures_account['free'],
                    'used': futures_account['used']
                }
            
            return {
                'spot': spot_balance,
                'futures': futures_balance,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching account summary: {e}")
            return {"error": str(e)}
    
    async def get_daily_pnl(self, days: int = 30) -> List[Dict]:
        """Get daily PNL breakdown."""
        try:
            if not self.futures_exchange:
                return []
            
            daily_pnl = []
            
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                since = int(date.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
                until = int(date.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)
                
                try:
                    trades = await self.futures_exchange.fetch_my_trades(since=since, limit=1000)
                    
                    day_pnl = 0.0
                    day_trades = 0
                    
                    for trade in trades:
                        if trade['side'] == 'sell':
                            pnl = trade['amount'] * trade['price'] - (trade['cost'] or 0)
                            day_pnl += pnl
                            day_trades += 1
                    
                    daily_pnl.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'pnl': day_pnl,
                        'trades': day_trades
                    })
                    
                except Exception as e:
                    logger.warning(f"Error fetching trades for {date.strftime('%Y-%m-%d')}: {e}")
                    daily_pnl.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'pnl': 0.0,
                        'trades': 0
                    })
                
                # Rate limiting
                await asyncio.sleep(0.1)
            
            return daily_pnl
            
        except Exception as e:
            logger.error(f"Error fetching daily PNL: {e}")
            return []












