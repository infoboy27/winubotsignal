"""
Account Executor
Executes trades on a specific Binance account with custom settings
"""

import sys
import ccxt
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

# Add packages to path
sys.path.append('/packages')

from common.logging import get_logger

logger = get_logger(__name__)


class AccountExecutor:
    """Executes trades on a specific account with custom settings."""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        account_config: Dict,
        test_mode: bool = False
    ):
        """
        Initialize account executor.
        
        Args:
            api_key: Decrypted Binance API key
            api_secret: Decrypted Binance API secret
            account_config: Account-specific configuration
            test_mode: Use testnet if True
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = account_config
        self.test_mode = test_mode
        
        # Account details
        self.account_id = account_config.get('id')
        self.account_name = account_config.get('api_name', 'Unknown')
        self.user_id = account_config.get('user_id')
        self.account_type = account_config.get('account_type', 'futures')
        
        # Trading settings
        self.max_position_size_usd = float(account_config.get('max_position_size_usd', 1000))
        self.leverage = float(account_config.get('leverage', 10.0))
        self.max_risk_per_trade = float(account_config.get('max_risk_per_trade', 0.02))
        self.max_daily_loss = float(account_config.get('max_daily_loss', 0.05))
        
        # Position sizing
        self.position_sizing_mode = account_config.get('position_sizing_mode', 'fixed')
        self.position_size_value = float(account_config.get('position_size_value', 100.0))
        
        # Exchange connection
        self.exchange = None
        self.current_balance = 0
        
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialize Binance exchange connection."""
        try:
            exchange_config = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'rateLimit': 1200,
            }
            
            if self.test_mode:
                exchange_config['sandbox'] = True
                exchange_config['options'] = {'test': True}
            else:
                exchange_config['sandbox'] = False
            
            # Set account type
            if self.account_type in ['futures', 'both']:
                exchange_config['options'] = exchange_config.get('options', {})
                exchange_config['options']['defaultType'] = 'future'
            
            self.exchange = ccxt.binance(exchange_config)
            
            mode = "TESTNET" if self.test_mode else "LIVE"
            logger.info(f"✅ Initialized {mode} connection for account: {self.account_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize exchange for {self.account_name}: {e}")
            raise
    
    async def get_balance(self) -> Dict:
        """Get current account balance."""
        try:
            balance = self.exchange.fetch_balance()
            
            if self.account_type == 'futures':
                # Futures balance
                usdt_balance = balance.get('USDT', {})
                self.current_balance = float(usdt_balance.get('free', 0))
            else:
                # Spot balance
                usdt_balance = balance.get('USDT', {})
                self.current_balance = float(usdt_balance.get('free', 0))
            
            return {
                "balance": self.current_balance,
                "currency": "USDT",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch balance for {self.account_name}: {e}")
            return {"balance": 0, "error": str(e)}
    
    def calculate_position_size(self, signal: Dict, current_balance: float) -> Dict:
        """
        Calculate position size based on account settings.
        
        Args:
            signal: Trading signal
            current_balance: Current account balance
            
        Returns:
            Dict with quantity, position_size_usd, risk_amount
        """
        try:
            entry_price = float(signal.get('entry_price', 0))
            stop_loss = float(signal.get('stop_loss', 0))
            
            if entry_price <= 0 or stop_loss <= 0:
                return {"error": "Invalid entry price or stop loss"}
            
            # Calculate risk per USD
            risk_per_unit = abs(entry_price - stop_loss) / entry_price
            
            # Determine position size based on mode
            if self.position_sizing_mode == 'fixed':
                # Fixed USD amount
                position_size_usd = min(self.position_size_value, self.max_position_size_usd)
            
            elif self.position_sizing_mode == 'percentage':
                # Percentage of balance
                position_size_usd = current_balance * (self.position_size_value / 100)
                position_size_usd = min(position_size_usd, self.max_position_size_usd)
            
            elif self.position_sizing_mode == 'kelly':
                # Kelly Criterion (simplified)
                win_rate = float(signal.get('win_rate', 0.55))
                risk_reward = abs(float(signal.get('take_profit_1', entry_price)) - entry_price) / abs(entry_price - stop_loss)
                
                kelly_fraction = (win_rate * risk_reward - (1 - win_rate)) / risk_reward
                kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
                
                position_size_usd = current_balance * kelly_fraction
                position_size_usd = min(position_size_usd, self.max_position_size_usd)
            
            else:
                # Default to fixed
                position_size_usd = min(self.position_size_value, self.max_position_size_usd)
            
            # Apply leverage
            effective_position_size = position_size_usd * self.leverage
            
            # Calculate quantity
            quantity = effective_position_size / entry_price
            
            # Calculate risk amount
            risk_amount = position_size_usd * risk_per_unit
            
            # Validate risk doesn't exceed limit
            if risk_amount / current_balance > self.max_risk_per_trade:
                # Reduce position size to meet risk limit
                max_risk_amount = current_balance * self.max_risk_per_trade
                position_size_usd = max_risk_amount / risk_per_unit
                effective_position_size = position_size_usd * self.leverage
                quantity = effective_position_size / entry_price
                risk_amount = max_risk_amount
            
            return {
                "quantity": quantity,
                "position_size_usd": position_size_usd,
                "effective_position_size": effective_position_size,
                "risk_amount": risk_amount,
                "risk_percentage": (risk_amount / current_balance) * 100,
                "leverage": self.leverage
            }
        
        except Exception as e:
            logger.error(f"❌ Error calculating position size for {self.account_name}: {e}")
            return {"error": str(e)}
    
    async def check_daily_limits(self) -> Dict:
        """Check if daily trading limits have been hit."""
        try:
            # This would query account_daily_stats table
            # For now, return OK
            return {
                "can_trade": True,
                "reason": "Within daily limits"
            }
        
        except Exception as e:
            logger.error(f"❌ Error checking daily limits for {self.account_name}: {e}")
            return {
                "can_trade": False,
                "reason": f"Error checking limits: {str(e)}"
            }
    
    async def execute_order(self, signal: Dict) -> Dict:
        """
        Execute an order based on the signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            Dict with execution result
        """
        try:
            logger.info(f"🔄 Executing order on {self.account_name} for {signal.get('symbol')}")
            
            # Get balance
            balance_info = await self.get_balance()
            if balance_info.get('error'):
                return {
                    "success": False,
                    "error": f"Failed to get balance: {balance_info['error']}",
                    "account_name": self.account_name,
                    "account_id": self.account_id
                }
            
            current_balance = balance_info['balance']
            
            # Check if balance is sufficient
            if current_balance < 10:  # Minimum $10
                return {
                    "success": False,
                    "error": f"Insufficient balance: ${current_balance:.2f}",
                    "account_name": self.account_name,
                    "account_id": self.account_id,
                    "current_balance": current_balance
                }
            
            # Check daily limits
            limits_check = await self.check_daily_limits()
            if not limits_check.get('can_trade', False):
                return {
                    "success": False,
                    "error": f"Daily limits hit: {limits_check.get('reason')}",
                    "account_name": self.account_name,
                    "account_id": self.account_id
                }
            
            # Calculate position size
            position_info = self.calculate_position_size(signal, current_balance)
            if position_info.get('error'):
                return {
                    "success": False,
                    "error": f"Position sizing failed: {position_info['error']}",
                    "account_name": self.account_name,
                    "account_id": self.account_id
                }
            
            # Prepare order
            symbol = signal['symbol'].replace('/', '')  # BTC/USDT -> BTCUSDT
            side = 'buy' if signal['direction'] == 'LONG' else 'sell'
            quantity = position_info['quantity']
            
            # Set leverage for futures
            if self.account_type in ['futures', 'both']:
                try:
                    await self.exchange.set_leverage(self.leverage, symbol)
                    logger.info(f"✅ Leverage set to {self.leverage}x for {symbol}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to set leverage: {e}")
            
            # Execute order
            if self.test_mode:
                logger.info(f"🧪 TEST MODE: Would place {side} order for {quantity:.6f} {symbol}")
                order_result = {
                    "id": f"test_{int(datetime.utcnow().timestamp())}",
                    "symbol": symbol,
                    "side": side,
                    "amount": quantity,
                    "price": float(signal['entry_price']),
                    "status": "filled",
                    "timestamp": datetime.utcnow().isoformat(),
                    "average": float(signal['entry_price'])
                }
            else:
                logger.info(f"🚀 LIVE: Placing {side} order for {quantity:.6f} {symbol}")
                order_result = await self.exchange.create_market_order(symbol, side, quantity)
                logger.info(f"✅ Order placed: {order_result.get('id')}")
            
            return {
                "success": True,
                "order_id": order_result.get('id'),
                "exchange_order_id": order_result.get('id'),
                "account_name": self.account_name,
                "account_id": self.account_id,
                "user_id": self.user_id,
                "symbol": signal['symbol'],
                "side": side.upper(),
                "quantity": quantity,
                "average_price": order_result.get('average') or order_result.get('price'),
                "position_size_usd": position_info['position_size_usd'],
                "leverage": self.leverage,
                "stop_loss": float(signal.get('stop_loss', 0)),
                "take_profit": float(signal.get('take_profit_1', 0)),
                "current_balance": current_balance,
                "test_mode": self.test_mode
            }
        
        except Exception as e:
            logger.error(f"❌ Order execution failed on {self.account_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "account_name": self.account_name,
                "account_id": self.account_id,
                "user_id": self.user_id
            }

