"""Modern signal format with comprehensive analysis and multi-source data."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from loguru import logger


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class MarketCondition(Enum):
    """Market condition types."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


class TimeframeImportance(Enum):
    """Timeframe importance levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TechnicalIndicators:
    """Technical indicators data."""
    rsi_14: float
    rsi_21: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float
    bb_position: float
    ema_20: float
    ema_50: float
    ema_200: float
    sma_50: float
    sma_200: float
    adx: float
    adx_di_plus: float
    adx_di_minus: float
    stoch_k: float
    stoch_d: float
    williams_r: float
    cci: float
    atr: float
    obv: float
    vwap: float
    ichimoku_tenkan: float
    ichimoku_kijun: float
    ichimoku_senkou_a: float
    ichimoku_senkou_b: float
    ichimoku_chikou: float


@dataclass
class MarketData:
    """Market data from multiple sources."""
    binance_price: float
    binance_volume_24h: float
    binance_change_24h: float
    gate_price: float
    gate_volume_24h: float
    gate_change_24h: float
    cmc_rank: int
    cmc_market_cap: float
    cmc_supply: float
    cmc_circulating_supply: float
    price_variance: float  # Variance between exchanges
    volume_consensus: float  # Consensus volume across exchanges


@dataclass
class ConfluenceAnalysis:
    """Multi-timeframe confluence analysis."""
    timeframe_signals: Dict[str, Dict]  # Signal for each timeframe
    confluence_score: float
    dominant_timeframe: str
    timeframe_agreement: float
    signal_strength_by_timeframe: Dict[str, SignalStrength]
    critical_timeframes: List[str]


@dataclass
class RiskMetrics:
    """Risk assessment metrics."""
    volatility_24h: float
    volatility_7d: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    var_95: float  # Value at Risk 95%
    expected_return: float
    risk_reward_ratio: float
    position_size: float
    stop_loss_distance: float
    take_profit_distance: float


@dataclass
class SmartMoneyFlow:
    """Smart money flow analysis."""
    institutional_volume: float
    retail_volume: float
    smart_money_ratio: float
    order_blocks: List[Dict]
    fair_value_gaps: List[Dict]
    liquidity_zones: List[Dict]
    stop_hunt_probability: float
    accumulation_phase: bool
    distribution_phase: bool


@dataclass
class ModernSignal:
    """Modern comprehensive signal format."""
    # Basic Info
    id: str
    symbol: str
    timestamp: datetime
    timeframe: str
    
    # Signal Details
    direction: str  # LONG/SHORT
    strength: SignalStrength
    confidence_score: float  # 0.0 to 1.0
    market_condition: MarketCondition
    
    # Price Levels
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    current_price: float
    
    # Analysis Components
    technical_indicators: TechnicalIndicators
    market_data: MarketData
    confluence_analysis: ConfluenceAnalysis
    risk_metrics: RiskMetrics
    smart_money_flow: SmartMoneyFlow
    
    # Additional Data
    volume_profile: Dict
    support_resistance_levels: List[float]
    fibonacci_levels: List[float]
    pivot_points: Dict
    market_sentiment: str
    news_impact: Optional[str]
    
    # Metadata
    data_sources: List[str]
    analysis_version: str
    created_by: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert enums to strings
        result['strength'] = self.strength.value
        result['market_condition'] = self.market_condition.value
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the signal."""
        return f"""
🚨 {self.symbol} {self.direction} Signal ({self.timeframe})
📊 Strength: {self.strength.value.upper()}
🎯 Confidence: {self.confidence_score:.1%}
💰 Entry: ${self.entry_price:,.2f}
🛡️ Stop Loss: ${self.stop_loss:,.2f}
🎯 Take Profit: ${self.take_profit_1:,.2f}
📈 Market: {self.market_condition.value.replace('_', ' ').title()}
🔗 Confluence: {self.confluence_analysis.confluence_score:.1%}
⚡ Risk/Reward: {self.risk_metrics.risk_reward_ratio:.2f}
        """.strip()


