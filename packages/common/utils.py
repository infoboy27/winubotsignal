"""Utility functions for Million Trader."""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from loguru import logger


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """Convert timestamp to datetime."""
    if timestamp > 1e12:  # Milliseconds
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to millisecond timestamp."""
    return int(dt.timestamp() * 1000)


def round_price(price: Union[float, Decimal], precision: int = 8) -> Decimal:
    """Round price to specified precision."""
    if isinstance(price, float):
        price = Decimal(str(price))
    return price.quantize(Decimal('0.1') ** precision, rounding=ROUND_DOWN)


def round_quantity(quantity: Union[float, Decimal], precision: int = 8) -> Decimal:
    """Round quantity to specified precision."""
    if isinstance(quantity, float):
        quantity = Decimal(str(quantity))
    return quantity.quantize(Decimal('0.1') ** precision, rounding=ROUND_DOWN)


def calculate_position_size(
    balance: Decimal,
    risk_percent: float,
    entry_price: Decimal,
    stop_loss: Decimal
) -> Decimal:
    """Calculate position size based on risk management."""
    risk_amount = balance * Decimal(risk_percent / 100)
    price_diff = abs(entry_price - stop_loss)
    
    if price_diff == 0:
        return Decimal('0')
    
    position_size = risk_amount / price_diff
    return round_quantity(position_size)


def calculate_risk_reward_ratio(
    entry_price: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal
) -> float:
    """Calculate risk to reward ratio."""
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    
    if risk == 0:
        return 0.0
    
    return float(reward / risk)


def calculate_pnl(
    side: str,
    entry_price: Decimal,
    exit_price: Decimal,
    quantity: Decimal
) -> Decimal:
    """Calculate PnL for a position."""
    if side.upper() == "LONG":
        return (exit_price - entry_price) * quantity
    else:  # SHORT
        return (entry_price - exit_price) * quantity


def format_currency(amount: Union[float, Decimal], decimals: int = 2) -> str:
    """Format currency amount with commas."""
    if isinstance(amount, Decimal):
        amount = float(amount)
    return f"{amount:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage with % symbol."""
    return f"{value:.{decimals}f}%"


def generate_signature(
    secret: str,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[str] = None
) -> str:
    """Generate HMAC signature for API requests."""
    if params:
        query_string = urlencode(sorted(params.items()))
        path = f"{path}?{query_string}"
    
    timestamp = str(int(time.time() * 1000))
    payload = f"{timestamp}{method.upper()}{path}"
    
    if body:
        payload += body
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


