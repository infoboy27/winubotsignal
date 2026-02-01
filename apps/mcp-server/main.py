#!/usr/bin/env python3
"""
Winu Bot MCP Server - Market Intelligence Chat
Provides LLM-powered market analysis using local Llama model
"""

import os
import sys
import asyncio
import asyncpg
import httpx
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import requests
from loguru import logger

sys.path.append('/packages')

# Configure logging
logger.add("mcp_server.log", rotation="10 MB", level="INFO")

app = FastAPI(
    title="Winu Bot MCP Server",
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://winu:winu250420@winu-bot-signal-postgres:5432/winudb")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
CMC_API_KEY = os.getenv("CMC_API_KEY", os.getenv("COINMARKETCAP_API_KEY", ""))

# Winu Bot Branding
APP_NAME = "Winu Bot"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "AI-Powered Cryptocurrency Market Intelligence"

# Initialize exchanges
binance = None
if BINANCE_API_KEY and BINANCE_API_SECRET:
    binance = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_API_SECRET,
        'enableRateLimit': True,
    })


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: Optional[List[str]] = None
    analysis: Optional[Dict[str, Any]] = None


async def get_db_connection():
    """Get database connection."""
    return await asyncpg.connect(DATABASE_URL)


async def fetch_market_data(symbol: str = None) -> Dict[str, Any]:
    """Fetch current market data from multiple sources."""
    market_data = {
        "binance": {},
        "coinmarketcap": {},
        "database": {}
    }
    
    try:
        # Fetch from Binance
        if binance:
            if symbol:
                ticker = binance.fetch_ticker(symbol.replace('/', ''))
                market_data["binance"] = {
                    "symbol": symbol,
                    "price": ticker.get("last"),
                    "volume": ticker.get("quoteVolume"),
                    "change_24h": ticker.get("percentage"),
                    "high_24h": ticker.get("high"),
                    "low_24h": ticker.get("low"),
                }
            else:
                tickers = binance.fetch_tickers()
                market_data["binance"] = {
                    "total_pairs": len(tickers),
                    "top_volume": sorted(
                        [(k, v.get("quoteVolume", 0)) for k, v in tickers.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                }
    except Exception as e:
        logger.error(f"Error fetching Binance data: {e}")
    
    try:
        # Fetch from CoinMarketCap
        if CMC_API_KEY:
            headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
            if symbol:
                base = symbol.split('/')[0]
                url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={base}"
            else:
                url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?limit=10"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    market_data["coinmarketcap"] = data.get("data", {})
    except Exception as e:
        logger.error(f"Error fetching CoinMarketCap data: {e}")
    
    try:
        # Fetch from database
        conn = await get_db_connection()
        if symbol:
            # Get recent signals
            signals = await conn.fetch("""
                SELECT symbol, direction, score, created_at, entry_price, stop_loss, take_profit_1
                FROM signals 
                WHERE symbol = $1 AND created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 10
            """, symbol)
            
            # Get OHLCV data for multiple timeframes
            ohlcv_1h = await conn.fetch("""
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv_data 
                WHERE symbol = $1 AND timeframe = '1h'
                ORDER BY timestamp DESC
                LIMIT 100
            """, symbol)
            
            ohlcv_1d = await conn.fetch("""
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv_data 
                WHERE symbol = $1 AND timeframe = '1d'
                ORDER BY timestamp DESC
                LIMIT 30
            """, symbol)
            
            # Calculate price statistics
            if ohlcv_1h:
                prices_1h = [float(c['close']) for c in ohlcv_1h]
                prices_1d = [float(c['close']) for c in ohlcv_1d] if ohlcv_1d else []
                
                price_stats = {
                    "current_price": prices_1h[0] if prices_1h else None,
                    "24h_high": max(prices_1h[:24]) if len(prices_1h) >= 24 else max(prices_1h) if prices_1h else None,
                    "24h_low": min(prices_1h[:24]) if len(prices_1h) >= 24 else min(prices_1h) if prices_1h else None,
                    "7d_high": max(prices_1d[:7]) if len(prices_1d) >= 7 else None,
                    "7d_low": min(prices_1d[:7]) if len(prices_1d) >= 7 else None,
                    "30d_high": max(prices_1d) if prices_1d else None,
                    "30d_low": min(prices_1d) if prices_1d else None,
                }
                
                if prices_1h and len(prices_1h) >= 24:
                    price_change_24h = ((prices_1h[0] - prices_1h[23]) / prices_1h[23]) * 100
                    price_stats["24h_change_percent"] = price_change_24h
                
                if prices_1d and len(prices_1d) >= 7:
                    price_change_7d = ((prices_1d[0] - prices_1d[6]) / prices_1d[6]) * 100
                    price_stats["7d_change_percent"] = price_change_7d
            else:
                price_stats = {}
            
            market_data["database"] = {
                "recent_signals": [dict(s) for s in signals],
                "ohlcv_1h": [dict(o) for o in ohlcv_1h[:10]],  # Last 10 candles
                "ohlcv_1d": [dict(o) for o in ohlcv_1d[:7]],  # Last 7 days
                "price_statistics": price_stats
            }
        else:
            # Get overall stats
            total_signals = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE created_at > NOW() - INTERVAL '24 hours'")
            top_symbols = await conn.fetch("""
                SELECT symbol, COUNT(*) as signal_count, AVG(score) as avg_score
                FROM signals 
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY symbol
                ORDER BY signal_count DESC
                LIMIT 10
            """)
            
            market_data["database"] = {
                "total_signals_24h": total_signals,
                "top_symbols": [dict(s) for s in top_symbols]
            }
        
        await conn.close()
    except Exception as e:
        logger.error(f"Error fetching database data: {e}")
    
    return market_data


async def query_ollama(prompt: str, context: Dict[str, Any] = None) -> str:
    """Query Ollama LLM with prompt and context."""
    try:
        # Prepare context for LLM
        context_str = ""
        if context:
            # Format context in a more readable way
            context_parts = []
            
            if context.get("binance"):
                binance_data = context["binance"]
                if isinstance(binance_data, dict):
                    if "symbol" in binance_data:
                        context_parts.append(f"Binance Data for {binance_data.get('symbol', 'N/A')}:")
                        context_parts.append(f"  Current Price: ${binance_data.get('price', 'N/A'):,.2f}")
                        context_parts.append(f"  24h Change: {binance_data.get('change_24h', 'N/A'):.2f}%")
                        context_parts.append(f"  24h High: ${binance_data.get('high_24h', 'N/A'):,.2f}")
                        context_parts.append(f"  24h Low: ${binance_data.get('low_24h', 'N/A'):,.2f}")
                        context_parts.append(f"  24h Volume: ${binance_data.get('volume', 'N/A'):,.2f}")
            
            if context.get("coinmarketcap"):
                cmc_data = context["coinmarketcap"]
                if isinstance(cmc_data, dict) and cmc_data:
                    context_parts.append("\nCoinMarketCap Data:")
                    context_parts.append(json.dumps(cmc_data, indent=2))
            
            if context.get("database"):
                db_data = context["database"]
                if "recent_signals" in db_data:
                    signals = db_data["recent_signals"]
                    if signals:
                        context_parts.append(f"\nRecent Trading Signals ({len(signals)} signals):")
                        for sig in signals[:5]:  # Show top 5
                            context_parts.append(f"  {sig.get('symbol', 'N/A')} {sig.get('direction', 'N/A')} - Score: {sig.get('score', 0):.2f} - Entry: ${sig.get('entry_price', 'N/A')}")
                
                if "ohlcv_1h" in db_data or "ohlcv_1d" in db_data:
                    if "ohlcv_1h" in db_data and db_data["ohlcv_1h"]:
                        ohlcv_1h = db_data["ohlcv_1h"]
                        latest = ohlcv_1h[0]
                        context_parts.append(f"\nLatest 1H OHLCV Data:")
                        context_parts.append(f"  Price: ${latest.get('close', 'N/A'):,.2f}")
                        context_parts.append(f"  Volume: {latest.get('volume', 'N/A'):,.2f}")
                    
                    if "price_statistics" in db_data:
                        stats = db_data["price_statistics"]
                        if stats:
                            context_parts.append(f"\nPrice Statistics:")
                            if stats.get("current_price"):
                                context_parts.append(f"  Current: ${stats['current_price']:,.2f}")
                            if stats.get("24h_high"):
                                context_parts.append(f"  24h High: ${stats['24h_high']:,.2f}")
                            if stats.get("24h_low"):
                                context_parts.append(f"  24h Low: ${stats['24h_low']:,.2f}")
                            if stats.get("24h_change_percent") is not None:
                                context_parts.append(f"  24h Change: {stats['24h_change_percent']:.2f}%")
                            if stats.get("7d_change_percent") is not None:
                                context_parts.append(f"  7d Change: {stats['7d_change_percent']:.2f}%")
            
            context_str = "\n".join(context_parts) if context_parts else json.dumps(context, indent=2)
        
        full_prompt = f"""You are Winu Bot, an advanced AI-powered cryptocurrency market analyst and trading assistant. 
You are part of the Winu Bot Signal platform, providing intelligent market analysis using real-time data.

You have access to:
- Real-time market data from Binance (prices, volume, 24h changes)
- Market intelligence from CoinMarketCap (market cap, rankings, trends)
- Historical trading data and signals from Winu Bot database
- Technical analysis indicators and patterns

Your role is to provide:
1. **Accurate Market Analysis**: Analyze current market conditions using all available data
2. **Trading Insights**: Provide actionable trading insights based on technical and fundamental analysis
3. **Risk Assessment**: Identify and explain potential risks
4. **Data-Driven Answers**: Always reference specific numbers, prices, and metrics from the data
5. **Professional Tone**: Be clear, concise, and professional, suitable for serious traders

**IMPORTANT**: 
- Always base your analysis on the provided data
- Use specific numbers (prices, percentages, volumes) from the context
- If data is not available, say so clearly
- Provide actionable insights, not just generic advice
- Format your response with clear sections and bullet points when appropriate

User Question: {prompt}

Available Data:
{context_str if context_str else "No specific market data available. Provide general market insights."}

Now provide a comprehensive, data-driven analysis:"""

        # Call Ollama API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 500  # Reduced from max_tokens for faster response
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "I apologize, but I couldn't generate a response.")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return "I'm experiencing technical difficulties. Please try again."
                
    except Exception as e:
        logger.error(f"Error querying Ollama: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"I encountered an error while processing your request: {str(e)}"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Ollama
        async with httpx.AsyncClient(timeout=5.0) as client:
            ollama_check = await client.get(f"{OLLAMA_URL}/api/tags")
            ollama_status = "healthy" if ollama_check.status_code == 200 else "unhealthy"
    except:
        ollama_status = "unhealthy"
    
    return {
        "status": "healthy",
        "ollama": ollama_status,
        "model": OLLAMA_MODEL,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for market analysis."""
    try:
        # Extract symbols from message if mentioned
        symbols = []
        message_lower = request.message.lower()
        common_symbols = ['btc', 'eth', 'ada', 'sol', 'dot', 'bnb', 'xrp', 'doge', 'matic', 'avax']
        for sym in common_symbols:
            if sym in message_lower:
                symbols.append(f"{sym.upper()}/USDT")
        
        # Fetch market data
        market_data = {}
        if symbols:
            market_data = await fetch_market_data(symbols[0])
        else:
            market_data = await fetch_market_data()
        
        # Query LLM with context
        response_text = await query_ollama(request.message, market_data)
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or f"conv_{datetime.utcnow().timestamp()}"
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            sources=["Binance", "CoinMarketCap", "Winu Database"],
            analysis=market_data
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            conversation_id = data.get("conversation_id")
            
            # Fetch market data
            market_data = await fetch_market_data()
            
            # Query LLM
            response_text = await query_ollama(message, market_data)
            
            # Send response
            await websocket.send_json({
                "response": response_text,
                "conversation_id": conversation_id or f"conv_{datetime.utcnow().timestamp()}",
                "sources": ["Binance", "CoinMarketCap", "Winu Database"],
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


@app.get("/api/market-data/{symbol}")
async def get_market_data(symbol: str):
    """Get market data for a specific symbol."""
    try:
        data = await fetch_market_data(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

