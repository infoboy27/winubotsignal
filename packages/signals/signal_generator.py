"""Main signal generator combining all analysis modules."""

import pandas as pd
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from loguru import logger

from .smooth_trail import SmoothTrailAnalyzer
from .trend import TrendAnalyzer
from .liquidity import LiquidityAnalyzer
from .smart_money import SmartMoneyAnalyzer
from .risk_management import RiskManager


class SignalGenerator:
    """
    Main signal generator that combines all analysis modules to create
    comprehensive trading signals with proper risk management.
    """
    
    def __init__(self, min_score: float = 0.65):
        self.min_score = min_score
        self.smooth_trail = SmoothTrailAnalyzer()
        self.trend = TrendAnalyzer()
        self.liquidity = LiquidityAnalyzer()
        self.smart_money = SmartMoneyAnalyzer()
        self.risk_manager = RiskManager()
        
    def generate_signal(
        self, 
        symbol: str, 
        timeframe: str, 
        df: pd.DataFrame,
        current_balance: Optional[Decimal] = None
    ) -> Optional[Dict]:
        """
        Generate a comprehensive trading signal.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            df: OHLCV DataFrame
            current_balance: Current account balance for position sizing
            
        Returns:
            Signal dictionary or None if no signal generated
        """
        try:
            if len(df) < 200:
                logger.warning(f"Insufficient data for {symbol} {timeframe}: {len(df)} candles")
                return None
            
            # Run all analyses
            smooth_trail_analysis = self.smooth_trail.analyze(df)
            trend_analysis = self.trend.analyze(df)
            liquidity_analysis = self.liquidity.analyze(df)
            smart_money_analysis = self.smart_money.analyze(df)
            
            # Determine signal direction based on confluences
            long_score, short_score = self._calculate_directional_scores(
                smooth_trail_analysis, trend_analysis, liquidity_analysis, smart_money_analysis
            )
            
            # Determine primary signal direction
            if long_score > short_score and long_score >= self.min_score:
                direction = "LONG"
                confidence_score = long_score
            elif short_score > long_score and short_score >= self.min_score:
                direction = "SHORT"
                confidence_score = short_score
            else:
                # No clear signal
                return None
            
            # Get current price
            current_price = Decimal(str(df['close'].iloc[-1]))
            
            # Calculate entry, stop loss, and take profits
            entry_levels = self._calculate_entry_levels(
                direction, current_price, smooth_trail_analysis, trend_analysis
            )
            
            if not entry_levels['entry']:
                logger.warning(f"Could not determine entry level for {symbol} {timeframe}")
                return None
            
            # Apply risk management
            risk_params = self.risk_manager.calculate_position_params(
                entry_price=entry_levels['entry'],
                stop_loss=entry_levels['stop_loss'],
                direction=direction,
                current_balance=current_balance or Decimal('10000'),
                risk_percent=1.0
            )
            
            # Create confluences summary
            confluences = {
                "trend": trend_analysis["score"] > 0.6,
                "smooth_trail": smooth_trail_analysis.get("support", False) if direction == "LONG" 
                              else smooth_trail_analysis.get("resistance", False),
                "liquidity": liquidity_analysis["validation"],
                "smart_money": smart_money_analysis["signal_detected"],
                "volume": liquidity_analysis["volume_confirmation"]
            }
            
            # Create signal context
            context = {
                "trend_analysis": trend_analysis,
                "smooth_trail_analysis": smooth_trail_analysis,
                "liquidity_analysis": liquidity_analysis,
                "smart_money_analysis": smart_money_analysis,
                "timeframe": timeframe,
                "candles_analyzed": len(df)
            }
            
            # Build final signal
            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal_type": "ENTRY",
                "direction": direction,
                "score": round(confidence_score, 3),
                "entry_price": entry_levels['entry'],
                "stop_loss": risk_params['stop_loss'],
                "take_profit_1": risk_params['take_profit_1'],
                "take_profit_2": risk_params['take_profit_2'],
                "take_profit_3": risk_params['take_profit_3'],
                "risk_reward_ratio": risk_params['risk_reward_ratio'],
                "confluences": confluences,
                "context": context,
                "created_at": datetime.utcnow(),
                "position_size": risk_params['position_size']
            }
            
            logger.info(
                f"Generated {direction} signal for {symbol} {timeframe} "
                f"with score {confidence_score:.3f}"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol} {timeframe}: {e}")
            return None
    
    def _calculate_directional_scores(
        self, 
        smooth_trail: Dict, 
        trend: Dict, 
        liquidity: Dict, 
        smart_money: Dict
    ) -> tuple[float, float]:
        """Calculate long and short signal scores based on all analyses."""
        
        long_score = 0.0
        short_score = 0.0
        
        # Trend analysis weight: 30%
        trend_weight = 0.3
        if trend["direction"] == "up":
            long_score += trend["score"] * trend_weight
        elif trend["direction"] == "down":
            short_score += trend["score"] * trend_weight
        
        # Smooth trail analysis weight: 25%
        trail_weight = 0.25
        if smooth_trail.get("support", False):
            long_score += trail_weight
        if smooth_trail.get("resistance", False):
            short_score += trail_weight
        
        # Liquidity analysis weight: 20%
        liquidity_weight = 0.2
        if liquidity["validation"]:
            if liquidity.get("direction") == "bullish":
                long_score += liquidity_weight
            elif liquidity.get("direction") == "bearish":
                short_score += liquidity_weight
        
        # Smart money analysis weight: 25%
        smart_money_weight = 0.25
        if smart_money["signal_detected"]:
            if smart_money.get("direction") == "bullish":
                long_score += smart_money_weight
            elif smart_money.get("direction") == "bearish":
                short_score += smart_money_weight
        
        # Normalize scores
        long_score = min(long_score, 1.0)
        short_score = min(short_score, 1.0)
        
        return long_score, short_score
    
    def _calculate_entry_levels(
        self, 
        direction: str, 
        current_price: Decimal, 
        smooth_trail: Dict, 
        trend: Dict
    ) -> Dict:
        """Calculate entry and stop loss levels."""
        
        if direction == "LONG":
            # For long positions, look for support levels
            support_levels = [
                level for level in smooth_trail.get("levels", [])
                if level["type"] == "support" and level["price"] <= float(current_price)
            ]
            
            if support_levels:
                # Use strongest support level
                best_support = max(support_levels, key=lambda x: x["strength"])
                entry_price = Decimal(str(best_support["price"]))
                stop_loss = entry_price * Decimal('0.98')  # 2% below entry
            else:
                # Use current price as entry
                entry_price = current_price
                stop_loss = current_price * Decimal('0.97')  # 3% stop loss
        
        else:  # SHORT
            # For short positions, look for resistance levels
            resistance_levels = [
                level for level in smooth_trail.get("levels", [])
                if level["type"] == "resistance" and level["price"] >= float(current_price)
            ]
            
            if resistance_levels:
                # Use strongest resistance level
                best_resistance = max(resistance_levels, key=lambda x: x["strength"])
                entry_price = Decimal(str(best_resistance["price"]))
                stop_loss = entry_price * Decimal('1.02')  # 2% above entry
            else:
                # Use current price as entry
                entry_price = current_price
                stop_loss = current_price * Decimal('1.03')  # 3% stop loss
        
        return {
            "entry": entry_price,
            "stop_loss": stop_loss
        }
    
    def batch_analyze(self, market_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Analyze multiple symbols and generate signals.
        
        Args:
            market_data: Dictionary of symbol -> DataFrame mappings
            
        Returns:
            List of generated signals
        """
        signals = []
        
        for symbol, df in market_data.items():
            try:
                # Analyze multiple timeframes
                for timeframe in ['15m', '1h', '4h']:
                    if timeframe in df.columns.get_level_values(1) if hasattr(df.columns, 'get_level_values') else [timeframe]:
                        signal = self.generate_signal(symbol, timeframe, df)
                        if signal:
                            signals.append(signal)
                            
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        # Sort signals by score
        signals.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Generated {len(signals)} signals from {len(market_data)} symbols")
        return signals
    
    def validate_signal(self, signal: Dict) -> bool:
        """Validate a signal meets all requirements."""
        required_fields = [
            'symbol', 'direction', 'score', 'entry_price', 
            'stop_loss', 'confluences'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in signal:
                logger.warning(f"Signal missing required field: {field}")
                return False
        
        # Check score threshold
        if signal['score'] < self.min_score:
            return False
        
        # Check risk/reward ratio
        if signal.get('risk_reward_ratio', 0) < 1.0:
            logger.warning(f"Poor risk/reward ratio: {signal.get('risk_reward_ratio')}")
            return False
        
        # Check confluence count
        confluences = signal.get('confluences', {})
        confluence_count = sum(1 for v in confluences.values() if v)
        
        if confluence_count < 2:
            logger.warning(f"Insufficient confluences: {confluence_count}")
            return False
        
        return True

