"""Smooth Trail analyzer - Dynamic support/resistance detection."""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from loguru import logger


class SmoothTrailAnalyzer:
    """
    Smooth Trail analysis for dynamic support and resistance levels.
    
    Uses pivot points, fractals, and regression channels to identify
    key levels where price is likely to react.
    """
    
    def __init__(self, lookback: int = 20, sensitivity: float = 0.02):
        self.lookback = lookback
        self.sensitivity = sensitivity
        self.support_levels = []
        self.resistance_levels = []
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze price data for Smooth Trail signals.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with support/resistance levels and signals
        """
        if len(df) < self.lookback * 2:
            return {"support": False, "resistance": False, "levels": []}
        
        # Find pivot points
        pivots = self._find_pivot_points(df)
        
        # Calculate dynamic support/resistance
        support_levels = self._calculate_support_levels(df, pivots)
        resistance_levels = self._calculate_resistance_levels(df, pivots)
        
        # Get current price
        current_price = df['close'].iloc[-1]
        
        # Check for support/resistance signals
        support_signal = self._check_support_signal(current_price, support_levels)
        resistance_signal = self._check_resistance_signal(current_price, resistance_levels)
        
        # Calculate strength of levels
        levels = []
        for level in support_levels:
            levels.append({
                "price": level,
                "type": "support",
                "strength": self._calculate_level_strength(df, level, "support"),
                "distance_percent": abs((current_price - level) / current_price * 100)
            })
        
        for level in resistance_levels:
            levels.append({
                "price": level,
                "type": "resistance", 
                "strength": self._calculate_level_strength(df, level, "resistance"),
                "distance_percent": abs((current_price - level) / current_price * 100)
            })
        
        # Sort by distance from current price
        levels.sort(key=lambda x: x["distance_percent"])
        
        return {
            "support": support_signal,
            "resistance": resistance_signal,
            "levels": levels[:10],  # Top 10 closest levels
            "current_price": current_price,
            "trend_direction": self._determine_trend_direction(df)
        }
    
    def _find_pivot_points(self, df: pd.DataFrame) -> Dict[str, List[Tuple[int, float]]]:
        """Find pivot highs and lows."""
        highs = []
        lows = []
        
        high_prices = df['high'].values
        low_prices = df['low'].values
        
        for i in range(self.lookback, len(df) - self.lookback):
            # Check for pivot high
            is_pivot_high = True
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and high_prices[j] >= high_prices[i]:
                    is_pivot_high = False
                    break
            
            if is_pivot_high:
                highs.append((i, high_prices[i]))
            
            # Check for pivot low
            is_pivot_low = True
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and low_prices[j] <= low_prices[i]:
                    is_pivot_low = False
                    break
            
            if is_pivot_low:
                lows.append((i, low_prices[i]))
        
        return {"highs": highs, "lows": lows}
    
    def _calculate_support_levels(self, df: pd.DataFrame, pivots: Dict) -> List[float]:
        """Calculate dynamic support levels."""
        pivot_lows = [price for _, price in pivots["lows"]]
        
        if len(pivot_lows) < 2:
            return []
        
        # Use recent pivot lows as support levels
        recent_lows = sorted(pivot_lows[-10:])  # Last 10 pivot lows
        
        # Group similar levels
        support_levels = []
        for low in recent_lows:
            is_new_level = True
            for existing in support_levels:
                if abs(low - existing) / existing < self.sensitivity:
                    is_new_level = False
                    break
            
            if is_new_level:
                support_levels.append(low)
        
        # Add moving average support
        ma_50 = df['close'].rolling(50).mean().iloc[-1]
        ma_200 = df['close'].rolling(200).mean().iloc[-1]
        
        if not pd.isna(ma_50):
            support_levels.append(ma_50)
        if not pd.isna(ma_200):
            support_levels.append(ma_200)
        
        return sorted(support_levels)
    
    def _calculate_resistance_levels(self, df: pd.DataFrame, pivots: Dict) -> List[float]:
        """Calculate dynamic resistance levels."""
        pivot_highs = [price for _, price in pivots["highs"]]
        
        if len(pivot_highs) < 2:
            return []
        
        # Use recent pivot highs as resistance levels
        recent_highs = sorted(pivot_highs[-10:], reverse=True)  # Last 10 pivot highs
        
        # Group similar levels
        resistance_levels = []
        for high in recent_highs:
            is_new_level = True
            for existing in resistance_levels:
                if abs(high - existing) / existing < self.sensitivity:
                    is_new_level = False
                    break
            
            if is_new_level:
                resistance_levels.append(high)
        
        return sorted(resistance_levels, reverse=True)
    
    def _check_support_signal(self, current_price: float, support_levels: List[float]) -> bool:
        """Check if price is near support level."""
        for level in support_levels:
            distance_percent = abs((current_price - level) / level * 100)
            if distance_percent < (self.sensitivity * 100) and current_price >= level:
                return True
        return False
    
    def _check_resistance_signal(self, current_price: float, resistance_levels: List[float]) -> bool:
        """Check if price is near resistance level."""
        for level in resistance_levels:
            distance_percent = abs((current_price - level) / level * 100)
            if distance_percent < (self.sensitivity * 100) and current_price <= level:
                return True
        return False
    
    def _calculate_level_strength(self, df: pd.DataFrame, level: float, level_type: str) -> float:
        """Calculate the strength of a support/resistance level."""
        touches = 0
        bounces = 0
        
        for i in range(len(df)):
            if level_type == "support":
                # Check if low touched the level
                if abs(df['low'].iloc[i] - level) / level < self.sensitivity:
                    touches += 1
                    # Check if it bounced (next candle closed higher)
                    if i < len(df) - 1 and df['close'].iloc[i + 1] > df['low'].iloc[i]:
                        bounces += 1
            else:  # resistance
                # Check if high touched the level
                if abs(df['high'].iloc[i] - level) / level < self.sensitivity:
                    touches += 1
                    # Check if it bounced (next candle closed lower)
                    if i < len(df) - 1 and df['close'].iloc[i + 1] < df['high'].iloc[i]:
                        bounces += 1
        
        if touches == 0:
            return 0.0
        
        # Strength is based on bounce rate and number of touches
        bounce_rate = bounces / touches
        strength = min(bounce_rate * (1 + touches * 0.1), 1.0)
        
        return strength
    
    def _determine_trend_direction(self, df: pd.DataFrame) -> str:
        """Determine overall trend direction."""
        if len(df) < 50:
            return "neutral"
        
        # Use EMA crossover
        ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
        ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
        
        if ema_20 > ema_50:
            return "up"
        elif ema_20 < ema_50:
            return "down"
        else:
            return "neutral"
    
    def get_entry_levels(self, df: pd.DataFrame, direction: str) -> Dict[str, Optional[float]]:
        """Get suggested entry levels based on Smooth Trail analysis."""
        analysis = self.analyze(df)
        current_price = analysis["current_price"]
        
        if direction.upper() == "LONG":
            # Look for support levels below current price
            support_levels = [
                level for level in analysis["levels"] 
                if level["type"] == "support" and level["price"] < current_price
            ]
            
            if support_levels:
                # Use strongest support level closest to current price
                best_support = max(support_levels, key=lambda x: x["strength"])
                return {
                    "entry": best_support["price"],
                    "stop_loss": best_support["price"] * 0.98,  # 2% below support
                    "confidence": best_support["strength"]
                }
        
        else:  # SHORT
            # Look for resistance levels above current price
            resistance_levels = [
                level for level in analysis["levels"]
                if level["type"] == "resistance" and level["price"] > current_price
            ]
            
            if resistance_levels:
                # Use strongest resistance level closest to current price
                best_resistance = max(resistance_levels, key=lambda x: x["strength"])
                return {
                    "entry": best_resistance["price"],
                    "stop_loss": best_resistance["price"] * 1.02,  # 2% above resistance
                    "confidence": best_resistance["strength"]
                }
        
        return {"entry": None, "stop_loss": None, "confidence": 0.0}

