# 🤖 Winu Bot MCP Chat Implementation

## Overview

This document describes the implementation of the AI-powered market intelligence chat system using local Llama 3.1 8B model via Model Context Protocol (MCP) server.

## Architecture

### Components

1. **Ollama Service** (`ollama`)
   - Runs Llama 3.1 8B model locally
   - Exposed on port 11434
   - Provides LLM inference capabilities

2. **MCP Server** (`mcp-server`)
   - FastAPI-based server for market intelligence
   - Integrates with:
     - Binance API (real-time market data)
     - CoinMarketCap API (market intelligence)
     - PostgreSQL database (historical signals and OHLCV data)
   - Exposed on port 8003
   - Accessible via `https://mcp-api.winu.app`

3. **Chat Interface** (`chat`)
   - Next.js-based ChatGPT-like interface
   - Real-time chat with market analysis
   - Accessible via `https://chat.winu.app`

4. **LLM Sentiment Analysis** (integrated into worker)
   - Enhances signal generation with AI sentiment analysis
   - Uses Ollama to analyze market sentiment
   - Adjusts signal scores based on sentiment

## Features

### Market Intelligence Chat

- **Real-time Market Analysis**: Get insights on current market conditions
- **Cryptocurrency Research**: Ask about specific coins (BTC, ETH, ADA, etc.)
- **Trading Signals**: Analyze recent signals and opportunities
- **Historical Data**: Access historical performance and patterns
- **Multi-source Data**: Combines Binance, CoinMarketCap, and Winu database

### LLM-Enhanced Signal Generation

- **Sentiment Analysis**: AI analyzes market sentiment for each signal
- **Score Adjustment**: Technical scores adjusted based on sentiment
- **Reasoning**: LLM provides reasoning for sentiment assessment
- **Confidence Levels**: Sentiment confidence scores included

## Setup Instructions

### 1. Start Services

```bash
cd /home/ubuntu/winubotsignal
docker compose -f docker-compose.traefik.yml up -d ollama mcp-server chat
```

### 2. Initialize Ollama Model

```bash
# Wait for Ollama to be ready (about 30 seconds)
sleep 30

# Pull Llama 3.1 8B model
docker exec winu-bot-signal-ollama ollama pull llama3.1:8b

# Or use the initialization script
./scripts/init_ollama.sh
```

### 3. Verify Services

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Check MCP Server
curl http://localhost:8003/health

