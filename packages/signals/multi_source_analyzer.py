"""Multi-source data analyzer for Binance, Gate.io, and CoinMarketCap."""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from loguru import logger

from .modern_signal import MarketData, ModernSignal, ModernSignalGenerator


@dataclass
class ExchangeData:
    """Data from a single exchange."""
    name: str
    price: float
    volume_24h: float
    change_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime
    order_book: Optional[Dict] = None
    trades: Optional[List[Dict]] = None


@dataclass
class CoinMarketCapData:
    """CoinMarketCap data."""
    rank: int
    market_cap: float
    supply: float
    circulating_supply: float
    max_supply: Optional[float]
    price: float
    volume_24h: float
    change_1h: float
    change_24h: float
    change_7d: float
    change_30d: float
    change_90d: float
    timestamp: datetime


class MultiSourceAnalyzer:
    """Analyzer that combines data from multiple sources for comprehensive analysis."""
    
    def __init__(self, binance_api_key: str = None, binance_secret: str = None,
                 gate_api_key: str = None, gate_secret: str = None,
                 cmc_api_key: str = None):
        self.binance_api_key = binance_api_key
        self.binance_secret = binance_secret
        self.gate_api_key = gate_api_key
        self.gate_secret = gate_secret
        self.cmc_api_key = cmc_api_key
        
        self.signal_generator = ModernSignalGenerator()
    
    async def analyze_symbol(self, symbol: str, timeframes: List[str] = None) -> Optional[ModernSignal]:
        """Comprehensive analysis of a symbol using multiple data sources."""
        
        if timeframes is None:
            timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        try:
            # Fetch data from all sources concurrently
            tasks = [
                self._fetch_binance_data(symbol),
                self._fetch_gate_data(symbol),
                self._fetch_cmc_data(symbol),
                self._fetch_multi_timeframe_data(symbol, timeframes)
            ]
            
            binance_data, gate_data, cmc_data, multi_tf_data = await asyncio.gather(*tasks)
            
            # Create aggregated market data
            market_data = self._aggregate_market_data(binance_data, gate_data, cmc_data)
            
            # Use primary timeframe for signal generation
            primary_timeframe = '1h'
            primary_df = multi_tf_data.get(primary_timeframe)
            
            if primary_df is None or len(primary_df) < 200:
                logger.warning(f"Insufficient data for {symbol} {primary_timeframe}")
                return None
            
            # Generate modern signal
            signal = self.signal_generator.generate_modern_signal(
                symbol=symbol,
                timeframe=primary_timeframe,
                df=primary_df,
                market_data=market_data,
                multi_timeframe_data=multi_tf_data
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    async def _fetch_binance_data(self, symbol: str) -> Optional[ExchangeData]:
        """Fetch data from Binance."""
        try:
            # Convert symbol format (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace('/', '')
            
            async with aiohttp.ClientSession() as session:
                # Get 24hr ticker
                url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return ExchangeData(
                            name="binance",
                            price=float(data['lastPrice']),
                            volume_24h=float(data['volume']),
                            change_24h=float(data['priceChangePercent']),
                            high_24h=float(data['highPrice']),
                            low_24h=float(data['lowPrice']),
                            timestamp=datetime.now()
                        )
        except Exception as e:
            logger.error(f"Error fetching Binance data for {symbol}: {e}")
            return None
    
    async def _fetch_gate_data(self, symbol: str) -> Optional[ExchangeData]:
        """Fetch data from Gate.io."""
        try:
            # Convert symbol format (BTC/USDT -> BTC_USDT)
            gate_symbol = symbol.replace('/', '_')
            
            async with aiohttp.ClientSession() as session:
                # Get ticker
                url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={gate_symbol}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            ticker = data[0]
                            return ExchangeData(
                                name="gate",
                                price=float(ticker['last']),
                                volume_24h=float(ticker['base_volume']),
                                change_24h=float(ticker['change_percentage']),
                                high_24h=float(ticker['high_24h']),
                                low_24h=float(ticker['low_24h']),
                                timestamp=datetime.now()
                            )
        except Exception as e:
            logger.error(f"Error fetching Gate.io data for {symbol}: {e}")
            return None
    
    async def _fetch_cmc_data(self, symbol: str) -> Optional[CoinMarketCapData]:
        """Fetch data from CoinMarketCap."""
        try:
            # Extract base symbol (BTC from BTC/USDT)
            base_symbol = symbol.split('/')[0]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'X-CMC_PRO_API_KEY': self.cmc_api_key,
                    'Accept': 'application/json'
                }
                
                # Get quotes
                url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
                params = {'symbol': base_symbol}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'data' in data and base_symbol in data['data']:
                            coin_data = data['data'][base_symbol]
                            quote = coin_data['quote']['USD']
                            
                            return CoinMarketCapData(
                                rank=coin_data['cmc_rank'],
                                market_cap=quote['market_cap'],
                                supply=coin_data['total_supply'] or 0,
                                circulating_supply=coin_data['circulating_supply'],
                                max_supply=coin_data['max_supply'],
                                price=quote['price'],
                                volume_24h=quote['volume_24h'],
                                change_1h=quote['percent_change_1h'],
                                change_24h=quote['percent_change_24h'],
                                change_7d=quote['percent_change_7d'],
                                change_30d=quote['percent_change_30d'],
                                change_90d=quote['percent_change_90d'],
                                timestamp=datetime.now()
                            )
        except Exception as e:
            logger.error(f"Error fetching CMC data for {symbol}: {e}")
            return None
    
    async def _fetch_multi_timeframe_data(self, symbol: str, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for multiple timeframes."""
        multi_tf_data = {}
        
        for tf in timeframes:
            try:
                # Fetch from Binance (most reliable for OHLCV)
                df = await self._fetch_ohlcv_binance(symbol, tf)
                if df is not None:
                    multi_tf_data[tf] = df
            except Exception as e:
                logger.error(f"Error fetching {tf} data for {symbol}: {e}")
        
        return multi_tf_data
    
    async def _fetch_ohlcv_binance(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Binance."""
        try:
            # Convert symbol and timeframe
            binance_symbol = symbol.replace('/', '')
            tf_map = {
                '1m': '1m', '5m': '5m', '15m': '15m',
                '1h': '1h', '4h': '4h', '1d': '1d'
            }
            binance_tf = tf_map.get(timeframe, '1h')
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': binance_symbol,
                    'interval': binance_tf,
                    'limit': 500
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Convert to DataFrame
                        df = pd.DataFrame(data, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                            'taker_buy_quote', 'ignore'
                        ])
                        
                        # Convert types
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = pd.to_numeric(df[col])
                        
                        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Error fetching OHLCV from Binance: {e}")
            return None
    
    def _aggregate_market_data(self, binance_data: Optional[ExchangeData], 
                             gate_data: Optional[ExchangeData], 
                             cmc_data: Optional[CoinMarketCapData]) -> MarketData:
        """Aggregate data from multiple sources."""
        
        # Calculate price variance between exchanges
        prices = []
        if binance_data:
            prices.append(binance_data.price)
        if gate_data:
            prices.append(gate_data.price)
        
        price_variance = np.var(prices) if len(prices) > 1 else 0.0
        
        # Calculate volume consensus
        volumes = []
        if binance_data:
            volumes.append(binance_data.volume_24h)
        if gate_data:
            volumes.append(gate_data.volume_24h)
        
        volume_consensus = np.mean(volumes) if volumes else 0.0
        
        return MarketData(
            binance_price=binance_data.price if binance_data else 0.0,
            binance_volume_24h=binance_data.volume_24h if binance_data else 0.0,
            binance_change_24h=binance_data.change_24h if binance_data else 0.0,
            gate_price=gate_data.price if gate_data else 0.0,
            gate_volume_24h=gate_data.volume_24h if gate_data else 0.0,
            gate_change_24h=gate_data.change_24h if gate_data else 0.0,
            cmc_rank=cmc_data.rank if cmc_data else 0,
            cmc_market_cap=cmc_data.market_cap if cmc_data else 0.0,
            cmc_supply=cmc_data.supply if cmc_data else 0.0,
            cmc_circulating_supply=cmc_data.circulating_supply if cmc_data else 0.0,
            price_variance=price_variance,
            volume_consensus=volume_consensus
        )
    
    async def analyze_multiple_symbols(self, symbols: List[str], timeframes: List[str] = None) -> List[ModernSignal]:
        """Analyze multiple symbols concurrently."""
        
        tasks = [self.analyze_symbol(symbol, timeframes) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = []
        for result in results:
            if isinstance(result, ModernSignal):
                signals.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error in symbol analysis: {result}")
        
        return signals