async def make_http_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retries: int = 3
) -> Optional[Dict[str, Any]]:
    """Make HTTP request with retries and error handling."""
    for attempt in range(retries + 1):
        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_data,
                timeout=timeout
            )
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {'data': response.text}
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} for {url}: {e}")
            if e.response.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt
                logger.info(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                await asyncio.sleep(wait_time)
                continue
            elif e.response.status_code >= 500 and attempt < retries:
                wait_time = 2 ** attempt
                logger.info(f"Server error, retrying in {wait_time}s (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                return None
                
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            if attempt < retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                continue
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            return None
    
    logger.error(f"Max retries exceeded for {url}")
    return None


def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format."""
    if not symbol or '/' not in symbol:
        return False
    
    parts = symbol.split('/')
    if len(parts) != 2:
        return False
    
    base, quote = parts
    if not base or not quote:
        return False
    
    # Check for valid characters (alphanumeric)
    if not base.replace('-', '').replace('_', '').isalnum():
        return False
    if not quote.replace('-', '').replace('_', '').isalnum():
        return False
    
    return True


def normalize_symbol(symbol: str, exchange: str = 'binance') -> str:
    """Normalize symbol format for different exchanges."""
    if not validate_symbol(symbol):
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    symbol = symbol.upper()
    
    if exchange.lower() == 'binance':
        return symbol.replace('/', '')
    elif exchange.lower() == 'gate':
        return symbol.replace('/', '_')
    else:
        return symbol


def parse_timeframe_to_seconds(timeframe: str) -> int:
    """Convert timeframe string to seconds."""
    timeframe_map = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '4h': 14400,
        '6h': 21600,
        '12h': 43200,
        '1d': 86400,
        '1w': 604800,
        '1M': 2592000,  # Approximate
    }
    
    return timeframe_map.get(timeframe, 3600)  # Default to 1 hour


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_decimal(value: Any, default: Decimal = Decimal('0')) -> Decimal:
    """Safely convert value to Decimal."""
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return default


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return []
    
    ema = []
    multiplier = 2 / (period + 1)
    
    # Start with SMA for first value
    sma = sum(prices[:period]) / period
    ema.append(sma)
    
    # Calculate EMA for remaining values
    for i in range(period, len(prices)):
        ema_value = (prices[i] * multiplier) + (ema[-1] * (1 - multiplier))
        ema.append(ema_value)
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return []
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    rsi_values = []
    
    for i in range(period, len(deltas)):
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)
        
        # Update averages
        gain = gains[i] if i < len(gains) else 0
        loss = losses[i] if i < len(losses) else 0
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    
    return rsi_values


def is_market_hours() -> bool:
    """Check if it's within market hours (crypto trades 24/7, so always True)."""
    return True


def get_next_candle_time(timeframe: str, current_time: Optional[datetime] = None) -> datetime:
    """Get the next candle opening time for given timeframe."""
    if current_time is None:
        current_time = utc_now()
    
    seconds = parse_timeframe_to_seconds(timeframe)
    
    # Round down to the current candle start
    timestamp = int(current_time.timestamp())
    candle_start = (timestamp // seconds) * seconds
    
    # Next candle starts after current one
    next_candle = candle_start + seconds
    
    return datetime.fromtimestamp(next_candle, tz=timezone.utc)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Acquire rate limit slot, waiting if necessary."""
        now = time.time()
        
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # If we're at the limit, wait
        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0]) + 0.1
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                return await self.acquire()
        
        # Record this call
        self.calls.append(now)


def create_alert_message(signal: Dict[str, Any]) -> str:
    """Create formatted alert message for notifications."""
    direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
    
    confluences = signal.get('confluences', {})
    confluence_text = []
    
    if confluences.get('trend'):
        confluence_text.append("Trend↑" if signal['direction'] == 'LONG' else "Trend↓")
    if confluences.get('smooth_trail'):
        confluence_text.append("Smooth Trail support" if signal['direction'] == 'LONG' else "Smooth Trail resistance")
    if confluences.get('liquidity'):
        confluence_text.append("Liquidity OK")
    if confluences.get('smart_money'):
        confluence_text.append("Smart Money sweep")
    if confluences.get('volume'):
        confluence_text.append("Volume confirmed")
    
    confluence_str = ", ".join(confluence_text) if confluence_text else "Basic setup"
    
    # Format money amounts with proper currency formatting
    def format_price(price):
        if price == 'N/A' or price is None:
            return 'N/A'
        try:
            price_float = float(price)
            if price_float >= 1000:
                return f"${price_float:,.2f}"
            else:
                return f"${price_float:.4f}"
        except (ValueError, TypeError):
            return str(price)
    
    # Modern alert template with better formatting
    score_emoji = "🔥" if signal['score'] >= 0.8 else "⚡" if signal['score'] >= 0.6 else "📊"
    confidence_level = "HIGH" if signal['score'] >= 0.8 else "MEDIUM" if signal['score'] >= 0.6 else "LOW"
    
    message = f"""🤖 **WINU BOT SIGNAL** {direction_emoji} {score_emoji}

**{signal['symbol']}** • {signal['timeframe']} • {signal['direction']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **ENTRY:** `{format_price(signal.get('entry_price', 'Market'))}`
🛡️ **STOP LOSS:** `{format_price(signal.get('stop_loss', 'N/A'))}`
🎯 **TAKE PROFITS:**
   • TP1: `{format_price(signal.get('take_profit_1', 'N/A'))}`
   • TP2: `{format_price(signal.get('take_profit_2', 'N/A'))}`
   • TP3: `{format_price(signal.get('take_profit_3', 'N/A'))}`

📈 **ANALYSIS:**
   • AI Score: `{signal['score']:.2f}` ({confidence_level})
   • Risk/Reward: `{signal.get('risk_reward_ratio', 'N/A')}`
   • Confluences: {confluence_str}

⏰ **Time:** {signal.get('created_at', utc_now().isoformat())}

⚠️ *Not financial advice. Trade responsibly.*"""
    
    return message




