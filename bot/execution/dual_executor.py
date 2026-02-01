"""
Dual Trading Executor for Spot and Futures
Handles both spot and futures trading with intelligent market selection
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
from config.bot_config import bot_settings

settings = get_settings()
logger = get_logger(__name__)


class DualTradingExecutor:
    """Executes trades on both spot and futures markets with intelligent selection."""
    
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.spot_exchange = None
        self.futures_exchange = None
        self.account_balance_spot = 0
        self.account_balance_futures = 0
        
        # Risk management
        self.max_risk_per_trade = 0.02  # 2% risk per trade
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.max_positions = 5  # Maximum concurrent positions
        
        # Dual trading settings
        self.enable_spot = bot_settings.enable_spot_trading
        self.enable_futures = bot_settings.enable_futures_trading
        self.default_trading_type = bot_settings.default_trading_type
        
        # Trading criteria
        self.spot_criteria = bot_settings.spot_trading_criteria
        self.futures_criteria = bot_settings.futures_trading_criteria
        
        # Initialize exchanges
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize both spot and futures exchanges."""
        try:
            if self.test_mode:
                # Spot exchange (testnet)
                self.spot_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': True,
                    'options': {
                        'defaultType': 'spot',  # Spot trading
                        'test': True
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
                
                # Futures exchange (testnet)
                self.futures_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': True,
                    'options': {
                        'defaultType': 'future',  # Futures trading
                        'test': True
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
                
                logger.info("🔧 Initialized dual TESTNET connections (Spot + Futures)")
            else:
                # Live trading - Spot
                self.spot_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': False,
                    'options': {
                        'defaultType': 'spot'
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
                
                # Live trading - Futures
                self.futures_exchange = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': False,
                    'options': {
                        'defaultType': 'future'
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
                
                logger.info("🚀 Initialized dual LIVE trading connections (Spot + Futures)")
                
        except Exception as e:
            logger.error(f"Failed to initialize exchanges: {e}")
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
    
    async def get_account_balances(self) -> Dict:
        """Get balances for both spot and futures."""
        try:
            balances = {}
            
            if self.enable_spot and self.spot_exchange:
                spot_balance = self.spot_exchange.fetch_balance()
                usdt_spot = spot_balance.get('USDT', {}).get('free', 0)
                balances['spot'] = {
                    "free_balance": float(usdt_spot),
                    "total_balance": float(spot_balance.get('USDT', {}).get('total', 0)),
                    "currency": "USDT"
                }
            
            if self.enable_futures and self.futures_exchange:
                futures_balance = self.futures_exchange.fetch_balance()
                usdt_futures = futures_balance.get('USDT', {}).get('free', 0)
                balances['futures'] = {
                    "free_balance": float(usdt_futures),
                    "total_balance": float(futures_balance.get('USDT', {}).get('total', 0)),
                    "currency": "USDT"
                }
            
            return balances
            
        except Exception as e:
            logger.error(f"Error fetching account balances: {e}")
            return {"spot": {"free_balance": 0}, "futures": {"free_balance": 0}}
    
    def analyze_signal_for_market_selection(self, signal: Dict) -> Dict:
        """Analyze signal to determine best market type (spot vs futures)."""
        try:
            signal_score = signal.get('quality_score', signal.get('signal_score', signal.get('score', 0.5)))
            volatility = self._calculate_signal_volatility(signal)
            timeframe = signal.get('timeframe', '1h')
            
            analysis = {
                "signal": signal,
                "signal_score": signal_score,
                "volatility": volatility,
                "timeframe": timeframe,
                "recommended_market": "none",
                "reasoning": [],
                "confidence": 0.0
            }
            
            # Check spot trading criteria
            spot_suitable = True
            spot_reasons = []
            
            if signal_score < self.spot_criteria["min_signal_score"]:
                spot_suitable = False
                spot_reasons.append(f"Signal score {signal_score:.2f} < {self.spot_criteria['min_signal_score']}")
            
            if volatility > self.spot_criteria["max_volatility"]:
                spot_suitable = False
                spot_reasons.append(f"Volatility {volatility:.2%} > {self.spot_criteria['max_volatility']:.2%}")
            
            # Check futures trading criteria
            futures_suitable = True
            futures_reasons = []
            
            if signal_score < self.futures_criteria["min_signal_score"]:
                futures_suitable = False
                futures_reasons.append(f"Signal score {signal_score:.2f} < {self.futures_criteria['min_signal_score']}")
            
            if volatility < self.futures_criteria["min_volatility"]:
                futures_suitable = False
                futures_reasons.append(f"Volatility {volatility:.2%} < {self.futures_criteria['min_volatility']:.2%}")
            
            # Decision logic - Prioritize futures for high-confidence signals
            if spot_suitable and futures_suitable:
                # Both suitable - prioritize futures for high-confidence signals
                if signal_score >= 0.8 and volatility >= 0.03:  # High confidence + any volatility >= 3% = futures
                    analysis["recommended_market"] = "futures"
                    analysis["reasoning"].append("High confidence + sufficient volatility = futures trading")
                    analysis["confidence"] = 0.9
                elif signal_score >= 0.8 and volatility < 0.03:  # Only very low volatility for spot with high confidence
                    analysis["recommended_market"] = "spot"
                    analysis["reasoning"].append("High confidence + very low volatility = spot trading")
                    analysis["confidence"] = 0.9
                elif signal_score >= 0.7 and volatility >= 0.03:
                    analysis["recommended_market"] = "futures"
                    analysis["reasoning"].append("Good confidence + sufficient volatility = futures trading")
                    analysis["confidence"] = 0.8
                else:
                    analysis["recommended_market"] = "futures"  # Default to futures for medium signals
                    analysis["reasoning"].append("Medium signal characteristics = futures trading")
                    analysis["confidence"] = 0.7
            elif spot_suitable:
                analysis["recommended_market"] = "spot"
                analysis["reasoning"].append("Signal meets spot criteria only")
                analysis["reasoning"].extend(spot_reasons)
                analysis["confidence"] = 0.8
            elif futures_suitable:
                analysis["recommended_market"] = "futures"
                analysis["reasoning"].append("Signal meets futures criteria only")
                analysis["reasoning"].extend(futures_reasons)
                analysis["confidence"] = 0.7
            else:
                analysis["recommended_market"] = "none"
                analysis["reasoning"].append("Signal doesn't meet criteria for either market")
                analysis["reasoning"].extend(spot_reasons)
                analysis["reasoning"].extend(futures_reasons)
                analysis["confidence"] = 0.0
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing signal: {e}")
            return {
                "signal": signal,
                "recommended_market": "none",
                "reasoning": [f"Analysis error: {str(e)}"],
                "confidence": 0.0
            }
    
    def _calculate_signal_volatility(self, signal: Dict) -> float:
        """Calculate volatility from signal data."""
        try:
            entry_price = float(signal.get('entry_price', 0))
            stop_loss = float(signal.get('stop_loss', 0))
            take_profit = float(signal.get('take_profit_1', 0))
            
            if entry_price <= 0:
                return 0.0
            
            # Calculate price range as volatility proxy
            price_range = max(take_profit, stop_loss) - min(take_profit, stop_loss)
            volatility = price_range / entry_price
            
            return min(volatility, 0.5)  # Cap at 50%
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.1  # Default moderate volatility
    
    async def _is_duplicate_signal(self, signal: Dict) -> bool:
        """Check if we already have a signal for this pair today."""
        try:
            if not bot_settings.enable_duplicate_prevention:
                return False
                
            conn = await self.connect_db()
            symbol = signal['symbol']
            
            # Check if we already executed a signal for this pair today
            today = datetime.utcnow().date()
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count 
                FROM signals 
                WHERE symbol = $1 
                AND DATE(created_at) = $2 
                AND is_executed = true
            """, symbol, today)
            
            await conn.close()
            
            if result and result['count'] >= bot_settings.max_signals_per_pair_per_day:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate signals: {e}")
            return False  # Allow signal if check fails
    
    def _meets_quality_threshold(self, signal: Dict) -> bool:
        """Check if signal meets minimum quality requirements."""
        try:
            signal_score = signal.get('quality_score', signal.get('signal_score', signal.get('score', 0.0)))
            
            # Check minimum score
            if signal_score < bot_settings.min_signal_score:
                logger.info(f"Signal score {signal_score:.2f} below minimum {bot_settings.min_signal_score}")
                return False
            
            # Check timeframe
            timeframe = signal.get('timeframe', '1h')
            min_timeframe = bot_settings.spot_trading_criteria.get('min_timeframe', '4h')
            
            # Convert timeframes to hours for comparison
            timeframe_hours = self._timeframe_to_hours(timeframe)
            min_hours = self._timeframe_to_hours(min_timeframe)
            
            if timeframe_hours < min_hours:
                logger.info(f"Timeframe {timeframe} below minimum {min_timeframe}")
                return False
            
            # Check volatility
            volatility = self._calculate_signal_volatility(signal)
            max_vol = bot_settings.max_volatility
            
            if volatility > max_vol:
                logger.info(f"Volatility {volatility:.3f} above maximum {max_vol}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal quality: {e}")
            return False
    
    def _timeframe_to_hours(self, timeframe: str) -> int:
        """Convert timeframe string to hours."""
        timeframe_map = {
            '1m': 0.017, '5m': 0.083, '15m': 0.25, '30m': 0.5,
            '1h': 1, '2h': 2, '4h': 4, '6h': 6, '8h': 8, '12h': 12,
            '1d': 24, '3d': 72, '1w': 168
        }
        return timeframe_map.get(timeframe, 1)
    
    async def execute_signal(self, signal: Dict) -> Dict:
        """Execute signal with intelligent market selection and duplicate prevention."""
        try:
            logger.info(f"🚀 Analyzing signal: {signal['symbol']} {signal['direction']}")
            
            # Check for duplicate signals for same pair
            if await self._is_duplicate_signal(signal):
                logger.warning(f"⚠️ Duplicate signal detected for {signal['symbol']} - skipping")
                return {
                    "success": False,
                    "error": "Duplicate signal for same pair - only one signal per pair per day allowed",
                    "analysis": {"recommended_market": "none", "confidence": 0.0, "reasoning": ["Duplicate prevention"]}
                }
            
            # Check signal quality before analysis
            if not self._meets_quality_threshold(signal):
                logger.warning(f"⚠️ Signal quality too low for {signal['symbol']} - skipping")
                return {
                    "success": False,
                    "error": "Signal quality below minimum threshold",
                    "analysis": {"recommended_market": "none", "confidence": 0.0, "reasoning": ["Quality threshold"]}
                }
            
            # Analyze signal for market selection
            analysis = self.analyze_signal_for_market_selection(signal)
            
            if analysis["recommended_market"] == "none":
                return {
                    "success": False,
                    "error": "Signal not suitable for any market",
                    "analysis": analysis
                }
            
            recommended_market = analysis["recommended_market"]
            logger.info(f"📊 Recommended market: {recommended_market.upper()} (confidence: {analysis['confidence']:.1%})")
            
            # Execute based on recommended market
            if recommended_market == "spot":
                return await self._execute_spot_trade(signal, analysis)
            elif recommended_market == "futures":
                return await self._execute_futures_trade(signal, analysis)
            else:
                return {
                    "success": False,
                    "error": f"Unknown market type: {recommended_market}",
                    "analysis": analysis
                }
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_spot_trade(self, signal: Dict, analysis: Dict) -> Dict:
        """Execute spot trade."""
        try:
            logger.info(f"💰 Executing SPOT trade: {signal['symbol']}")
            
            # Get spot balance
            balances = await self.get_account_balances()
            spot_balance = balances.get('spot', {}).get('free_balance', 0)
            
            if spot_balance < 50:  # Minimum spot balance
                return {
                    "success": False,
                    "error": "Insufficient spot balance",
                    "balance": spot_balance,
                    "market": "spot"
                }
            
            # Calculate position size (no leverage for spot)
            position_size = self._calculate_spot_position_size(signal, spot_balance)
            
            if position_size <= 0:
                return {
                    "success": False,
                    "error": "Invalid position size",
                    "market": "spot"
                }
            
            # Execute spot order
            symbol = signal['symbol'].replace('/', '')
            side = 'buy' if signal['direction'] == 'LONG' else 'sell'
            
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would place SPOT {side} order for {position_size} {symbol}")
                order_result = {
                    "id": f"spot_test_{int(time.time())}",
                    "symbol": symbol,
                    "side": side,
                    "amount": position_size,
                    "price": float(signal['entry_price']),
                    "status": "filled",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                logger.info(f"🚀 Placing LIVE SPOT {side} order for {position_size} {symbol}")
                try:
                    order_result = self.spot_exchange.create_market_order(symbol, side, position_size)
                    logger.info(f"✅ SPOT order placed successfully: {order_result['id']}")
                except Exception as e:
                    logger.error(f"❌ Failed to place SPOT order: {e}")
                    return {
                        "success": False,
                        "error": f"Order placement failed: {str(e)}",
                        "market": "spot"
                    }
            
            # Store position
            position_id = await self._store_position(signal, order_result, position_size, "spot")
            
            return {
                "success": True,
                "market": "spot",
                "order_id": order_result['id'],
                "position_id": position_id,
                "quantity": position_size,
                "entry_price": float(signal['entry_price']),
                "analysis": analysis,
                "test_mode": self.test_mode
            }
            
        except Exception as e:
            logger.error(f"Error executing spot trade: {e}")
            return {"success": False, "error": str(e), "market": "spot"}
    
    async def _execute_futures_trade(self, signal: Dict, analysis: Dict) -> Dict:
        """Execute futures trade."""
        try:
            logger.info(f"⚡ Executing FUTURES trade: {signal['symbol']}")
            
            # Get futures balance
            balances = await self.get_account_balances()
            futures_balance = balances.get('futures', {}).get('free_balance', 0)
            
            if futures_balance < 50:  # Minimum futures balance
                return {
                    "success": False,
                    "error": "Insufficient futures balance",
                    "balance": futures_balance,
                    "market": "futures"
                }
            
            # Set leverage
            leverage = min(bot_settings.leverage, bot_settings.max_leverage)
            # Keep symbol in CCXT format (DOGE/USDT) for set_leverage
            leverage_symbol = signal['symbol']
            # For order placement, we need the Binance format (DOGEUSDT)
            order_symbol = signal['symbol'].replace('/', '')
            
            try:
                if not self.test_mode:
                    # Set leverage on Binance futures using ccxt method (needs DOGE/USDT format)
                    logger.info(f"🔧 Setting leverage: {leverage} (type: {type(leverage)}) for {leverage_symbol}")
                    # Ensure leverage is an integer
                    leverage_int = int(leverage)
                    result = self.futures_exchange.set_leverage(leverage_int, leverage_symbol)
                    logger.info(f"⚡ Leverage set to {leverage_int}x for {leverage_symbol}")
                    
                    # CRITICAL: Verify leverage was actually set
                    await self._verify_leverage_setting(order_symbol, leverage)
                    
                else:
                    logger.info(f"🧪 TEST MODE: Would set leverage {leverage}x for {leverage_symbol}")
            except Exception as e:
                logger.error(f"❌ CRITICAL ERROR setting leverage: {e}")
                # STOP trading if leverage cannot be set - this is a critical risk management issue
                return {
                    "success": False,
                    "error": f"Failed to set leverage {leverage}x for {leverage_symbol}: {str(e)}",
                    "market": "futures",
                    "critical_error": True
                }
            
            # Calculate position size (with leverage)
            position_size = self._calculate_futures_position_size(signal, futures_balance, leverage)
            
            if position_size <= 0:
                return {
                    "success": False,
                    "error": "Invalid position size",
                    "market": "futures"
                }
            
            # Execute futures order
            side = 'buy' if signal['direction'] == 'LONG' else 'sell'
            
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would place FUTURES {side} order for {position_size} {leverage_symbol} at {leverage}x")
                order_result = {
                    "id": f"futures_test_{int(time.time())}",
                    "symbol": leverage_symbol,
                    "side": side,
                    "amount": position_size,
                    "price": float(signal['entry_price']),
                    "status": "filled",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                logger.info(f"🚀 Placing LIVE FUTURES {side} order for {position_size} {leverage_symbol} at {leverage}x leverage")
                try:
                    order_result = self.futures_exchange.create_market_order(leverage_symbol, side, position_size)
                    logger.info(f"✅ FUTURES order placed successfully: {order_result['id']}")
                except Exception as e:
                    logger.error(f"❌ Failed to place FUTURES order: {e}")
                    return {
                        "success": False,
                        "error": f"Order placement failed: {str(e)}",
                        "market": "futures"
                    }
            
            # Set stop loss and take profit (DISABLED - Manual management)
            # await self._set_futures_sl_tp(signal, order_result, position_size)
            logger.info(f"⚠️ Auto SL/TP disabled - manage manually on Binance")
            
            # Store position
            position_id = await self._store_position(signal, order_result, position_size, "futures")
            
            return {
                "success": True,
                "market": "futures",
                "order_id": order_result['id'],
                "position_id": position_id,
                "quantity": position_size,
                "entry_price": float(signal['entry_price']),
                "leverage": leverage,
                "analysis": analysis,
                "test_mode": self.test_mode
            }
            
        except Exception as e:
            logger.error(f"Error executing futures trade: {e}")
            return {"success": False, "error": str(e), "market": "futures"}
    
    def _calculate_spot_position_size(self, signal: Dict, balance: float) -> float:
        """Calculate position size for spot trading (no leverage)."""
        try:
            entry_price = float(signal['entry_price'])
            risk_amount = balance * self.max_risk_per_trade
            
            # For spot, use a conservative approach
            max_position_value = balance * 0.5  # Max 50% of balance for spot
            position_value = min(risk_amount * 10, max_position_value)  # 10x risk for spot
            
            quantity = position_value / entry_price
            
            # Round to appropriate precision
            if 'BTC' in signal['symbol']:
                return round(quantity, 6)
            elif 'ETH' in signal['symbol']:
                return round(quantity, 5)
            else:
                return round(quantity, 4)
                
        except Exception as e:
            logger.error(f"Error calculating spot position size: {e}")
            return 0.0
    
    def _calculate_futures_position_size(self, signal: Dict, balance: float, leverage: float) -> float:
        """Calculate position size for futures trading (with leverage)."""
        try:
            entry_price = float(signal['entry_price'])
            stop_loss = float(signal['stop_loss'])
            
            # Calculate risk per trade
            risk_amount = balance * self.max_risk_per_trade
            
            # Calculate stop loss distance
            if signal['direction'] == 'LONG':
                risk_per_unit = entry_price - stop_loss
            else:  # SHORT
                risk_per_unit = stop_loss - entry_price
            
            if risk_per_unit <= 0:
                return 0.0
            
            # Calculate quantity with leverage
            quantity = (risk_amount * leverage) / risk_per_unit
            
            # Apply maximum position size limit
            max_position_value = balance * 0.3 * leverage  # Max 30% with leverage
            max_quantity_by_value = max_position_value / entry_price
            
            final_quantity = min(quantity, max_quantity_by_value)
            
            # Ensure minimum position size for BTC (0.001 BTC minimum)
            if 'BTC' in signal['symbol']:
                final_quantity = max(final_quantity, 0.001)  # Minimum 0.001 BTC
                return round(final_quantity, 6)
            elif 'ETH' in signal['symbol']:
                return round(final_quantity, 5)
            else:
                return round(final_quantity, 4)
                
        except Exception as e:
            logger.error(f"Error calculating futures position size: {e}")
            return 0.0
    
    async def _set_futures_sl_tp(self, signal: Dict, order_result: Dict, quantity: float) -> Dict:
        """Set stop loss and take profit for futures."""
        try:
            symbol = signal['symbol'].replace('/', '')
            side = 'sell' if signal['direction'] == 'LONG' else 'buy'
            
            # Stop Loss
            sl_price = float(signal['stop_loss'])
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would set futures stop loss at {sl_price}")
            else:
                self.futures_exchange.create_limit_order(symbol, side, quantity, sl_price)
                logger.info(f"🛡️ Futures stop loss set: {sl_price}")
            
            # Take Profit
            tp_price = float(signal['take_profit_1'])
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would set futures take profit at {tp_price}")
            else:
                self.futures_exchange.create_limit_order(symbol, side, quantity, tp_price)
                logger.info(f"🎯 Futures take profit set: {tp_price}")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error setting futures SL/TP: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_position(self, signal: Dict, order_result: Dict, quantity: float, market_type: str) -> int:
        """Store position in database."""
        conn = None
        try:
            conn = await self.connect_db()
            
            position_id = await conn.fetchval("""
                INSERT INTO paper_positions (
                    symbol, side, entry_price, quantity, stop_loss, take_profit,
                    current_price, unrealized_pnl, is_open, signal_id, 
                    market_type, opened_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
            """, 
                signal['symbol'],
                signal['direction'],
                float(signal['entry_price']),
                quantity,
                float(signal['stop_loss']),
                float(signal['take_profit_1']),
                float(signal['entry_price']),
                0.0,
                True,
                signal['id'],
                market_type,  # spot or futures
                datetime.utcnow(),
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            # Mark signal as executed
            await conn.execute("""
                UPDATE signals 
                SET is_executed = true, updated_at = $2
                WHERE id = $1
            """, signal['id'], datetime.utcnow())
            
            logger.info(f"💾 {market_type.upper()} position stored: ID {position_id}")
            logger.info(f"✅ Signal {signal['id']} marked as executed")
            return position_id
            
        except Exception as e:
            logger.error(f"Error storing position: {e}")
            return 0
        finally:
            if conn:
                await conn.close()

    async def get_account_balance(self) -> Dict:
        """Get account balance (for compatibility with trading bot)."""
        balances = await self.get_account_balances()
        # Return futures balance as default for compatibility
        return balances.get("futures", {"free_balance": 0, "total_balance": 0, "currency": "USDT"})
    
    async def monitor_positions(self) -> List[Dict]:
        """Monitor all positions (spot and futures)."""
        positions = []
        
        try:
            # Get positions from database first (more reliable)
            conn = await self.connect_db()
            db_positions = await conn.fetch("""
                SELECT id, symbol, side, entry_price, quantity, stop_loss, take_profit,
                       current_price, unrealized_pnl, market_type, created_at, updated_at
                FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            for pos in db_positions:
                # Get current market price
                try:
                    symbol_clean = pos['symbol'].replace('/', '')
                    ticker = self.futures_exchange.fetch_ticker(symbol_clean) if self.futures_exchange else None
                    current_price = ticker['last'] if ticker else float(pos['current_price'])
                    
                    # Calculate unrealized PnL
                    entry_price = float(pos['entry_price'])
                    quantity = float(pos['quantity'])
                    
                    if pos['side'] == 'LONG':
                        unrealized_pnl = (current_price - entry_price) * quantity
                    else:  # SHORT
                        unrealized_pnl = (entry_price - current_price) * quantity
                    
                    # DISABLED: Automatic position closing based on SL/TP
                    # User requested manual management only - positions will stay open until manually closed
                    should_close = False
                    close_reason = ""
                    is_partial_close = False
                    
                    # Note: Automatic SL/TP monitoring is disabled
                    # Positions must be managed manually on the exchange
                    
                    # Handle partial take profit at 1.5% (DISABLED)
                    if False:  # is_partial_close - disabled
                        # Close 50% of position at 1.5% profit
                        partial_quantity = quantity * 0.5
                        partial_pnl = unrealized_pnl * 0.5
                        
                        # Close 50% on exchange first
                        if not self.test_mode:
                            try:
                                symbol = pos['symbol'].replace('/', '')
                                close_side = 'sell' if pos['side'] == 'LONG' else 'buy'
                                
                                if pos['market_type'] == 'futures':
                                    close_order = self.futures_exchange.create_market_order(
                                        symbol, close_side, partial_quantity
                                    )
                                    logger.info(f"💰 PARTIAL FUTURES close on Binance: {close_order['id']}")
                                else:
                                    close_order = self.spot_exchange.create_market_order(
                                        symbol, close_side, partial_quantity
                                    )
                                    logger.info(f"💰 PARTIAL SPOT close on Binance: {close_order['id']}")
                            except Exception as e:
                                logger.error(f"❌ Failed to close partial position on exchange: {e}")
                                # Continue with database update anyway
                        else:
                            logger.info(f"🧪 TEST MODE: Would close 50% of {pos['market_type']} position {pos['symbol']} {pos['side']} {partial_quantity}")
                        
                        # Create partial close record
                        await conn.execute("""
                            INSERT INTO paper_positions 
                            (symbol, side, entry_price, quantity, stop_loss, take_profit, 
                             current_price, realized_pnl, market_type, is_open, close_reason, 
                             original_position_id, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, false, $10, $11, $12, $13)
                        """, pos['symbol'], pos['side'], entry_price, partial_quantity, 
                        pos['stop_loss'], pos['take_profit'], current_price, partial_pnl, 
                        pos['market_type'], close_reason, pos['id'], pos['created_at'], datetime.utcnow())
                        
                        # Reduce original position size by 50%
                        remaining_quantity = quantity * 0.5
                        remaining_pnl = unrealized_pnl * 0.5
                        
                        await conn.execute("""
                            UPDATE paper_positions 
                            SET quantity = $1, unrealized_pnl = $2, updated_at = $3
                            WHERE id = $4
                        """, remaining_quantity, remaining_pnl, datetime.utcnow(), pos['id'])
                        
                        logger.info(f"💰 PARTIAL CLOSE: {pos['symbol']} {pos['side']} - 50% at 1.5% profit - PnL: {partial_pnl:.2f} USDT")
                        
                        # Update quantity for remaining position
                        quantity = remaining_quantity
                        unrealized_pnl = remaining_pnl
                    
                    # Close position if SL/TP hit
                    elif should_close:
                        # Close position on exchange and database
                        close_result = await self.close_position(pos['id'], close_reason)
                        if close_result['success']:
                            logger.info(f"🔒 Position CLOSED: {pos['symbol']} {pos['side']} - {close_reason} - PnL: {close_result['realized_pnl']:.2f} USDT")
                        else:
                            logger.error(f"❌ Failed to close position: {close_result['error']}")
                        continue  # Skip adding to positions list
                    
                    # Update position in database with current price (if still open)
                    await conn.execute("""
                        UPDATE paper_positions 
                        SET current_price = $1, unrealized_pnl = $2, updated_at = $3
                        WHERE id = $4
                    """, current_price, unrealized_pnl, datetime.utcnow(), pos['id'])
                    
                    positions.append({
                        "id": pos['id'],
                        "symbol": pos['symbol'],
                        "side": pos['side'],
                        "entry_price": entry_price,
                        "current_price": current_price,
                        "quantity": quantity,
                        "unrealized_pnl": unrealized_pnl,
                        "pnl_percentage": (unrealized_pnl / (entry_price * quantity)) * 100,
                        "market_type": pos['market_type'],
                        "stop_loss": float(pos['stop_loss']) if pos['stop_loss'] else None,
                        "take_profit": float(pos['take_profit']) if pos['take_profit'] else None,
                        "created_at": pos['created_at'].isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    })
                    
                    logger.info(f"📊 Updated position: {pos['symbol']} {pos['side']} - PnL: {unrealized_pnl:.2f} USDT")
                    
                except Exception as e:
                    logger.error(f"Error updating position {pos['id']}: {e}")
                    # Still include position with old data
                    positions.append({
                        "id": pos['id'],
                        "symbol": pos['symbol'],
                        "side": pos['side'],
                        "entry_price": float(pos['entry_price']),
                        "current_price": float(pos['current_price']),
                        "quantity": float(pos['quantity']),
                        "unrealized_pnl": float(pos['unrealized_pnl']),
                        "pnl_percentage": 0.0,
                        "market_type": pos['market_type'],
                        "created_at": pos['created_at'].isoformat(),
                        "updated_at": pos['updated_at'].isoformat()
                    })
            
            await conn.close()
            
            logger.info(f"📊 Found {len(positions)} total positions from database")
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            
        return positions
    
    async def close_position(self, position_id: int, reason: str = "manual") -> Dict:
        """Close a position on the exchange and database."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get position details
            position = await conn.fetchrow("""
                SELECT * FROM paper_positions WHERE id = $1 AND is_open = true
            """, position_id)
            
            if not position:
                return {"success": False, "error": "Position not found or already closed"}
            
            symbol = position['symbol'].replace('/', '')
            side = position['side']
            quantity = float(position['quantity'])
            market_type = position['market_type']
            
            # Close position on exchange
            if not self.test_mode:
                try:
                    if market_type == 'futures':
                        # Close futures position
                        close_side = 'sell' if side == 'LONG' else 'buy'
                        close_order = self.futures_exchange.create_market_order(
                            symbol, close_side, quantity
                        )
                        logger.info(f"🔒 FUTURES position closed on Binance: {close_order['id']}")
                        
                        # Cancel any pending SL/TP orders
                        try:
                            orders = self.futures_exchange.fetch_open_orders(symbol)
                            for order in orders:
                                if order['side'] == close_side:
                                    self.futures_exchange.cancel_order(order['id'], symbol)
                                    logger.info(f"🚫 Cancelled pending order: {order['id']}")
                        except Exception as e:
                            logger.warning(f"Could not cancel pending orders: {e}")
                            
                    else:  # spot
                        # Close spot position
                        close_side = 'sell' if side == 'LONG' else 'buy'
                        close_order = self.spot_exchange.create_market_order(
                            symbol, close_side, quantity
                        )
                        logger.info(f"🔒 SPOT position closed on Binance: {close_order['id']}")
                        
                        # Cancel any pending SL/TP orders
                        try:
                            orders = self.spot_exchange.fetch_open_orders(symbol)
                            for order in orders:
                                if order['side'] == close_side:
                                    self.spot_exchange.cancel_order(order['id'], symbol)
                                    logger.info(f"🚫 Cancelled pending order: {order['id']}")
                        except Exception as e:
                            logger.warning(f"Could not cancel pending orders: {e}")
                            
                except Exception as e:
                    logger.error(f"Error closing position on exchange: {e}")
                    return {"success": False, "error": f"Exchange closure failed: {e}"}
            else:
                logger.info(f"🧪 TEST MODE: Would close {market_type} position {symbol} {side} {quantity}")
            
            # Calculate realized PnL
            entry_price = float(position['entry_price'])
            current_price = float(position['current_price'])
            
            if side == 'LONG':
                realized_pnl = (current_price - entry_price) * quantity
            else:  # SHORT
                realized_pnl = (entry_price - current_price) * quantity
            
            # Update position in database
            await conn.execute("""
                UPDATE paper_positions 
                SET is_open = false, closed_at = $1, realized_pnl = $2, updated_at = $3, close_reason = $4
                WHERE id = $5
            """, datetime.utcnow(), realized_pnl, datetime.utcnow(), reason, position_id)
            
            logger.info(f"🔒 Position {position_id} closed: {realized_pnl:.2f} USDT PnL - Reason: {reason}")
            
            return {
                "success": True,
                "position_id": position_id,
                "realized_pnl": realized_pnl,
                "reason": reason,
                "market_type": market_type
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
                leverage_info = self.futures_exchange.fetch_leverage_tiers([symbol])
                
                if leverage_info and symbol in leverage_info:
                    # Get current position info to check leverage
                    positions = self.futures_exchange.fetch_positions([symbol])
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
    """Test the dual executor."""
    executor = DualTradingExecutor(test_mode=True)
    
    print("🤖 Testing Dual Trading Executor...")
    
    # Test signal analysis
    test_signal = {
        "id": "test_123",
        "symbol": "BTC/USDT",
        "direction": "LONG",
        "entry_price": 50000.0,
        "stop_loss": 48000.0,
        "take_profit_1": 52000.0,
        "signal_score": 0.75,
        "timeframe": "4h"
    }
    
    analysis = executor.analyze_signal_for_market_selection(test_signal)
    print(f"📊 Signal Analysis:")
    print(f"   Recommended Market: {analysis['recommended_market'].upper()}")
    print(f"   Confidence: {analysis['confidence']:.1%}")
    print(f"   Reasoning: {', '.join(analysis['reasoning'])}")
    
    # Test execution
    result = await executor.execute_signal(test_signal)
    print(f"\n🚀 Execution Result:")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Market: {result['market'].upper()}")
        print(f"   Position ID: {result['position_id']}")


if __name__ == "__main__":
    asyncio.run(main())

