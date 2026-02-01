"""Trend analyzer - Multi-timeframe trend detection."""

import numpy as np
import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    from . import mock_pandas_ta as ta
from typing import Dict, List
from loguru import logger


class TrendAnalyzer:
    """
    Multi-timeframe trend analysis using EMA alignments, ADX, and momentum indicators.
    """
    
    def __init__(self, fast_ema: int = 20, slow_ema: int = 50, trend_ema: int = 200):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.trend_ema = trend_ema
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze trend direction and strength.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with trend analysis results
        """
        if len(df) < self.trend_ema:
            return self._default_result()
        
        # Calculate EMAs
        df['ema_fast'] = ta.ema(df['close'], length=self.fast_ema)
        df['ema_slow'] = ta.ema(df['close'], length=self.slow_ema)
        df['ema_trend'] = ta.ema(df['close'], length=self.trend_ema)
        
        # Calculate ADX for trend strength
        adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
        if isinstance(adx_data, pd.DataFrame):
            df['adx'] = adx_data['ADX_14']
            df['di_plus'] = adx_data['DMP_14']
            df['di_minus'] = adx_data['DMN_14']
        else:
            # Handle case where ADX returns a Series
            df['adx'] = adx_data
            df['di_plus'] = 0  # Default values if not available
            df['di_minus'] = 0
        
        # Calculate momentum indicators
        df['rsi'] = ta.rsi(df['close'], length=14)
        macd_data = ta.macd(df['close'])
        df['macd'] = macd_data['MACD_12_26_9']
        df['macd_signal'] = macd_data['MACDs_12_26_9']
        df['macd_histogram'] = macd_data['MACDh_12_26_9']
        
        # Get latest values
        latest = df.iloc[-1]
        
        # Determine trend direction
        trend_direction = self._determine_trend_direction(latest)
        
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength(df)
        
        # Check EMA alignment
        ema_alignment = self._check_ema_alignment(latest)
        
        # Check momentum confirmation
        momentum_confirmation = self._check_momentum_confirmation(latest)
        
        # Calculate trend score
        trend_score = self._calculate_trend_score(
            trend_direction, trend_strength, ema_alignment, momentum_confirmation
        )
        
        return {
            "direction": trend_direction,
            "strength": trend_strength,
            "score": trend_score,
            "ema_alignment": ema_alignment,
            "momentum_confirmation": momentum_confirmation,
            "adx": latest['adx'] if not pd.isna(latest['adx']) else 0,
            "rsi": latest['rsi'] if not pd.isna(latest['rsi']) else 50,
            "macd_signal": "bullish" if latest['macd'] > latest['macd_signal'] else "bearish",
            "trend_change_probability": self._calculate_trend_change_probability(df)
        }
    
    def _determine_trend_direction(self, latest: pd.Series) -> str:
        """Determine primary trend direction."""
        price = latest['close']
        ema_fast = latest['ema_fast']
        ema_slow = latest['ema_slow']
        ema_trend = latest['ema_trend']
        
        # Primary trend based on 200 EMA
        if price > ema_trend:
            primary_trend = "up"
        elif price < ema_trend:
            primary_trend = "down"
        else:
            primary_trend = "neutral"
        
        # Short-term trend based on EMA crossover
        if ema_fast > ema_slow:
            short_term_trend = "up"
        elif ema_fast < ema_slow:
            short_term_trend = "down"
        else:
            short_term_trend = "neutral"
        
        # Combine trends
        if primary_trend == short_term_trend:
            return primary_trend
        elif primary_trend == "neutral":
            return short_term_trend
        else:
            return "mixed"
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength using ADX and price momentum."""
        if len(df) < 20:
            return 0.0
        
        latest_adx = df['adx'].iloc[-1]
        if pd.isna(latest_adx):
            return 0.0
        
        # ADX strength interpretation
        if latest_adx > 50:
            adx_strength = 1.0
        elif latest_adx > 25:
            adx_strength = 0.7
        elif latest_adx > 15:
            adx_strength = 0.4
        else:
            adx_strength = 0.1
        
        # Price momentum strength
        price_change_20 = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]
        momentum_strength = min(abs(price_change_20) * 10, 1.0)
        
        # Combine strengths
        return (adx_strength + momentum_strength) / 2
    
    def _check_ema_alignment(self, latest: pd.Series) -> bool:
        """Check if EMAs are properly aligned with trend."""
        price = latest['close']
        ema_fast = latest['ema_fast']
        ema_slow = latest['ema_slow']
        ema_trend = latest['ema_trend']
        
        # For uptrend: price > fast > slow > trend
        uptrend_aligned = price > ema_fast > ema_slow > ema_trend
        
        # For downtrend: price < fast < slow < trend
        downtrend_aligned = price < ema_fast < ema_slow < ema_trend
        
        return uptrend_aligned or downtrend_aligned
    
    def _check_momentum_confirmation(self, latest: pd.Series) -> bool:
        """Check if momentum indicators confirm the trend."""
        rsi = latest['rsi']
        macd = latest['macd']
        macd_signal = latest['macd_signal']
        di_plus = latest['di_plus']
        di_minus = latest['di_minus']
        
        # Check for bullish momentum
        bullish_momentum = (
            rsi > 50 and
            macd > macd_signal and
            di_plus > di_minus
        )
        
        # Check for bearish momentum
        bearish_momentum = (
            rsi < 50 and
            macd < macd_signal and
            di_plus < di_minus
        )
        
        return bullish_momentum or bearish_momentum
    
    def _calculate_trend_score(
        self, 
        direction: str, 
        strength: float, 
        ema_alignment: bool, 
        momentum_confirmation: bool
    ) -> float:
        """Calculate overall trend score."""
        if direction in ["neutral", "mixed"]:
            return 0.0
        
        score = strength
        
        # Bonus for EMA alignment
        if ema_alignment:
            score += 0.2
        
        # Bonus for momentum confirmation
        if momentum_confirmation:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_trend_change_probability(self, df: pd.DataFrame) -> float:
        """Calculate probability of trend change."""
        if len(df) < 20:
            return 0.5
        
        # Check for divergence between price and momentum
        recent_prices = df['close'].iloc[-10:].values
        recent_rsi = df['rsi'].iloc[-10:].values
        
        price_trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
        rsi_trend = np.polyfit(range(len(recent_rsi)), recent_rsi, 1)[0]
        
        # If price and RSI trends diverge, higher probability of change
        if (price_trend > 0 and rsi_trend < 0) or (price_trend < 0 and rsi_trend > 0):
            divergence_probability = 0.7
        else:
            divergence_probability = 0.3
        
        # Check for overbought/oversold conditions
        latest_rsi = df['rsi'].iloc[-1]
        if latest_rsi > 80 or latest_rsi < 20:
            overbought_oversold_probability = 0.8
        elif latest_rsi > 70 or latest_rsi < 30:
            overbought_oversold_probability = 0.6
        else:
            overbought_oversold_probability = 0.2
        
        # Combine probabilities
        return (divergence_probability + overbought_oversold_probability) / 2
    
    def _default_result(self) -> Dict:
        """Return default result when insufficient data."""
        return {
            "direction": "neutral",
            "strength": 0.0,
            "score": 0.0,
            "ema_alignment": False,
            "momentum_confirmation": False,
            "adx": 0.0,
            "rsi": 50.0,
            "macd_signal": "neutral",
            "trend_change_probability": 0.5
        }
    
    def get_trend_signals(self, df: pd.DataFrame) -> Dict:
        """Get specific trend-based trading signals."""
        analysis = self.analyze(df)
        
        signals = {
            "long_signal": False,
            "short_signal": False,
            "confidence": 0.0,
            "reason": []
        }
        
        if analysis["score"] > 0.6:
            if analysis["direction"] == "up":
                signals["long_signal"] = True
                signals["confidence"] = analysis["score"]
                signals["reason"].append("Strong uptrend detected")
                
                if analysis["ema_alignment"]:
                    signals["reason"].append("EMA alignment confirmed")
                
                if analysis["momentum_confirmation"]:
                    signals["reason"].append("Momentum confirmation")
            
            elif analysis["direction"] == "down":
                signals["short_signal"] = True
                signals["confidence"] = analysis["score"]
                signals["reason"].append("Strong downtrend detected")
                
                if analysis["ema_alignment"]:
                    signals["reason"].append("EMA alignment confirmed")
                
                if analysis["momentum_confirmation"]:
                    signals["reason"].append("Momentum confirmation")
        
        return signals

