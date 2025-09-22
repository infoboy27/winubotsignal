"""Risk management module for position sizing and stop loss calculation."""

import pandas as pd
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional
from loguru import logger
try:
    import pandas_ta as ta
except ImportError:
    from . import mock_pandas_ta as ta


class RiskManager:
    """
    Advanced risk management for position sizing, stop loss placement,
    and take profit calculations.
    """
    
    def __init__(self):
        self.default_risk_percent = 1.0
        self.max_risk_percent = 5.0
        self.min_risk_reward = 1.5
        self.max_positions = 10
    
    def calculate_position_params(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        direction: str,
        current_balance: Decimal,
        risk_percent: float = 1.0,
        df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Calculate comprehensive position parameters.
        
        Args:
            entry_price: Entry price for the position
            stop_loss: Initial stop loss level
            direction: Position direction (LONG/SHORT)
            current_balance: Current account balance
            risk_percent: Risk percentage per trade
            df: Price data for advanced calculations
            
        Returns:
            Dictionary with position parameters
        """
        try:
            # Validate inputs
            risk_percent = max(0.1, min(risk_percent, self.max_risk_percent))
            
            # Calculate risk amount
            risk_amount = current_balance * Decimal(risk_percent / 100)
            
            # Calculate position size
            price_diff = abs(entry_price - stop_loss)
            if price_diff == 0:
                logger.warning("Entry price equals stop loss, using default 2% stop")
                if direction == "LONG":
                    stop_loss = entry_price * Decimal('0.98')
                else:
                    stop_loss = entry_price * Decimal('1.02')
                price_diff = abs(entry_price - stop_loss)
            
            position_size = risk_amount / price_diff
            
            # Calculate take profit levels using ATR if available
            take_profits = self._calculate_take_profits(
                entry_price, stop_loss, direction, df
            )
            
            # Calculate risk/reward ratio
            if take_profits['take_profit_1']:
                reward = abs(take_profits['take_profit_1'] - entry_price)
                risk = abs(entry_price - stop_loss)
                risk_reward_ratio = float(reward / risk) if risk > 0 else 0
            else:
                risk_reward_ratio = 0
            
            # Adjust position size based on volatility if data available
            if df is not None and len(df) > 20:
                volatility_adjustment = self._calculate_volatility_adjustment(df)
                position_size *= Decimal(str(volatility_adjustment))
            
            return {
                "position_size": self._round_position_size(position_size),
                "risk_amount": risk_amount,
                "stop_loss": stop_loss,
                "take_profit_1": take_profits['take_profit_1'],
                "take_profit_2": take_profits['take_profit_2'],
                "take_profit_3": take_profits['take_profit_3'],
                "risk_reward_ratio": round(risk_reward_ratio, 2),
                "risk_percent_used": risk_percent,
                "entry_price": entry_price
            }
            
        except Exception as e:
            logger.error(f"Error calculating position parameters: {e}")
            return self._default_position_params(entry_price, current_balance)
    
    def _calculate_take_profits(
        self, 
        entry_price: Decimal, 
        stop_loss: Decimal, 
        direction: str,
        df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """Calculate multiple take profit levels."""
        
        risk = abs(entry_price - stop_loss)
        
        # Default take profits based on risk multiples
        if direction == "LONG":
            tp1 = entry_price + (risk * Decimal('1.5'))  # 1.5R
            tp2 = entry_price + (risk * Decimal('2.5'))  # 2.5R
            tp3 = entry_price + (risk * Decimal('4.0'))  # 4R
        else:  # SHORT
            tp1 = entry_price - (risk * Decimal('1.5'))
            tp2 = entry_price - (risk * Decimal('2.5'))
            tp3 = entry_price - (risk * Decimal('4.0'))
        
        # Adjust based on ATR if available
        if df is not None and len(df) > 20:
            atr = self._calculate_atr(df)
            if atr > 0:
                atr_decimal = Decimal(str(atr))
                
                if direction == "LONG":
                    tp1 = entry_price + (atr_decimal * Decimal('2'))
                    tp2 = entry_price + (atr_decimal * Decimal('3'))
                    tp3 = entry_price + (atr_decimal * Decimal('5'))
                else:
                    tp1 = entry_price - (atr_decimal * Decimal('2'))
                    tp2 = entry_price - (atr_decimal * Decimal('3'))
                    tp3 = entry_price - (atr_decimal * Decimal('5'))
        
        return {
            "take_profit_1": self._round_price(tp1),
            "take_profit_2": self._round_price(tp2),
            "take_profit_3": self._round_price(tp3)
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        try:
            atr_data = ta.atr(df['high'], df['low'], df['close'], length=period)
            if atr_data is not None and not atr_data.empty:
                return float(atr_data.iloc[-1])
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_volatility_adjustment(self, df: pd.DataFrame) -> float:
        """Calculate volatility-based position size adjustment."""
        try:
            # Calculate recent volatility
            returns = df['close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5)  # Annualized volatility
            
            # Adjust position size based on volatility
            # Higher volatility = smaller position
            if volatility > 0.5:  # High volatility
                return 0.7
            elif volatility > 0.3:  # Medium volatility
                return 0.85
            else:  # Low volatility
                return 1.0
                
        except Exception:
            return 1.0
    
    def calculate_dynamic_stop_loss(
        self, 
        entry_price: Decimal, 
        direction: str, 
        df: pd.DataFrame,
        method: str = "atr"
    ) -> Decimal:
        """
        Calculate dynamic stop loss based on various methods.
        
        Args:
            entry_price: Entry price
            direction: Position direction
            df: Price data
            method: Method to use (atr, support_resistance, volatility)
            
        Returns:
            Stop loss price
        """
        try:
            if method == "atr":
                return self._atr_stop_loss(entry_price, direction, df)
            elif method == "support_resistance":
                return self._support_resistance_stop_loss(entry_price, direction, df)
            elif method == "volatility":
                return self._volatility_stop_loss(entry_price, direction, df)
            else:
                # Default percentage stop
                if direction == "LONG":
                    return entry_price * Decimal('0.97')
                else:
                    return entry_price * Decimal('1.03')
                    
        except Exception as e:
            logger.error(f"Error calculating dynamic stop loss: {e}")
            # Fallback to percentage stop
            if direction == "LONG":
                return entry_price * Decimal('0.97')
            else:
                return entry_price * Decimal('1.03')
    
    def _atr_stop_loss(self, entry_price: Decimal, direction: str, df: pd.DataFrame) -> Decimal:
        """Calculate ATR-based stop loss."""
        atr = self._calculate_atr(df)
        atr_multiplier = 2.0  # 2x ATR
        
        if direction == "LONG":
            stop_loss = entry_price - Decimal(str(atr * atr_multiplier))
        else:
            stop_loss = entry_price + Decimal(str(atr * atr_multiplier))
        
        return self._round_price(stop_loss)
    
    def _support_resistance_stop_loss(
        self, 
        entry_price: Decimal, 
        direction: str, 
        df: pd.DataFrame
    ) -> Decimal:
        """Calculate stop loss based on support/resistance levels."""
        
        if direction == "LONG":
            # Find recent support level
            recent_lows = df['low'].iloc[-20:].min()
            buffer = recent_lows * 0.005  # 0.5% buffer
            stop_loss = Decimal(str(recent_lows - buffer))
        else:
            # Find recent resistance level
            recent_highs = df['high'].iloc[-20:].max()
            buffer = recent_highs * 0.005  # 0.5% buffer
            stop_loss = Decimal(str(recent_highs + buffer))
        
        return self._round_price(stop_loss)
    
    def _volatility_stop_loss(
        self, 
        entry_price: Decimal, 
        direction: str, 
        df: pd.DataFrame
    ) -> Decimal:
        """Calculate volatility-based stop loss."""
        
        # Calculate recent price volatility
        returns = df['close'].pct_change().dropna()
        volatility = returns.std()
        
        # Use 2 standard deviations
        stop_distance = entry_price * Decimal(str(volatility * 2))
        
        if direction == "LONG":
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance
        
        return self._round_price(stop_loss)
    
    def validate_risk_parameters(
        self, 
        entry_price: Decimal, 
        stop_loss: Decimal, 
        take_profit: Decimal,
        direction: str
    ) -> Dict:
        """Validate risk parameters meet minimum requirements."""
        
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Calculate risk and reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            validation_result["valid"] = False
            validation_result["errors"].append("Risk cannot be zero")
            return validation_result
        
        # Check risk/reward ratio
        risk_reward_ratio = float(reward / risk)
        
        if risk_reward_ratio < self.min_risk_reward:
            validation_result["warnings"].append(
                f"Risk/reward ratio {risk_reward_ratio:.2f} is below minimum {self.min_risk_reward}"
            )
        
        # Check stop loss placement
        if direction == "LONG":
            if stop_loss >= entry_price:
                validation_result["valid"] = False
                validation_result["errors"].append("Stop loss must be below entry price for long positions")
            
            if take_profit <= entry_price:
                validation_result["valid"] = False
                validation_result["errors"].append("Take profit must be above entry price for long positions")
        
        else:  # SHORT
            if stop_loss <= entry_price:
                validation_result["valid"] = False
                validation_result["errors"].append("Stop loss must be above entry price for short positions")
            
            if take_profit >= entry_price:
                validation_result["valid"] = False
                validation_result["errors"].append("Take profit must be below entry price for short positions")
        
        # Check maximum risk percentage
        risk_percent = float(risk / entry_price * 100)
        if risk_percent > 10:
            validation_result["warnings"].append(
                f"Risk percentage {risk_percent:.2f}% is very high"
            )
        
        return validation_result
    
    def calculate_portfolio_risk(self, positions: list, current_balance: Decimal) -> Dict:
        """Calculate overall portfolio risk metrics."""
        
        if not positions:
            return {
                "total_risk_amount": Decimal('0'),
                "total_risk_percent": 0.0,
                "position_count": 0,
                "max_risk_per_position": 0.0,
                "correlation_risk": 0.0
            }
        
        total_risk = sum(Decimal(str(pos.get('risk_amount', 0))) for pos in positions)
        total_risk_percent = float(total_risk / current_balance * 100)
        
        # Calculate maximum risk per position
        max_risk = max(Decimal(str(pos.get('risk_amount', 0))) for pos in positions)
        max_risk_percent = float(max_risk / current_balance * 100)
        
        # Simple correlation risk (would need price data for proper calculation)
        symbols = [pos.get('symbol', '') for pos in positions]
        correlation_risk = len(set(symbols)) / len(symbols) if symbols else 0
        
        return {
            "total_risk_amount": total_risk,
            "total_risk_percent": round(total_risk_percent, 2),
            "position_count": len(positions),
            "max_risk_per_position": round(max_risk_percent, 2),
            "correlation_risk": round(correlation_risk, 2)
        }
    
    def _round_price(self, price: Decimal, precision: int = 8) -> Decimal:
        """Round price to specified precision."""
        return price.quantize(Decimal('0.1') ** precision, rounding=ROUND_DOWN)
    
    def _round_position_size(self, size: Decimal, precision: int = 6) -> Decimal:
        """Round position size to specified precision."""
        return size.quantize(Decimal('0.1') ** precision, rounding=ROUND_DOWN)
    
    def _default_position_params(self, entry_price: Decimal, balance: Decimal) -> Dict:
        """Return default position parameters in case of error."""
        risk_amount = balance * Decimal('0.01')  # 1% risk
        
        return {
            "position_size": risk_amount / (entry_price * Decimal('0.03')),  # 3% stop
            "risk_amount": risk_amount,
            "stop_loss": entry_price * Decimal('0.97'),
            "take_profit_1": entry_price * Decimal('1.045'),  # 1.5R
            "take_profit_2": entry_price * Decimal('1.075'),  # 2.5R
            "take_profit_3": entry_price * Decimal('1.12'),   # 4R
            "risk_reward_ratio": 1.5,
            "risk_percent_used": 1.0,
            "entry_price": entry_price
        }

