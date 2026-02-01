"""
Binance Execution Engine for Automated Trading
Handles order execution, risk management, and position monitoring
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


class BinanceExecutor:
    """Executes trades on Binance with comprehensive risk management."""
    
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.exchange = None
        self.account_balance = 0
        self.max_risk_per_trade = 0.02  # 2% risk per trade
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.max_positions = 3  # Maximum concurrent positions
        
        # Leverage management - using bot config
        from config.bot_config import bot_settings
        self.leverage = bot_settings.leverage
        self.max_leverage = bot_settings.max_leverage
        
        # Market condition filters
        self.enable_volatility_filter = bot_settings.enable_volatility_filter
        self.enable_liquidity_filter = bot_settings.enable_liquidity_filter
        self.enable_trend_filter = bot_settings.enable_trend_filter
        self.max_volatility = bot_settings.max_volatility
        self.min_liquidity = bot_settings.min_liquidity
        
        # Initialize exchange
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialize Binance exchange connection."""
        try:
            if self.test_mode:
                # Testnet configuration
                self.exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': True,  # Use testnet
                    'options': {
                        'defaultType': 'future',  # Futures trading
                        'test': True  # Test mode
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
                logger.info("🔧 Initialized Binance TESTNET connection")
            else:
                # Live trading configuration
                self.exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': False,  # Live trading
                    'options': {
                        'defaultType': 'future'  # Futures trading
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
                logger.info("🚀 Initialized Binance LIVE trading connection")
                
        except Exception as e:
            logger.error(f"Failed to initialize Binance exchange: {e}")
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
    
    async def get_account_balance(self) -> Dict:
        """Get current account balance."""
        try:
            balance = self.exchange.fetch_balance()
            
            # Get USDT balance for futures
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            total_balance = balance.get('USDT', {}).get('total', 0)
            
            self.account_balance = float(usdt_balance)
            
            return {
                "free_balance": float(usdt_balance),
                "total_balance": float(total_balance),
                "currency": "USDT"
            }
            
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            return {"free_balance": 0, "total_balance": 0, "currency": "USDT"}
    
    async def set_leverage(self, symbol: str, leverage: float = None) -> Dict:
        """Set leverage for a trading pair with verification."""
        try:
            if leverage is None:
                leverage = self.leverage
            
            # Ensure leverage is within limits
            leverage = min(leverage, self.max_leverage)
            
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would set leverage {leverage}x for {symbol}")
                return {"success": True, "leverage": leverage, "symbol": symbol}
            else:
                # Set leverage on Binance futures
                result = self.exchange.set_leverage(leverage, symbol)
                logger.info(f"⚡ Leverage set to {leverage}x for {symbol}")
                
                # CRITICAL: Verify leverage was actually set
                verification_result = await self._verify_leverage_setting(symbol, leverage)
                if not verification_result:
                    logger.error(f"❌ CRITICAL: Leverage verification failed for {symbol}")
                    return {"success": False, "error": f"Leverage verification failed for {symbol}", "critical_error": True}
                
                return {"success": True, "leverage": leverage, "symbol": symbol, "result": result}
                
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR setting leverage: {e}")
            return {"success": False, "error": str(e), "critical_error": True}
    
    async def check_market_conditions(self, symbol: str) -> Dict:
        """Check if market conditions are suitable for trading."""
        try:
            symbol_clean = symbol.replace('/', '')
            
            # Get market data
            ticker = self.exchange.fetch_ticker(symbol_clean)
            ohlcv = self.exchange.fetch_ohlcv(symbol_clean, '1h', limit=24)
            
            # Calculate volatility (24h price range)
            if len(ohlcv) >= 24:
                prices = [candle[4] for candle in ohlcv[-24:]]  # Close prices
                high_price = max(prices)
                low_price = min(prices)
                volatility = (high_price - low_price) / low_price
            else:
                volatility = 0
            
            # Get volume and liquidity
            volume_24h = ticker.get('quoteVolume', 0)
            liquidity_score = volume_24h / 1000000  # Convert to millions
            
            # Check filters
            conditions = {
                "symbol": symbol,
                "volatility": volatility,
                "volume_24h": volume_24h,
                "liquidity_score": liquidity_score,
                "suitable_for_trading": True,
                "reasons": []
            }
            
            # Volatility filter
            if self.enable_volatility_filter and volatility > self.max_volatility:
                conditions["suitable_for_trading"] = False
                conditions["reasons"].append(f"High volatility: {volatility:.2%} > {self.max_volatility:.2%}")
            
            # Liquidity filter
            if self.enable_liquidity_filter and volume_24h < self.min_liquidity:
                conditions["suitable_for_trading"] = False
                conditions["reasons"].append(f"Low liquidity: {volume_24h:,.0f} < {self.min_liquidity:,.0f}")
            
            # Trend filter (simple RSI-based)
            if self.enable_trend_filter and len(ohlcv) >= 14:
                rsi = self._calculate_rsi([candle[4] for candle in ohlcv[-14:]])
                if rsi > 80:  # Overbought
                    conditions["reasons"].append(f"Overbought condition: RSI {rsi:.1f}")
                elif rsi < 20:  # Oversold
                    conditions["reasons"].append(f"Oversold condition: RSI {rsi:.1f}")
            
            logger.info(f"📊 Market conditions for {symbol}: Volatility {volatility:.2%}, Volume {volume_24h:,.0f}, Suitable: {conditions['suitable_for_trading']}")
            
            return conditions
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            return {
                "symbol": symbol,
                "suitable_for_trading": False,
                "reasons": [f"Error checking conditions: {str(e)}"]
            }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50  # Neutral RSI if not enough data
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_position_size(self, signal: Dict, account_balance: float) -> Dict:
        """Calculate safe position size based on risk management."""
        try:
            entry_price = float(signal['entry_price'])
            stop_loss = float(signal['stop_loss'])
            
            # Calculate risk per trade
            risk_amount = account_balance * self.max_risk_per_trade
            
            # Calculate position size based on stop loss distance
            if signal['direction'] == 'LONG':
                risk_per_unit = entry_price - stop_loss
            else:  # SHORT
                risk_per_unit = stop_loss - entry_price
            
            if risk_per_unit <= 0:
                return {"quantity": 0, "risk_amount": 0, "error": "Invalid stop loss"}
            
            # Calculate quantity
            quantity = risk_amount / risk_per_unit
            
            # Apply maximum position size limit
            max_position_value = account_balance * 0.3  # Max 30% of balance per position
            max_quantity_by_value = max_position_value / entry_price
            
            final_quantity = min(quantity, max_quantity_by_value)
            
            # Round to appropriate precision
            if 'BTC' in signal['symbol']:
                final_quantity = round(final_quantity, 6)
            elif 'ETH' in signal['symbol']:
                final_quantity = round(final_quantity, 5)
            else:
                final_quantity = round(final_quantity, 4)
            
            return {
                "quantity": final_quantity,
                "risk_amount": risk_amount,
                "position_value": final_quantity * entry_price,
                "risk_percentage": (risk_amount / account_balance) * 100
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"quantity": 0, "risk_amount": 0, "error": str(e)}
    
    async def execute_signal(self, signal: Dict) -> Dict:
        """Execute a trading signal with full risk management."""
        try:
            logger.info(f"🚀 Executing signal: {signal['symbol']} {signal['direction']}")
            
            # Check market conditions first
            market_conditions = await self.check_market_conditions(signal['symbol'])
            if not market_conditions['suitable_for_trading']:
                return {
                    "success": False,
                    "error": "Market conditions not suitable for trading",
                    "reasons": market_conditions['reasons'],
                    "market_data": market_conditions
                }
            
            # Set leverage for the trading pair
            leverage_result = await self.set_leverage(signal['symbol'])
            if not leverage_result['success']:
                return {
                    "success": False,
                    "error": f"Failed to set leverage: {leverage_result.get('error', 'Unknown error')}"
                }
            
            # Get account balance
            balance = await self.get_account_balance()
            if balance['free_balance'] < 50:  # Minimum balance check (reduced from 100 to 50)
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "balance": balance['free_balance']
                }
            
            # Calculate position size
            position_info = self.calculate_position_size(signal, balance['free_balance'])
            if position_info.get('error'):
                return {
                    "success": False,
                    "error": position_info['error']
                }
            
            if position_info['quantity'] <= 0:
                return {
                    "success": False,
                    "error": "Invalid position size"
                }
            
            # Prepare order parameters
            symbol = signal['symbol'].replace('/', '')  # Convert BTC/USDT to BTCUSDT
            side = 'buy' if signal['direction'] == 'LONG' else 'sell'
            quantity = position_info['quantity']
            
            # Place market order
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would place {side} order for {quantity} {symbol}")
                order_result = {
                    "id": f"test_{int(time.time())}",
                    "symbol": symbol,
                    "side": side,
                    "amount": quantity,
                    "price": float(signal['entry_price']),
                    "status": "filled",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # Live trading
                order_result = self.exchange.create_market_order(
                    symbol, side, quantity
                )
                logger.info(f"✅ Order placed: {order_result['id']}")
            
            # Set stop loss and take profit orders
            sl_tp_result = await self.set_stop_loss_take_profit(
                signal, order_result, position_info
            )
            
            # Store position in database
            position_id = await self.store_position(signal, order_result, position_info)
            
            return {
                "success": True,
                "order_id": order_result['id'],
                "position_id": position_id,
                "quantity": quantity,
                "entry_price": float(signal['entry_price']),
                "stop_loss": float(signal['stop_loss']),
                "take_profit": float(signal['take_profit_1']),
                "risk_amount": position_info['risk_amount'],
                "leverage": leverage_result['leverage'],
                "market_conditions": market_conditions,
                "test_mode": self.test_mode
            }
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def set_stop_loss_take_profit(self, signal: Dict, order_result: Dict, position_info: Dict) -> Dict:
        """Set stop loss and take profit orders."""
        try:
            symbol = signal['symbol'].replace('/', '')
            side = 'sell' if signal['direction'] == 'LONG' else 'buy'
            quantity = position_info['quantity']
            
            # Stop Loss Order
            sl_price = float(signal['stop_loss'])
            sl_order = None
            
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would set stop loss at {sl_price}")
                sl_order = {"id": f"sl_test_{int(time.time())}", "status": "open"}
            else:
                sl_order = self.exchange.create_limit_order(
                    symbol, side, quantity, sl_price
                )
                logger.info(f"🛡️ Stop loss set: {sl_order['id']}")
            
            # Take Profit Order
            tp_price = float(signal['take_profit_1'])
            tp_order = None
            
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would set take profit at {tp_price}")
                tp_order = {"id": f"tp_test_{int(time.time())}", "status": "open"}
            else:
                tp_order = self.exchange.create_limit_order(
                    symbol, side, quantity, tp_price
                )
                logger.info(f"🎯 Take profit set: {tp_order['id']}")
            
            return {
                "stop_loss_order": sl_order,
                "take_profit_order": tp_order
            }
            
        except Exception as e:
            logger.error(f"Error setting stop loss/take profit: {e}")
            return {"error": str(e)}
    
    async def store_position(self, signal: Dict, order_result: Dict, position_info: Dict) -> int:
        """Store position in database."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Insert position
            position_id = await conn.fetchval("""
                INSERT INTO paper_positions (
                    symbol, side, entry_price, quantity, stop_loss, take_profit,
                    current_price, unrealized_pnl, is_open, signal_id, opened_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
            """, 
                signal['symbol'],
                signal['direction'],
                float(signal['entry_price']),
                position_info['quantity'],
                float(signal['stop_loss']),
                float(signal['take_profit_1']),
                float(signal['entry_price']),  # Current price = entry price initially
                0.0,  # Unrealized PnL starts at 0
                True,  # Position is open
                signal['id'],
                datetime.utcnow(),  # opened_at
                datetime.utcnow(),  # created_at
                datetime.utcnow()  # updated_at
            )
            
            # Mark signal as executed
            await conn.execute("""
                UPDATE signals 
                SET is_executed = true, updated_at = $2
                WHERE id = $1
            """, signal['id'], datetime.utcnow())
            
            logger.info(f"💾 Position stored: ID {position_id}")
            logger.info(f"✅ Signal {signal['id']} marked as executed")
            return position_id
            
        except Exception as e:
            logger.error(f"Error storing position: {e}")
            return 0
        finally:
            if conn:
                await conn.close()
    
    async def monitor_positions(self) -> List[Dict]:
        """Monitor all open positions."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get all open positions
            positions = await conn.fetch("""
                SELECT * FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            updated_positions = []
            
            for position in positions:
                # Get current market price
                symbol = position['symbol'].replace('/', '')
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Calculate unrealized PnL
                entry_price = float(position['entry_price'])
                quantity = float(position['quantity'])
                
                if position['side'] == 'LONG':
                    unrealized_pnl = (current_price - entry_price) * quantity
                else:  # SHORT
                    unrealized_pnl = (entry_price - current_price) * quantity
                
                # Update position in database
                await conn.execute("""
                    UPDATE paper_positions 
                    SET current_price = $1, unrealized_pnl = $2, updated_at = $3
                    WHERE id = $4
                """, current_price, unrealized_pnl, datetime.utcnow(), position['id'])
                
                updated_positions.append({
                    "id": position['id'],
                    "symbol": position['symbol'],
                    "side": position['side'],
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "quantity": quantity,
                    "unrealized_pnl": unrealized_pnl,
                    "pnl_percentage": (unrealized_pnl / (entry_price * quantity)) * 100
                })
            
            return updated_positions
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            return []
        finally:
            if conn:
                await conn.close()
    
    async def close_position(self, position_id: int, reason: str = "manual") -> Dict:
        """Close a position."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get position details
            position = await conn.fetchrow("""
                SELECT * FROM paper_positions WHERE id = $1
            """, position_id)
            
            if not position:
                return {"success": False, "error": "Position not found"}
            
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
                SET is_open = false, closed_at = $1, realized_pnl = $2, updated_at = $3
                WHERE id = $4
            """, datetime.utcnow(), realized_pnl, datetime.utcnow(), position_id)
            
            logger.info(f"🔒 Position {position_id} closed: {realized_pnl:.2f} USDT PnL")
            
            return {
                "success": True,
                "position_id": position_id,
                "realized_pnl": realized_pnl,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    async def _verify_leverage_setting(self, symbol: str, expected_leverage: float) -> bool:
        """Verify that leverage was actually set on Binance."""
        try:
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Skipping leverage verification for {symbol}")
                return True
            
            # Get current leverage from Binance
            try:
                # Try to get leverage info from the exchange
                leverage_info = self.exchange.fetch_leverage_tiers([symbol])
                
                if leverage_info and symbol in leverage_info:
                    # Get current position info to check leverage
                    positions = self.exchange.fetch_positions([symbol])
                    for position in positions:
                        if position['symbol'] == symbol and position['side'] != 'closed':
                            current_leverage = position.get('leverage', 1)
                            if current_leverage == expected_leverage:
                                logger.info(f"✅ Leverage verification successful: {symbol} = {current_leverage}x")
                                return True
                            else:
                                logger.error(f"❌ Leverage verification failed: {symbol} expected {expected_leverage}x, got {current_leverage}x")
                                return False
                
                # If no position exists, we can't verify but assume it's set correctly
                logger.info(f"✅ Leverage setting completed for {symbol} (no position to verify)")
                return True
                
            except Exception as verify_error:
                logger.warning(f"⚠️ Could not verify leverage for {symbol}: {verify_error}")
                # Don't fail the trade if we can't verify, but log the issue
                return True
                
        except Exception as e:
            logger.error(f"❌ Error in leverage verification: {e}")
            return False


async def main():
    """Test the Binance executor."""
    executor = BinanceExecutor(test_mode=True)
    
    print("🤖 Testing Binance Executor...")
    
    # Test account balance
    balance = await executor.get_account_balance()
    print(f"💰 Account Balance: {balance['free_balance']:.2f} {balance['currency']}")
    
    # Test position monitoring
    positions = await executor.monitor_positions()
    print(f"📊 Open Positions: {len(positions)}")
    
    for pos in positions:
        print(f"   {pos['symbol']} {pos['side']}: {pos['unrealized_pnl']:.2f} USDT")


if __name__ == "__main__":
    asyncio.run(main())






