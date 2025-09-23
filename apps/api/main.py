"""Million Trader FastAPI Application."""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict, Any

import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import from packages
import sys
import os
sys.path.append('/packages')

from common.config import get_settings
from common.logging import setup_logging, get_logger
from common.database import Base

# Import routers
from routers import auth, assets, signals, alerts, backtests, users

# Setup logging
setup_logging()
logger = get_logger(__name__)

settings = get_settings()

# Import database setup from dependencies
from dependencies import engine, AsyncSessionLocal

# Redis setup
redis_client = None

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        if self.active_connections:
            disconnected_clients = []
            for client_id, connection in self.active_connections.items():
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)
            
            # Remove disconnected clients
            for client_id in disconnected_clients:
                self.disconnect(client_id)

manager = ConnectionManager()

# Background task for listening to Redis notifications
async def redis_listener():
    """Listen for Redis notifications and broadcast to WebSocket clients."""
    global redis_client
    
    if not redis_client:
        logger.warning("Redis client not initialized, skipping Redis listener")
        return
    
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('signals', 'alerts', 'system')
        
        logger.info("Started Redis listener for real-time updates")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    channel = message['channel'].decode('utf-8')
                    data = json.loads(message['data'].decode('utf-8'))
                    
                    # Broadcast to all connected WebSocket clients
                    await manager.broadcast({
                        'type': channel,
                        'data': data,
                        'timestamp': data.get('timestamp')
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing Redis message: {e}")
                    
    except Exception as e:
        logger.error(f"Redis listener error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Million Trader API...")
    
    # Initialize Redis
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=False
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/updated")
        
        # Setup TimescaleDB hypertables
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT setup_hypertables();")
            await session.commit()
        logger.info("TimescaleDB hypertables configured")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    
    # Start Redis listener
    if redis_client:
        asyncio.create_task(redis_listener())
    
    logger.info("Million Trader API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Million Trader API...")
    
    if redis_client:
        await redis_client.close()
    
    await engine.dispose()
    logger.info("Million Trader API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Million Trader API",
    description="AI-powered crypto trading signals and alerts system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3003", 
        "http://localhost:3000",
        "https://dashboard.winu.app",
        "https://api.winu.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics
if not settings.monitoring.debug:
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(assets.router, prefix="/assets", tags=["Assets"])
app.include_router(signals.router, prefix="/signals", tags=["Signals"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(backtests.router, prefix="/backtests", tags=["Backtests"])
app.include_router(users.router, prefix="/users", tags=["Users"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Redis
    try:
        if redis_client:
            await redis_client.ping()
            redis_status = "healthy"
        else:
            redis_status = "not_connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" and redis_status in ["healthy", "not_connected"] else "unhealthy",
        "timestamp": "2025-09-22T22:05:00Z",
        "version": "1.0.0",
        "services": {
            "database": db_status,
            "redis": redis_status,
            "api": "healthy"
        }
    }


@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts."""
    client_id = f"client_{id(websocket)}"
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get('type') == 'ping':
                await manager.send_personal_message({'type': 'pong'}, client_id)
            elif message.get('type') == 'subscribe':
                # Handle subscription to specific symbols/channels
                await manager.send_personal_message({
                    'type': 'subscribed',
                    'data': message.get('data', {})
                }, client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Million Trader API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/alerts"
    }


# Import database dependency
from dependencies import get_db


# Dependency to get Redis client
async def get_redis():
    """Redis client dependency."""
    return redis_client


# Add dependencies to app state for access in routers
app.state.get_db = get_db
app.state.get_redis = get_redis
app.state.websocket_manager = manager


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.monitoring.debug,
        log_level=settings.monitoring.log_level.lower()
    )

