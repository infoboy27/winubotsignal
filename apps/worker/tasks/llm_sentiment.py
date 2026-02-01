"""
LLM Sentiment Analysis for Trading Signals
Uses local Llama model via MCP server to analyze market sentiment
"""

import os
import httpx
import asyncio
from typing import Dict, Optional, Any
from loguru import logger

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8003")


async def analyze_signal_sentiment(
    symbol: str,
    direction: str,
    price: float,
    technical_score: float,
    market_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Analyze signal sentiment using LLM.
    
    Returns:
        {
            "sentiment": "bullish" | "bearish" | "neutral",
            "confidence": float (0-1),
            "reasoning": str,
            "adjusted_score": float (technical_score adjusted by sentiment)
        }
    """
    try:
        # Prepare prompt for sentiment analysis
        prompt = f"""Analyze the trading signal sentiment for {symbol} {direction} at price ${price:,.2f}.

Technical Analysis Score: {technical_score:.2f} (0-1 scale)

Market Context:
{_format_market_data(market_data) if market_data else "No additional market data available."}

Provide a sentiment analysis:
1. Overall sentiment (bullish/bearish/neutral)
2. Confidence level (0-1)
3. Brief reasoning (2-3 sentences)
4. Adjusted confidence score considering both technical and sentiment factors

Format your response as JSON:
{{
    "sentiment": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "adjusted_score": 0.0-1.0
}}"""

        # Query Ollama directly for faster response
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent analysis
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Try to extract JSON from response
                import json
                import re
                
                # Look for JSON in the response
                json_match = re.search(r'\{[^{}]*"sentiment"[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        sentiment_data = json.loads(json_match.group())
                        return {
                            "sentiment": sentiment_data.get("sentiment", "neutral").lower(),
                            "confidence": float(sentiment_data.get("confidence", 0.5)),
                            "reasoning": sentiment_data.get("reasoning", "No reasoning provided"),
                            "adjusted_score": float(sentiment_data.get("adjusted_score", technical_score))
                        }
                    except json.JSONDecodeError:
                        pass
                
                # Fallback: parse sentiment from text
                sentiment = "neutral"
                if "bullish" in response_text.lower():
                    sentiment = "bullish"
                elif "bearish" in response_text.lower():
                    sentiment = "bearish"
                
                # Extract confidence from text (look for numbers 0-1)
                confidence_match = re.search(r'(?:confidence|score)[:\s]+([0-9.]+)', response_text, re.IGNORECASE)
                confidence = float(confidence_match.group(1)) if confidence_match else 0.5
                if confidence > 1.0:
                    confidence = confidence / 100.0
                
                # Calculate adjusted score
                sentiment_multiplier = {
                    "bullish": 1.1 if direction.upper() == "LONG" else 0.9,
                    "bearish": 0.9 if direction.upper() == "LONG" else 1.1,
                    "neutral": 1.0
                }
                adjusted_score = min(0.95, technical_score * sentiment_multiplier.get(sentiment, 1.0))
                
                return {
                    "sentiment": sentiment,
                    "confidence": confidence,
                    "reasoning": response_text[:200],  # First 200 chars
                    "adjusted_score": adjusted_score
                }
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return _default_sentiment(technical_score)
                
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return _default_sentiment(technical_score)


def _format_market_data(market_data: Dict) -> str:
    """Format market data for LLM prompt."""
    parts = []
    
    if market_data.get("binance"):
        binance = market_data["binance"]
        if isinstance(binance, dict) and "price" in binance:
            parts.append(f"Binance Price: ${binance.get('price', 'N/A'):,.2f}")
            parts.append(f"24h Change: {binance.get('change_24h', 'N/A'):.2f}%")
    
    if market_data.get("database"):
        db = market_data["database"]
        if "price_statistics" in db:
            stats = db["price_statistics"]
            if stats.get("current_price"):
                parts.append(f"Current Price: ${stats['current_price']:,.2f}")
            if stats.get("24h_change_percent") is not None:
                parts.append(f"24h Change: {stats['24h_change_percent']:.2f}%")
    
    return "\n".join(parts) if parts else "No market data available"


def _default_sentiment(technical_score: float) -> Dict[str, Any]:
    """Return default sentiment when analysis fails."""
    return {
        "sentiment": "neutral",
        "confidence": 0.5,
        "reasoning": "Sentiment analysis unavailable, using technical score only",
        "adjusted_score": technical_score
    }

