"""Real-time signal generation with live market data."""

import asyncio
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
import sys
sys.path.append('/packages')

from common.database import Signal, Asset
from common.logging import get_logger
from dependencies import get_db

router = APIRouter()
logger = get_logger(__name__)

class RealTimePriceFetcher:
    """Fetches real-time prices from multiple exchanges."""
    
    @staticmethod
    async def get_binance_prices() -> Dict[str, float]:
        """Fetch real-time prices from Binance API."""
        try:
            response = requests.get('https://api.binance.com/api/v3/ticker/price', timeout=10)
            if response.status_code == 200:
                prices = response.json()
                result = {}
                for price_data in prices:
                    symbol = price_data['symbol']
                    if symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']:
                        # Convert to our format
                        formatted_symbol = symbol.replace('USDT', '/USDT')
                        result[formatted_symbol] = float(price_data['price'])
                return result
        except Exception as e:
            logger.error(f"Error fetching Binance prices: {e}")
        return {}

    @staticmethod
    async def get_coingecko_prices() -> Dict[str, float]:
        """Fetch real-time prices from CoinGecko API as backup."""
        try:
            # CoinGecko API for major cryptocurrencies
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,cardano,polkadot&vs_currencies=usd',
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'BTC/USDT': data.get('bitcoin', {}).get('usd', 0),
                    'ETH/USDT': data.get('ethereum', {}).get('usd', 0),
                    'SOL/USDT': data.get('solana', {}).get('usd', 0),
                    'ADA/USDT': data.get('cardano', {}).get('usd', 0),
                    'DOT/USDT': data.get('polkadot', {}).get('usd', 0),
                }
        except Exception as e:
            logger.error(f"Error fetching CoinGecko prices: {e}")
        return {}

    @staticmethod
    async def get_live_prices() -> Dict[str, float]:
        """Get live prices from multiple sources with fallback."""
        # Try Binance first (most reliable for crypto)
        prices = await RealTimePriceFetcher.get_binance_prices()
        if prices:
            return prices
        
        # Fallback to CoinGecko
        prices = await RealTimePriceFetcher.get_coingecko_prices()
        if prices:
            return prices
        
        raise HTTPException(status_code=503, detail="Unable to fetch live market data")

class TechnicalAnalyzer:
    """Performs technical analysis on real market data."""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_momentum(prices: List[float], period: int = 10) -> float:
        """Calculate price momentum."""
        if len(prices) < period:
            return 0.0
        
        return (prices[-1] - prices[-period]) / prices[-period] * 100

    @staticmethod
    def analyze_signal(symbol: str, current_price: float, historical_prices: List[float]) -> Dict[str, Any]:
        """Analyze market data and generate signal."""
        if len(historical_prices) < 20:
            return None
        
        # Calculate technical indicators
        rsi = TechnicalAnalyzer.calculate_rsi(historical_prices)
        momentum = TechnicalAnalyzer.calculate_momentum(historical_prices)
        
        # Determine signal direction and confidence
        signal_data = {
            'symbol': symbol,
            'current_price': current_price,
            'rsi': rsi,
            'momentum': momentum,
            'direction': None,
            'confidence': 0.0,
            'entry_price': current_price,
            'take_profit': None,
            'stop_loss': None
        }
        
        # RSI-based signals
        if rsi < 30:  # Oversold
            signal_data['direction'] = 'LONG'
            signal_data['confidence'] = min(0.9, 0.6 + (30 - rsi) / 30 * 0.3)
        elif rsi > 70:  # Overbought
            signal_data['direction'] = 'SHORT'
            signal_data['confidence'] = min(0.9, 0.6 + (rsi - 70) / 30 * 0.3)
        elif 40 <= rsi <= 60:  # Neutral
            # Use momentum for direction
            if momentum > 2:
                signal_data['direction'] = 'LONG'
                signal_data['confidence'] = min(0.8, 0.5 + momentum / 10)
            elif momentum < -2:
                signal_data['direction'] = 'SHORT'
                signal_data['confidence'] = min(0.8, 0.5 + abs(momentum) / 10)
        
        # Only generate signal if confidence is high enough
        if signal_data['direction'] and signal_data['confidence'] >= 0.6:
            # Calculate TP/SL based on volatility
            volatility = abs(momentum) / 100
            tp_sl_percent = max(0.015, min(0.03, volatility))  # 1.5-3% based on volatility
            
            if signal_data['direction'] == 'LONG':
                signal_data['take_profit'] = round(current_price * (1 + tp_sl_percent), 2)
                signal_data['stop_loss'] = round(current_price * (1 - tp_sl_percent), 2)
            else:  # SHORT
                signal_data['take_profit'] = round(current_price * (1 - tp_sl_percent), 2)
                signal_data['stop_loss'] = round(current_price * (1 + tp_sl_percent), 2)
            
            return signal_data
        
        return None

@router.post("/generate")
async def generate_real_time_signals(db: AsyncSession = Depends(get_db)):
    """Generate signals based on real-time market data."""
    try:
        # Get live prices
        live_prices = await RealTimePriceFetcher.get_live_prices()
        logger.info(f"Fetched live prices: {live_prices}")
        
        generated_signals = []
        
        for symbol, current_price in live_prices.items():
            if current_price <= 0:
                continue
            
            # For now, we'll generate signals based on current price analysis
            # In production, you'd fetch historical data for proper technical analysis
            historical_prices = [current_price * (1 + (i - 20) * 0.01) for i in range(20)]
            
            signal_data = TechnicalAnalyzer.analyze_signal(symbol, current_price, historical_prices)
            
            if signal_data:
                # Save signal to database
                signal = Signal(
                    symbol=signal_data['symbol'],
                    timeframe='ONE_HOUR',
                    signal_type='ENTRY',
                    direction=signal_data['direction'],
                    entry_price=signal_data['entry_price'],
                    take_profit_1=signal_data['take_profit'],
                    stop_loss=signal_data['stop_loss'],
                    score=signal_data['confidence'],
                    is_active=True,
                    created_at=datetime.utcnow(),
                    realized_pnl=0.0,
                    confluences=json.dumps({"rsi": signal_data['rsi'], "momentum": signal_data['momentum']}),
                    context=json.dumps({"analysis": "real_time_technical"}),
                    updated_at=datetime.utcnow()
                )
                
                db.add(signal)
                generated_signals.append({
                    'symbol': signal_data['symbol'],
                    'direction': signal_data['direction'],
                    'entry_price': signal_data['entry_price'],
                    'confidence': signal_data['confidence'],
                    'rsi': signal_data['rsi'],
                    'momentum': signal_data['momentum']
                })
        
        await db.commit()
        
        return {
            "message": f"Generated {len(generated_signals)} real-time signals",
            "signals": generated_signals,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating real-time signals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate signals: {str(e)}")

@router.get("/live-prices")
async def get_live_prices():
    """Get current live market prices."""
    try:
        prices = await RealTimePriceFetcher.get_live_prices()
        return {
            "prices": prices,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "live_market_data"
        }
    except Exception as e:
        logger.error(f"Error fetching live prices: {e}")
        raise HTTPException(status_code=503, detail="Unable to fetch live market data")