# Check Chat Interface
curl http://localhost:3001
```

### 4. Access Chat Interface

- **Production**: https://chat.winu.app
- **MCP API**: https://mcp-api.winu.app
- **API Docs**: https://mcp-api.winu.app/docs

## Configuration

### Environment Variables

**Ollama:**
- `OLLAMA_URL`: http://ollama:11434 (default)
- `OLLAMA_MODEL`: llama3.1:8b (default)

**MCP Server:**
- `DATABASE_URL`: PostgreSQL connection string
- `BINANCE_API_KEY`: Binance API key (optional)
- `BINANCE_API_SECRET`: Binance API secret (optional)
- `CMC_API_KEY` or `COINMARKETCAP_API_KEY`: CoinMarketCap API key (optional)

**Chat:**
- `NEXT_PUBLIC_MCP_API_URL`: https://mcp-api.winu.app
- `MCP_SERVER_URL`: http://mcp-server:8003 (internal)

## API Endpoints

### MCP Server

- `GET /health` - Health check
- `POST /api/chat` - Chat endpoint
- `WS /ws/chat` - WebSocket chat endpoint
- `GET /api/market-data/{symbol}` - Get market data for symbol

### Chat Request Format

```json
{
  "message": "What's the current market sentiment for Bitcoin?",
  "conversation_id": "optional-conversation-id",
  "context": {}
}
```

### Chat Response Format

```json
{
  "response": "Based on the current market data...",
  "conversation_id": "conv_1234567890",
  "sources": ["Binance", "CoinMarketCap", "Winu Database"],
  "analysis": {
    "binance": {...},
    "coinmarketcap": {...},
    "database": {...}
  }
}
```

## LLM Sentiment Analysis Integration

The signal generation process now includes LLM sentiment analysis:

1. **Technical Analysis**: Standard technical indicators calculate base score
2. **Sentiment Analysis**: LLM analyzes market sentiment for the symbol
3. **Score Adjustment**: Final score adjusted based on sentiment alignment
4. **Enhanced Context**: Sentiment data stored in signal confluences

### Example Signal with LLM Sentiment

```json
{
  "symbol": "BTC/USDT",
  "direction": "LONG",
  "score": 0.85,
  "confluences": {
    "multi_timeframe": true,
    "momentum": true,
    "support_resistance": true,
    "rsi": 45.2,
    "ema": 42500.0,
    "llm_sentiment": "bullish",
    "llm_confidence": 0.78
  },
  "context": {
    "strategy": "improved_win_rate_with_llm",
    "version": "2.0",
    "llm_reasoning": "Strong bullish momentum with positive volume trends..."
  }
}
```

## Usage Examples

### Chat Interface

1. **Market Analysis**
   - "What's the current market sentiment for Bitcoin?"
   - "Analyze ADA/USDT trading opportunities"
   - "What are the best performing coins today?"

2. **Signal Analysis**
   - "Explain the recent signals for SOL/USDT"
   - "What signals were generated in the last 24 hours?"
   - "Show me high-confidence signals"

3. **Historical Data**
   - "What was BTC's performance last week?"
   - "Show me price trends for ETH/USDT"
   - "Compare BTC and ETH performance"

### API Usage

```bash
# Chat via API
curl -X POST https://mcp-api.winu.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current price of Bitcoin?"
  }'

# Get market data
curl https://mcp-api.winu.app/api/market-data/BTC/USDT
```

## Monitoring

### Health Checks

```bash
# Check all services
docker ps | grep -E "ollama|mcp-server|chat"

# Check logs
docker logs winu-bot-signal-ollama
docker logs winu-bot-signal-mcp-server
docker logs winu-bot-signal-chat
```

### Performance

- **Ollama**: ~8GB RAM required for Llama 3.1 8B
- **MCP Server**: ~500MB RAM
- **Chat Interface**: ~200MB RAM
- **Response Time**: 2-5 seconds per query (depending on model load)

## Troubleshooting

### Ollama Not Responding

```bash
# Check if Ollama is running
docker ps | grep ollama

# Check logs
docker logs winu-bot-signal-ollama

# Restart if needed
docker restart winu-bot-signal-ollama
```

### Model Not Found

```bash
# Pull model manually
docker exec winu-bot-signal-ollama ollama pull llama3.1:8b

# Verify model
docker exec winu-bot-signal-ollama ollama list
```

### MCP Server Errors

```bash
# Check database connection
docker exec winu-bot-signal-mcp-server python -c "import asyncpg; print('OK')"

# Check API keys
docker exec winu-bot-signal-mcp-server env | grep -E "BINANCE|CMC"
```

### Chat Interface Not Loading

```bash
# Check Next.js build
docker logs winu-bot-signal-chat

# Rebuild if needed
docker compose -f docker-compose.traefik.yml build chat
docker compose -f docker-compose.traefik.yml up -d chat
```

## Future Enhancements

- [ ] Streaming responses for real-time chat
- [ ] Conversation history persistence
- [ ] Multi-language support
- [ ] Advanced chart generation
- [ ] Voice input/output
- [ ] Mobile app integration
- [ ] Custom model fine-tuning
- [ ] Sentiment analysis dashboard

## Security Considerations

- MCP server uses CORS middleware for cross-origin requests
- API keys stored in environment variables (not in code)
- Database credentials secured via Docker secrets
- HTTPS enforced via Traefik with Cloudflare certificates
- Rate limiting recommended for production use

## License

Part of the Winu Bot Signal platform.

