"""Liquidity analyzer - Volume and liquidity validation."""

import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict
from loguru import logger


class LiquidityAnalyzer:
    """
    Analyze liquidity conditions and volume patterns to validate signals.
    """
    
    def __init__(self, volume_lookback: int = 20):
        self.volume_lookback = volume_lookback
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze liquidity and volume conditions.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with liquidity analysis results
        """
        if len(df) < self.volume_lookback:
            return self._default_result()
        
        # Calculate volume indicators
        df['volume_sma'] = df['volume'].rolling(self.volume_lookback).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Calculate VWAP
        df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        
        # Calculate On-Balance Volume
        df['obv'] = ta.obv(df['close'], df['volume'])
        
        # Calculate Volume Weighted Moving Average
        df['vwma'] = ta.vwma(df['close'], df['volume'], length=20)
        
        # Get latest values
        latest = df.iloc[-1]
        current_price = latest['close']
        current_volume = latest['volume']
        avg_volume = latest['volume_sma']
        volume_ratio = latest['volume_ratio']
        vwap = latest['vwap']
        
        # Volume validation
        volume_confirmation = self._validate_volume(df)
        
        # VWAP analysis
        vwap_analysis = self._analyze_vwap(current_price, vwap, df)
        
        # Liquidity validation
        liquidity_validation = self._validate_liquidity(df)
        
        # Overall direction based on volume and price action
        direction = self._determine_direction(df)
        
        return {
            "validation": liquidity_validation,
            "volume_confirmation": volume_confirmation,
            "direction": direction,
            "volume_ratio": round(volume_ratio, 2),
            "vwap_analysis": vwap_analysis,
            "current_volume": current_volume,
            "average_volume": avg_volume,
            "liquidity_score": self._calculate_liquidity_score(df)
        }
    
    def _validate_volume(self, df: pd.DataFrame) -> bool:
        """Validate if current volume supports the move."""
        if len(df) < 5:
            return False
        
        # Check recent volume trend
        recent_volumes = df['volume'].iloc[-5:].values
        recent_volume_ratios = df['volume_ratio'].iloc[-5:].values
        
        # Current volume should be above average
        current_volume_ratio = recent_volume_ratios[-1]
        
        # Volume should be increasing on the move
        volume_trend = np.polyfit(range(len(recent_volumes)), recent_volumes, 1)[0]
        
        return current_volume_ratio > 1.2 and volume_trend > 0
    
    def _analyze_vwap(self, current_price: float, vwap: float, df: pd.DataFrame) -> Dict:
        """Analyze price relative to VWAP."""
        if pd.isna(vwap):
            return {"position": "unknown", "deviation": 0.0, "signal": "neutral"}
        
        deviation = (current_price - vwap) / vwap * 100
        
        if current_price > vwap:
            position = "above"
            signal = "bullish" if deviation > 0.5 else "neutral"
        elif current_price < vwap:
            position = "below"
            signal = "bearish" if deviation < -0.5 else "neutral"
        else:
            position = "at"
            signal = "neutral"
        
        # Check for VWAP reclaim or rejection
        recent_prices = df['close'].iloc[-5:].values
        vwap_values = df['vwap'].iloc[-5:].values
        
        reclaim = False
        rejection = False
        
        if len(recent_prices) >= 3:
            # Check if price recently crossed above VWAP (reclaim)
            if recent_prices[-3] < vwap_values[-3] and recent_prices[-1] > vwap_values[-1]:
                reclaim = True
                signal = "bullish"
            
            # Check if price recently crossed below VWAP (rejection)
            elif recent_prices[-3] > vwap_values[-3] and recent_prices[-1] < vwap_values[-1]:
                rejection = True
                signal = "bearish"
        
        return {
            "position": position,
            "deviation": round(deviation, 2),
            "signal": signal,
            "reclaim": reclaim,
            "rejection": rejection
        }
    
    def _validate_liquidity(self, df: pd.DataFrame) -> bool:
        """Validate overall liquidity conditions."""
        if len(df) < self.volume_lookback:
            return False
        
        # Check volume consistency
        recent_volumes = df['volume'].iloc[-10:].values
        volume_std = np.std(recent_volumes)
        volume_mean = np.mean(recent_volumes)
        volume_cv = volume_std / volume_mean if volume_mean > 0 else 1
        
        # Lower coefficient of variation indicates more consistent liquidity
        consistent_liquidity = volume_cv < 0.8
        
        # Check for volume spikes (potential manipulation)
        volume_ratios = df['volume_ratio'].iloc[-10:].values
        extreme_spikes = np.sum(volume_ratios > 5) > 2
        
        # Check average volume level
        current_avg_volume = df['volume_sma'].iloc[-1]
        historical_avg = df['volume'].iloc[:-10].mean() if len(df) > 20 else current_avg_volume
        
        adequate_volume = current_avg_volume > historical_avg * 0.5
        
        return consistent_liquidity and not extreme_spikes and adequate_volume
    
    def _determine_direction(self, df: pd.DataFrame) -> str:
        """Determine liquidity-based direction."""
        if len(df) < 10:
            return "neutral"
        
        # Analyze OBV trend
        obv_values = df['obv'].iloc[-10:].values
        obv_trend = np.polyfit(range(len(obv_values)), obv_values, 1)[0]
        
        # Analyze volume-weighted price trend
        vwma_values = df['vwma'].iloc[-10:].values
        price_values = df['close'].iloc[-10:].values
        
        vwma_trend = np.polyfit(range(len(vwma_values)), vwma_values, 1)[0]
        price_trend = np.polyfit(range(len(price_values)), price_values, 1)[0]
        
        # Check if volume supports price direction
        volume_price_aligned = (obv_trend > 0 and price_trend > 0) or (obv_trend < 0 and price_trend < 0)
        
        if volume_price_aligned:
            if price_trend > 0:
                return "bullish"
            else:
                return "bearish"
        else:
            return "divergence"  # Volume-price divergence
    
    def _calculate_liquidity_score(self, df: pd.DataFrame) -> float:
        """Calculate overall liquidity score."""
        if len(df) < self.volume_lookback:
            return 0.0
        
        score = 0.0
        
        # Volume consistency (30%)
        recent_volumes = df['volume'].iloc[-10:].values
        volume_std = np.std(recent_volumes)
        volume_mean = np.mean(recent_volumes)
        volume_cv = volume_std / volume_mean if volume_mean > 0 else 1
        
        consistency_score = max(0, 1 - volume_cv)
        score += consistency_score * 0.3
        
        # Volume level (25%)
        current_volume_ratio = df['volume_ratio'].iloc[-1]
        volume_score = min(current_volume_ratio / 2, 1.0)
        score += volume_score * 0.25
        
        # VWAP alignment (25%)
        vwap_analysis = self._analyze_vwap(
            df['close'].iloc[-1], 
            df['vwap'].iloc[-1], 
            df
        )
        
        if vwap_analysis["signal"] in ["bullish", "bearish"]:
            vwap_score = 1.0
        else:
            vwap_score = 0.5
        
        score += vwap_score * 0.25
        
        # OBV trend strength (20%)
        if len(df) >= 20:
            obv_values = df['obv'].iloc[-20:].values
            obv_trend_strength = abs(np.corrcoef(range(len(obv_values)), obv_values)[0, 1])
            score += obv_trend_strength * 0.2
        
        return min(score, 1.0)
    
    def _default_result(self) -> Dict:
        """Return default result when insufficient data."""
        return {
            "validation": False,
            "volume_confirmation": False,
            "direction": "neutral",
            "volume_ratio": 1.0,
            "vwap_analysis": {
                "position": "unknown",
                "deviation": 0.0,
                "signal": "neutral",
                "reclaim": False,
                "rejection": False
            },
            "current_volume": 0,
            "average_volume": 0,
            "liquidity_score": 0.0
        }
    
    def get_volume_profile(self, df: pd.DataFrame, bins: int = 20) -> Dict:
        """Get volume profile analysis."""
        if len(df) < bins:
            return {"levels": [], "poc": None, "value_area": None}
        
        # Calculate price levels and volume
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_range = price_max - price_min
        
        if price_range == 0:
            return {"levels": [], "poc": None, "value_area": None}
        
        # Create price bins
        bin_size = price_range / bins
        volume_profile = {}
        
        for i, row in df.iterrows():
            # Distribute volume across price range of each candle
            candle_range = row['high'] - row['low']
            if candle_range > 0:
                # Simple distribution - could be more sophisticated
                mid_price = (row['high'] + row['low']) / 2
                bin_index = int((mid_price - price_min) / bin_size)
                bin_index = min(bin_index, bins - 1)
                
                price_level = price_min + (bin_index * bin_size) + (bin_size / 2)
                
                if price_level not in volume_profile:
                    volume_profile[price_level] = 0
                
                volume_profile[price_level] += row['volume']
        
        # Find Point of Control (highest volume level)
        if volume_profile:
            poc = max(volume_profile.items(), key=lambda x: x[1])[0]
            
            # Calculate value area (70% of volume)
            sorted_levels = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
            total_volume = sum(v for _, v in sorted_levels)
            value_area_volume = total_volume * 0.7
            
            cumulative_volume = 0
            value_area_levels = []
            
            for price, volume in sorted_levels:
                cumulative_volume += volume
                value_area_levels.append(price)
                if cumulative_volume >= value_area_volume:
                    break
            
            value_area = {
                "high": max(value_area_levels),
                "low": min(value_area_levels)
            }
        else:
            poc = None
            value_area = None
        
        # Format levels
        levels = [
            {"price": price, "volume": volume}
            for price, volume in sorted(volume_profile.items())
        ]
        
        return {
            "levels": levels,
            "poc": poc,
            "value_area": value_area
        }

