"""Monitoring API endpoints for system health checks."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Dict, Any
from datetime import datetime, timedelta
import subprocess
import requests

import sys
sys.path.append('/packages')

from common.database import Asset, Signal, OHLCV
from dependencies import get_db

router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/status")
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """Get comprehensive system status."""
    try:
        # Get database stats
        total_assets_result = await db.execute(select(func.count(Asset.id)))
        total_assets = total_assets_result.scalar()
        
        active_assets_result = await db.execute(select(func.count(Asset.id)).where(Asset.active == True))
        active_assets = active_assets_result.scalar()
        
        total_candles_result = await db.execute(select(func.count(OHLCV.id)))
        total_candles = total_candles_result.scalar()
        
        # Last data update
        last_ohlcv_result = await db.execute(select(OHLCV).order_by(desc(OHLCV.timestamp)).limit(1))
        last_ohlcv = last_ohlcv_result.scalar_one_or_none()
        last_data_update = last_ohlcv.timestamp.isoformat() if last_ohlcv else None
        
        # Recent signals
        recent_signals_result = await db.execute(
            select(Signal).order_by(desc(Signal.created_at)).limit(10)
        )
        recent_signals = recent_signals_result.scalars().all()
        
        # Signals today
        today = datetime.utcnow().date()
        signals_today_result = await db.execute(
            select(func.count(Signal.id)).where(Signal.created_at >= today)
        )
        signals_today = signals_today_result.scalar()
        
        # Check Docker services (skip if docker not available in container)
        docker_services = {}
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"], 
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.strip().split('\n'):
                if line:
                    name, status = line.split('\t', 1)
                    docker_services[name] = status
        except FileNotFoundError:
            # Docker not available in container, use alternative check
            docker_services = {"status": "Docker not available in container", "note": "This is normal for API container"}
        except Exception as e:
            docker_services = {"error": str(e)}
        
        # Check worker logs for errors/warnings
        # Initialize variables before try block
        has_errors = False
        has_warnings = False
        last_scan = "No recent scan found"
        last_ingestion = "No recent ingestion found"
        ingestion_candles = 0
        
        try:
            result = subprocess.run([
                "docker", "logs", "winu-bot-signal-worker", "--tail", "100"
            ], capture_output=True, text=True, timeout=10)
            
            logs = result.stdout
            has_errors = "ERROR" in logs
            has_warnings = "WARNING" in logs
            
            # Extract last scan and ingestion info
            for line in reversed(logs.split('\n')):
                if "Market scan completed" in line:
                    last_scan = line.strip()
                    break
            
            for line in reversed(logs.split('\n')):
                if "Data ingestion completed" in line:
                    last_ingestion = line.strip()
                    # Extract candle count from log
                    if "total_candles" in line:
                        try:
                            import re
                            match = re.search(r"'total_candles': (\d+)", line)
                            if match:
                                ingestion_candles = int(match.group(1))
                        except:
                            pass
                    break
                    
        except FileNotFoundError:
            # Docker not available in container
            has_errors = False
            has_warnings = False
            last_scan = "Docker not available in container"
            last_ingestion = "Docker not available in container"
        except Exception as e:
            has_errors = True
            has_warnings = True
            last_scan = f"Error: {str(e)}"
            last_ingestion = f"Error: {str(e)}"
        
        return {
            "api_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "health": {
                "services": {
                    "api": {"status": "healthy"},
                    "docker": docker_services
                }
            },
            "data_ingestion": {
                "status": "success",
                "total_candles": total_candles,
                "last_data_update": last_data_update,
                "active_assets": active_assets,
                "total_assets": total_assets,
                "candles": ingestion_candles
            },
            "recent_signals": len(recent_signals),
            "signal_generation": {
                "status": "success",
                "recent_signals": len(recent_signals),
                "signals_today": signals_today,
                "latest_signal": {
                    "symbol": recent_signals[0].symbol,
                    "direction": recent_signals[0].direction,
                    "created_at": recent_signals[0].created_at.isoformat()
                } if recent_signals else None
            },
            "worker_logs": {
                "status": "success",
                "has_errors": has_errors,
                "has_warnings": has_warnings,
                "last_scan": last_scan,
                "last_ingestion": last_ingestion,
                "ingestion_candles": ingestion_candles
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting system status: {str(e)}")

@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