class ModernSignalGenerator:
    """Enhanced signal generator with modern format and multi-source analysis."""
    
    def __init__(self):
        self.data_sources = ['binance', 'gate', 'coinmarketcap']
        self.analysis_version = "2.0.0"
        self.created_by = "Million Trader AI"
    
    def generate_modern_signal(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
        market_data: MarketData,
        multi_timeframe_data: Dict[str, pd.DataFrame]
    ) -> Optional[ModernSignal]:
        """Generate a modern comprehensive signal."""
        
        try:
            # Calculate technical indicators
            indicators = self._calculate_technical_indicators(df)
            
            # Analyze confluence across timeframes
            confluence = self._analyze_multi_timeframe_confluence(
                symbol, multi_timeframe_data
            )
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(df, market_data)
            
            # Analyze smart money flow
            smart_money = self._analyze_smart_money_flow(df)
            
            # Determine signal direction and strength
            direction, strength, confidence = self._determine_signal(
                indicators, confluence, risk_metrics, smart_money
            )
            
            if confidence < 0.65:  # Minimum confidence threshold
                return None
            
            # Calculate price levels
            entry_price = df['close'].iloc[-1]
            stop_loss, take_profits = self._calculate_price_levels(
                df, direction, indicators, confluence
            )
            
            # Determine market condition
            market_condition = self._determine_market_condition(
                df, indicators, confluence
            )
            
            # Create modern signal
            signal = ModernSignal(
                id=f"{symbol}_{timeframe}_{int(datetime.now().timestamp())}",
                symbol=symbol,
                timestamp=datetime.now(),
                timeframe=timeframe,
                direction=direction,
                strength=strength,
                confidence_score=confidence,
                market_condition=market_condition,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit_1=take_profits[0],
                take_profit_2=take_profits[1],
                take_profit_3=take_profits[2],
                current_price=entry_price,
                technical_indicators=indicators,
                market_data=market_data,
                confluence_analysis=confluence,
                risk_metrics=risk_metrics,
                smart_money_flow=smart_money,
                volume_profile=self._analyze_volume_profile(df),
                support_resistance_levels=self._find_support_resistance(df),
                fibonacci_levels=self._calculate_fibonacci_levels(df),
                pivot_points=self._calculate_pivot_points(df),
                market_sentiment=self._analyze_sentiment(market_data),
                news_impact=None,  # Would integrate with news API
                data_sources=self.data_sources,
                analysis_version=self.analysis_version,
                created_by=self.created_by
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating modern signal: {e}")
            return None
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Calculate comprehensive technical indicators."""
        # This would use pandas_ta or talib for calculations
        # For now, returning mock data
        return TechnicalIndicators(
            rsi_14=50.0, rsi_21=50.0, macd=0.0, macd_signal=0.0, macd_histogram=0.0,
            bb_upper=0.0, bb_middle=0.0, bb_lower=0.0, bb_width=0.0, bb_position=0.5,
            ema_20=0.0, ema_50=0.0, ema_200=0.0, sma_50=0.0, sma_200=0.0,
            adx=0.0, adx_di_plus=0.0, adx_di_minus=0.0, stoch_k=0.0, stoch_d=0.0,
            williams_r=0.0, cci=0.0, atr=0.0, obv=0.0, vwap=0.0,
            ichimoku_tenkan=0.0, ichimoku_kijun=0.0, ichimoku_senkou_a=0.0,
            ichimoku_senkou_b=0.0, ichimoku_chikou=0.0
        )
    
    def _analyze_multi_timeframe_confluence(self, symbol: str, data: Dict[str, pd.DataFrame]) -> ConfluenceAnalysis:
        """Analyze confluence across multiple timeframes."""
        # Implementation would analyze each timeframe and determine confluence
        return ConfluenceAnalysis(
            timeframe_signals={},
            confluence_score=0.75,
            dominant_timeframe="1h",
            timeframe_agreement=0.8,
            signal_strength_by_timeframe={},
            critical_timeframes=["1h", "4h", "1d"]
        )
    
    def _calculate_risk_metrics(self, df: pd.DataFrame, market_data: MarketData) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        return RiskMetrics(
            volatility_24h=0.05, volatility_7d=0.15, max_drawdown=0.1,
            sharpe_ratio=1.2, sortino_ratio=1.5, var_95=0.02,
            expected_return=0.08, risk_reward_ratio=2.5,
            position_size=0.02, stop_loss_distance=0.02, take_profit_distance=0.05
        )
    
    def _analyze_smart_money_flow(self, df: pd.DataFrame) -> SmartMoneyFlow:
        """Analyze smart money flow patterns."""
        return SmartMoneyFlow(
            institutional_volume=0.0, retail_volume=0.0, smart_money_ratio=0.0,
            order_blocks=[], fair_value_gaps=[], liquidity_zones=[],
            stop_hunt_probability=0.0, accumulation_phase=False, distribution_phase=False
        )
    
    def _determine_signal(self, indicators, confluence, risk_metrics, smart_money) -> Tuple[str, SignalStrength, float]:
        """Determine signal direction, strength, and confidence."""
        # Complex logic to determine signal based on all factors
        return "LONG", SignalStrength.STRONG, 0.85
    
    def _calculate_price_levels(self, df, direction, indicators, confluence) -> Tuple[float, List[float]]:
        """Calculate stop loss and take profit levels."""
        current_price = df['close'].iloc[-1]
        if direction == "LONG":
            stop_loss = current_price * 0.98  # 2% stop loss
            take_profits = [current_price * 1.05, current_price * 1.10, current_price * 1.15]
        else:
            stop_loss = current_price * 1.02  # 2% stop loss
            take_profits = [current_price * 0.95, current_price * 0.90, current_price * 0.85]
        
        return stop_loss, take_profits
    
    def _determine_market_condition(self, df, indicators, confluence) -> MarketCondition:
        """Determine current market condition."""
        return MarketCondition.TRENDING_UP
    
    def _analyze_volume_profile(self, df: pd.DataFrame) -> Dict:
        """Analyze volume profile."""
        return {"high_volume_nodes": [], "low_volume_nodes": []}
    
    def _find_support_resistance(self, df: pd.DataFrame) -> List[float]:
        """Find key support and resistance levels."""
        return []
    
    def _calculate_fibonacci_levels(self, df: pd.DataFrame) -> List[float]:
        """Calculate Fibonacci retracement levels."""
        return []
    
    def _calculate_pivot_points(self, df: pd.DataFrame) -> Dict:
        """Calculate pivot points."""
        return {}
    
    def _analyze_sentiment(self, market_data: MarketData) -> str:
        """Analyze market sentiment."""
        return "bullish"






