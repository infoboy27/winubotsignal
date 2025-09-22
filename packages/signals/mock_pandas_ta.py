"""
Mock pandas_ta module to replace missing pandas_ta functionality.
This provides basic technical analysis functions for testing purposes.
"""

import pandas as pd
import numpy as np

def atr(high, low, close, length=14):
    """Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=length).mean()

def vwap(high, low, close, volume):
    """Volume Weighted Average Price"""
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()

def obv(close, volume):
    """On Balance Volume"""
    obv = np.where(close > close.shift(1), volume, 
                   np.where(close < close.shift(1), -volume, 0))
    return pd.Series(obv, index=close.index).cumsum()

def vwma(close, volume, length=20):
    """Volume Weighted Moving Average"""
    return (close * volume).rolling(window=length).sum() / volume.rolling(window=length).sum()

def ema(close, length=20):
    """Exponential Moving Average"""
    return close.ewm(span=length).mean()

def adx(high, low, close, length=14):
    """Average Directional Index"""
    # Simplified ADX calculation
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    tr = atr(high, low, close, 1)
    plus_di = 100 * (plus_dm.rolling(window=length).mean() / tr.rolling(window=length).mean())
    minus_di = 100 * (minus_dm.rolling(window=length).mean() / tr.rolling(window=length).mean())
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=length).mean()
    
    return adx

def rsi(close, length=14):
    """Relative Strength Index"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(close, fast=12, slow=26, signal=9):
    """MACD (Moving Average Convergence Divergence)"""
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'MACD_12_26_9': macd_line,
        'MACDs_12_26_9': signal_line,
        'MACDh_12_26_9': histogram
    })
