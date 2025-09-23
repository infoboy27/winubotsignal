"""Smart Money analyzer - Institutional flow detection."""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from loguru import logger


class SmartMoneyAnalyzer:
    """
    Detect smart money (institutional) activity through order flow analysis,
    stop hunts, fair value gaps, and order blocks.
    """
    
    def __init__(self, lookback: int = 50):
        self.lookback = lookback
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze smart money activity.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with smart money analysis results
        """
        if len(df) < self.lookback:
            return self._default_result()
        
        # Detect order blocks
        order_blocks = self._detect_order_blocks(df)
        
        # Detect fair value gaps
        fair_value_gaps = self._detect_fair_value_gaps(df)
        
        # Detect stop hunts/liquidity sweeps
        stop_hunts = self._detect_stop_hunts(df)
        
        # Analyze volume anomalies
        volume_anomalies = self._analyze_volume_anomalies(df)
        
        # Check for smart money signals
        signal_detected = self._evaluate_smart_money_signal(
            order_blocks, fair_value_gaps, stop_hunts, volume_anomalies, df
        )
        
        # Determine direction
        direction = self._determine_direction(
            order_blocks, fair_value_gaps, stop_hunts, df
        )
        
        return {
            "signal_detected": signal_detected,
            "direction": direction,
            "order_blocks": order_blocks,
            "fair_value_gaps": fair_value_gaps,
            "stop_hunts": stop_hunts,
            "volume_anomalies": volume_anomalies,
            "confidence": self._calculate_confidence(
                order_blocks, fair_value_gaps, stop_hunts, volume_anomalies
            )
        }
    
    def _detect_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Detect institutional order blocks."""
        order_blocks = []
        
        # Look for significant price moves with high volume
        for i in range(10, len(df) - 5):
            candle = df.iloc[i]
            
            # Check for strong bullish candle
            body_size = abs(candle['close'] - candle['open'])
            candle_range = candle['high'] - candle['low']
            
            if body_size / candle_range > 0.7:  # Strong body
                # Check volume
                avg_volume = df['volume'].iloc[i-10:i].mean()
                if candle['volume'] > avg_volume * 1.5:
                    
                    # Check if it's a bullish or bearish order block
                    if candle['close'] > candle['open']:
                        # Bullish order block
                        order_blocks.append({
                            "type": "bullish",
                            "index": i,
                            "high": candle['high'],
                            "low": candle['low'],
                            "open": candle['open'],
                            "close": candle['close'],
                            "volume": candle['volume'],
                            "strength": min(candle['volume'] / avg_volume, 3.0)
                        })
                    else:
                        # Bearish order block
                        order_blocks.append({
                            "type": "bearish",
                            "index": i,
                            "high": candle['high'],
                            "low": candle['low'],
                            "open": candle['open'],
                            "close": candle['close'],
                            "volume": candle['volume'],
                            "strength": min(candle['volume'] / avg_volume, 3.0)
                        })
        
        # Return only recent order blocks
        recent_blocks = [ob for ob in order_blocks if len(df) - ob['index'] <= 20]
        return sorted(recent_blocks, key=lambda x: x['index'], reverse=True)[:5]
    
    def _detect_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Detect fair value gaps (FVGs)."""
        fvgs = []
        
        for i in range(1, len(df) - 1):
            prev_candle = df.iloc[i-1]
            current_candle = df.iloc[i]
            next_candle = df.iloc[i+1]
            
            # Bullish FVG: gap between prev high and next low
            if (prev_candle['high'] < next_candle['low'] and 
                current_candle['close'] > current_candle['open']):
                
                gap_size = next_candle['low'] - prev_candle['high']
                gap_percent = gap_size / prev_candle['high'] * 100
                
                if gap_percent > 0.1:  # Minimum 0.1% gap
                    fvgs.append({
                        "type": "bullish",
                        "index": i,
                        "high": next_candle['low'],
                        "low": prev_candle['high'],
                        "gap_size": gap_size,
                        "gap_percent": gap_percent,
                        "filled": False
                    })
            
            # Bearish FVG: gap between prev low and next high
            elif (prev_candle['low'] > next_candle['high'] and 
                  current_candle['close'] < current_candle['open']):
                
                gap_size = prev_candle['low'] - next_candle['high']
                gap_percent = gap_size / prev_candle['low'] * 100
                
                if gap_percent > 0.1:  # Minimum 0.1% gap
                    fvgs.append({
                        "type": "bearish",
                        "index": i,
                        "high": prev_candle['low'],
                        "low": next_candle['high'],
                        "gap_size": gap_size,
                        "gap_percent": gap_percent,
                        "filled": False
                    })
        
        # Check if gaps have been filled
        current_price = df['close'].iloc[-1]
        for fvg in fvgs:
            if fvg['low'] <= current_price <= fvg['high']:
                fvg['filled'] = True
        
        # Return recent unfilled gaps
        recent_fvgs = [fvg for fvg in fvgs if len(df) - fvg['index'] <= 30 and not fvg['filled']]
        return sorted(recent_fvgs, key=lambda x: x['index'], reverse=True)[:5]
    
    def _detect_stop_hunts(self, df: pd.DataFrame) -> List[Dict]:
        """Detect stop hunts and liquidity sweeps."""
        stop_hunts = []
        
        # Look for price moves that quickly reverse after hitting highs/lows
        for i in range(5, len(df) - 2):
            current_candle = df.iloc[i]
            
            # Check for liquidity sweep above recent highs
            recent_highs = df['high'].iloc[i-5:i]
            max_recent_high = recent_highs.max()
            
            if current_candle['high'] > max_recent_high:
                # Check if price quickly reversed
                next_candles = df.iloc[i+1:i+3]
                if len(next_candles) > 0 and next_candles['close'].min() < current_candle['open']:
                    
                    # Calculate sweep characteristics
                    sweep_distance = current_candle['high'] - max_recent_high
                    sweep_percent = sweep_distance / max_recent_high * 100
                    
                    # Check volume spike
                    avg_volume = df['volume'].iloc[i-5:i].mean()
                    volume_ratio = current_candle['volume'] / avg_volume
                    
                    if sweep_percent > 0.05 and volume_ratio > 1.2:
                        stop_hunts.append({
                            "type": "high_sweep",
                            "index": i,
                            "sweep_level": current_candle['high'],
                            "previous_high": max_recent_high,
                            "sweep_distance": sweep_distance,
                            "sweep_percent": sweep_percent,
                            "volume_ratio": volume_ratio,
                            "reversal_strength": current_candle['open'] - next_candles['close'].min()
                        })
            
            # Check for liquidity sweep below recent lows
            recent_lows = df['low'].iloc[i-5:i]
            min_recent_low = recent_lows.min()
            
            if current_candle['low'] < min_recent_low:
                # Check if price quickly reversed
                next_candles = df.iloc[i+1:i+3]
                if len(next_candles) > 0 and next_candles['close'].max() > current_candle['open']:
                    
                    # Calculate sweep characteristics
                    sweep_distance = min_recent_low - current_candle['low']
                    sweep_percent = sweep_distance / min_recent_low * 100
                    
                    # Check volume spike
                    avg_volume = df['volume'].iloc[i-5:i].mean()
                    volume_ratio = current_candle['volume'] / avg_volume
                    
                    if sweep_percent > 0.05 and volume_ratio > 1.2:
                        stop_hunts.append({
                            "type": "low_sweep",
                            "index": i,
                            "sweep_level": current_candle['low'],
                            "previous_low": min_recent_low,
                            "sweep_distance": sweep_distance,
                            "sweep_percent": sweep_percent,
                            "volume_ratio": volume_ratio,
                            "reversal_strength": next_candles['close'].max() - current_candle['open']
                        })
        
        # Return recent stop hunts
        recent_hunts = [sh for sh in stop_hunts if len(df) - sh['index'] <= 10]
        return sorted(recent_hunts, key=lambda x: x['index'], reverse=True)[:3]
    
    def _analyze_volume_anomalies(self, df: pd.DataFrame) -> Dict:
        """Analyze volume anomalies that might indicate smart money activity."""
        if len(df) < 20:
            return {"detected": False, "anomalies": []}
        
        # Calculate volume statistics
        volume_mean = df['volume'].iloc[-20:].mean()
        volume_std = df['volume'].iloc[-20:].std()
        
        anomalies = []
        
        # Look for volume spikes in last 10 candles
        for i in range(len(df) - 10, len(df)):
            candle = df.iloc[i]
            z_score = (candle['volume'] - volume_mean) / volume_std if volume_std > 0 else 0
            
            if z_score > 2:  # Significant volume spike
                # Check if it's dark pool activity (high volume, small price move)
                price_change = abs(candle['close'] - candle['open']) / candle['open'] * 100
                
                if price_change < 0.5:  # Small price move with high volume
                    anomalies.append({
                        "type": "dark_pool",
                        "index": i,
                        "volume": candle['volume'],
                        "z_score": z_score,
                        "price_change_percent": price_change
                    })
                else:
                    anomalies.append({
                        "type": "volume_spike",
                        "index": i,
                        "volume": candle['volume'],
                        "z_score": z_score,
                        "price_change_percent": price_change
                    })
        
        return {
            "detected": len(anomalies) > 0,
            "anomalies": anomalies
        }
    
    def _evaluate_smart_money_signal(
        self, 
        order_blocks: List[Dict], 
        fair_value_gaps: List[Dict], 
        stop_hunts: List[Dict],
        volume_anomalies: Dict,
        df: pd.DataFrame
    ) -> bool:
        """Evaluate if there's a valid smart money signal."""
        
        signal_strength = 0
        
        # Order blocks add strength
        if order_blocks:
            signal_strength += len(order_blocks) * 0.3
        
        # Fair value gaps add strength
        if fair_value_gaps:
            signal_strength += len(fair_value_gaps) * 0.2
        
        # Recent stop hunts add significant strength
        recent_stop_hunts = [sh for sh in stop_hunts if len(df) - sh['index'] <= 5]
        if recent_stop_hunts:
            signal_strength += len(recent_stop_hunts) * 0.4
        
        # Volume anomalies add strength
        if volume_anomalies['detected']:
            signal_strength += len(volume_anomalies['anomalies']) * 0.1
        
        return signal_strength >= 0.6
    
    def _determine_direction(
        self, 
        order_blocks: List[Dict], 
        fair_value_gaps: List[Dict], 
        stop_hunts: List[Dict],
        df: pd.DataFrame
    ) -> str:
        """Determine the direction of smart money flow."""
        
        bullish_signals = 0
        bearish_signals = 0
        
        # Count bullish/bearish order blocks
        for ob in order_blocks:
            if ob['type'] == 'bullish':
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        # Count bullish/bearish FVGs
        for fvg in fair_value_gaps:
            if fvg['type'] == 'bullish':
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        # Stop hunts indicate reversal
        for sh in stop_hunts:
            if sh['type'] == 'high_sweep':
                bearish_signals += 2  # High sweep usually leads to bearish move
            else:
                bullish_signals += 2  # Low sweep usually leads to bullish move
        
        if bullish_signals > bearish_signals:
            return "bullish"
        elif bearish_signals > bullish_signals:
            return "bearish"
        else:
            return "neutral"
    
    def _calculate_confidence(
        self, 
        order_blocks: List[Dict], 
        fair_value_gaps: List[Dict], 
        stop_hunts: List[Dict],
        volume_anomalies: Dict
    ) -> float:
        """Calculate confidence in smart money analysis."""
        
        confidence = 0.0
        
        # Order blocks confidence
        if order_blocks:
            avg_strength = sum(ob['strength'] for ob in order_blocks) / len(order_blocks)
            confidence += min(avg_strength * 0.2, 0.3)
        
        # FVG confidence
        if fair_value_gaps:
            avg_gap_percent = sum(fvg['gap_percent'] for fvg in fair_value_gaps) / len(fair_value_gaps)
            confidence += min(avg_gap_percent * 0.1, 0.2)
        
        # Stop hunt confidence
        if stop_hunts:
            avg_volume_ratio = sum(sh['volume_ratio'] for sh in stop_hunts) / len(stop_hunts)
            confidence += min(avg_volume_ratio * 0.1, 0.3)
        
        # Volume anomaly confidence
        if volume_anomalies['detected']:
            anomaly_count = len(volume_anomalies['anomalies'])
            confidence += min(anomaly_count * 0.1, 0.2)
        
        return min(confidence, 1.0)
    
    def _default_result(self) -> Dict:
        """Return default result when insufficient data."""
        return {
            "signal_detected": False,
            "direction": "neutral",
            "order_blocks": [],
            "fair_value_gaps": [],
            "stop_hunts": [],
            "volume_anomalies": {"detected": False, "anomalies": []},
            "confidence": 0.0
        }




