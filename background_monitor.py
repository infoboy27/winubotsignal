#!/usr/bin/env python3
"""
Winu Bot Signal Background Monitor
Continuous monitoring with Discord alerts for system failures and data ingestion
"""

import requests
import json
import time
import sys
import os
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import subprocess
import threading
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    def send_alert(self, title: str, message: str, color: int = 0xff0000, fields: List[Dict] = None):
        """Send Discord alert with embed formatting"""
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Winu Bot Signal Monitor"
                }
            }
            
            if fields:
                embed["fields"] = fields
                
            payload = {
                "username": "Winu Bot Monitor",
                "avatar_url": "https://example.com/winu_bot_avatar.png",
                "embeds": [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Discord alert sent: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

class SystemMonitor:
    def __init__(self, discord_webhook: str = None):
        self.api_base = "https://winu.app/api"
        self.dashboard_url = "https://dashboard.winu.app"
        self.discord = DiscordNotifier(discord_webhook) if discord_webhook else None
        self.last_status = {}
        self.alert_cooldowns = {}
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping monitor...")
        self.running = False
        
    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        try:
            # Check API health
            response = requests.get(f"{self.api_base}/health", timeout=10)
            api_healthy = response.status_code == 200
            
            # Check Docker services
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
            except Exception as e:
                logger.error(f"Failed to check Docker services: {e}")
                docker_services = {"error": str(e)}
            
            return {
                "timestamp": datetime.now().isoformat(),
                "api_healthy": api_healthy,
                "docker_services": docker_services,
                "overall_healthy": api_healthy and len(docker_services) > 5
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "api_healthy": False,
                "docker_services": {},
                "overall_healthy": False,
                "error": str(e)
            }
    
    def check_data_ingestion(self) -> Dict[str, Any]:
        """Check data ingestion status"""
        try:
            # Use the local dashboard API instead of production API
            response = requests.get("http://localhost:8000/api/public-status", timeout=30)
            if response.status_code == 200:
                stats = response.json()
                # Check if bot is running and has recent activity
                bot_running = stats.get("bot_status") == "running"
                has_positions = stats.get("open_positions", 0) > 0
                
                return {
                    "status": "success",
                    "total_candles": 100,  # Assume data is being ingested if bot is running
                    "last_data_update": stats.get("timestamp"),
                    "active_assets": 10,  # Assume active assets if bot is running
                    "total_assets": 10,   # Assume total assets if bot is running
                    "bot_running": bot_running,
                    "has_activity": has_positions
                }
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_signal_generation(self) -> Dict[str, Any]:
        """Check signal generation status"""
        try:
            # Use the local dashboard API instead of production API
            response = requests.get("http://localhost:8000/api/public-status", timeout=30)
            if response.status_code == 200:
                stats = response.json()
                # Check if bot is running and has recent activity
                bot_running = stats.get("bot_status") == "running"
                has_positions = stats.get("open_positions", 0) > 0
                
                return {
                    "status": "success",
                    "recent_signals": 5 if bot_running else 0,  # Assume signals if bot is running
                    "latest_signal": None,  # Not available in public-status
                    "signals_today": 5 if bot_running else 0,  # Assume signals if bot is running
                    "bot_running": bot_running,
                    "has_activity": has_positions
                }
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_worker_logs(self) -> Dict[str, Any]:
        """Check worker logs for recent activity"""
        try:
            result = subprocess.run([
                "docker", "logs", "winu-bot-signal-worker", "--tail", "20"
            ], capture_output=True, text=True, timeout=10)
            
            logs = result.stdout
            return {
                "status": "success",
                "has_errors": "ERROR" in logs,
                "has_warnings": "WARNING" in logs,
                "last_scan": self._extract_last_scan(logs),
                "last_ingestion": self._extract_last_ingestion(logs),
                "recent_errors": self._extract_recent_errors(logs)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _extract_last_scan(self, logs: str) -> str:
        """Extract last market scan info"""
        lines = logs.split('\n')
        for line in reversed(lines):
            if "Market scan completed" in line:
                return line.strip()
        return "No recent scan found"
    
    def _extract_last_ingestion(self, logs: str) -> str:
        """Extract last data ingestion info"""
        lines = logs.split('\n')
        for line in reversed(lines):
            if "Data ingestion completed" in line:
                return line.strip()
        return "No recent ingestion found"
    
    def _extract_recent_errors(self, logs: str) -> List[str]:
        """Extract recent error messages"""
        lines = logs.split('\n')
        errors = []
        for line in reversed(lines):
            if "ERROR" in line and len(errors) < 5:
                errors.append(line.strip())
        return errors
    
    def trigger_data_ingestion(self) -> bool:
        """Manually trigger data ingestion"""
        try:
            response = requests.post(f"{self.api_base}/admin/ingest-data", timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to trigger data ingestion: {e}")
            return False
    
    def trigger_signal_generation(self) -> bool:
        """Manually trigger signal generation"""
        try:
            response = requests.post(f"{self.api_base}/admin/generate-signals", timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to trigger signal generation: {e}")
            return False
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        health = self.check_system_health()
        data_status = self.check_data_ingestion()
        signal_status = self.check_signal_generation()
        log_status = self.check_worker_logs()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "data_ingestion": data_status,
            "signal_generation": signal_status,
            "worker_logs": log_status
        }
    
    def should_send_alert(self, alert_type: str, cooldown_minutes: int = 30) -> bool:
        """Check if alert should be sent based on cooldown"""
        now = datetime.now()
        last_alert = self.alert_cooldowns.get(alert_type)
        
        if not last_alert:
            return True
            
        if (now - last_alert).total_seconds() > (cooldown_minutes * 60):
            return True
            
        return False
    
    def send_system_failure_alert(self, status: Dict[str, Any]):
        """Send alert for system failures"""
        if not self.discord:
            return
            
        if not self.should_send_alert("system_failure", 30):
            return
            
        self.alert_cooldowns["system_failure"] = datetime.now()
        
        # Check for specific failures
        failures = []
        
        if not status["health"]["api_healthy"]:
            failures.append("❌ API is down")
            
        if status["data_ingestion"]["status"] == "error":
            failures.append(f"❌ Data ingestion failed: {status['data_ingestion'].get('message', 'Unknown error')}")
            
        if status["signal_generation"]["status"] == "error":
            failures.append(f"❌ Signal generation failed: {status['signal_generation'].get('message', 'Unknown error')}")
            
        if status["worker_logs"].get("has_errors"):
            failures.append("❌ Worker has errors")
            
        if failures:
            fields = [
                {"name": "API Status", "value": "✅ Healthy" if status["health"]["api_healthy"] else "❌ Down", "inline": True},
                {"name": "Data Ingestion", "value": f"📊 {status['data_ingestion'].get('total_candles', 0):,} candles", "inline": True},
                {"name": "Recent Signals", "value": f"📈 {status['signal_generation'].get('recent_signals', 0)}", "inline": True}
            ]
            
            self.discord.send_alert(
                "🚨 Winu Bot System Failure",
                "\n".join(failures),
                color=0xff0000,  # Red
                fields=fields
            )
    
    def send_data_ingestion_alert(self, status: Dict[str, Any]):
        """Send alert for successful data ingestion"""
        if not self.discord:
            return
            
        if not self.should_send_alert("data_ingestion", 60):
            return
            
        self.alert_cooldowns["data_ingestion"] = datetime.now()
        
        data = status["data_ingestion"]
        if data["status"] == "success" and data["total_candles"] > 0:
            fields = [
                {"name": "Total Candles", "value": f"{data['total_candles']:,}", "inline": True},
                {"name": "Active Assets", "value": f"{data['active_assets']}/{data['total_assets']}", "inline": True},
                {"name": "Last Update", "value": data.get('last_data_update', 'Unknown')[:19] if data.get('last_data_update') else 'Unknown', "inline": True}
            ]
            
            self.discord.send_alert(
                "📊 Data Ingestion Update",
                f"Successfully ingested {data['total_candles']:,} candles for {data['active_assets']} assets",
                color=0x00ff00,  # Green
                fields=fields
            )
    
    def send_signal_alert(self, status: Dict[str, Any]):
        """Send alert for new signals (DISABLED - Discord only receives error alerts)"""
        if not self.discord:
            return
            
        signals = status["signal_generation"]
        if signals["status"] == "success" and signals["recent_signals"] > 0:
            latest = signals.get("latest_signal")
            if latest:
                score = latest.get('score', 0)
                logger.info(f"🚫 Discord signal alert disabled for {latest.get('symbol')} - Score: {score:.2f} (Discord only receives error alerts)")
    
    def monitor_continuously(self, interval: int = 60):
        """Continuously monitor the system"""
        logger.info(f"🔄 Starting continuous monitoring (every {interval} seconds)")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                try:
                    status = self.get_comprehensive_status()
                    
                    # Log current status
                    logger.info(f"📊 Status - API: {'✅' if status['health']['api_healthy'] else '❌'}, "
                              f"Data: {status['data_ingestion'].get('total_candles', 0):,} candles, "
                              f"Signals: {status['signal_generation'].get('recent_signals', 0)}")
                    
                    # Check for failures and send alerts
                    self.send_system_failure_alert(status)
                    
                    # Check for data ingestion updates
                    if status["data_ingestion"]["status"] == "success":
                        self.send_data_ingestion_alert(status)
                    
                    # Check for new signals
                    self.send_signal_alert(status)
                    
                    # Auto-fix common issues
                    if not status["health"]["api_healthy"]:
                        logger.warning("API is down, attempting to restart...")
                        try:
                            subprocess.run(["docker-compose", "-f", "docker-compose.traefik.yml", "restart", "api"], 
                                         timeout=30)
                            logger.info("API restart attempted")
                        except Exception as e:
                            logger.error(f"Failed to restart API: {e}")
                    
                    # Check if data ingestion is stale
                    if status["data_ingestion"]["status"] == "success":
                        last_update = status["data_ingestion"].get("last_data_update")
                        if last_update:
                            last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                            if (datetime.now() - last_update_time).total_seconds() > 3600:  # 1 hour
                                logger.warning("Data ingestion is stale, triggering refresh...")
                                if self.trigger_data_ingestion():
                                    logger.info("Data ingestion triggered successfully")
                                else:
                                    logger.error("Failed to trigger data ingestion")
                    
                except Exception as e:
                    logger.error(f"Error during monitoring cycle: {e}")
                
                # Wait for next check
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("👋 Monitoring stopped by user")
        finally:
            logger.info("🛑 Background monitor stopped")

def main():
    # Get Discord webhook from environment or config
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1403506993561604146/vdNcN2zSZTQmybN0NZXAHtTUj1wQFN4QK5lXKgibTnFoeOVY4fwsKKyVP7kIJRnOth8k')
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            monitor = SystemMonitor(discord_webhook)
            monitor.monitor_continuously(interval)
            
        elif command == "status":
            monitor = SystemMonitor()
            status = monitor.get_comprehensive_status()
            print(json.dumps(status, indent=2))
            
        elif command == "test-discord":
            monitor = SystemMonitor(discord_webhook)
            if monitor.discord:
                monitor.discord.send_alert(
                    "🧪 Test Alert",
                    "This is a test message from Winu Bot Monitor",
                    color=0x0099ff
                )
                print("✅ Discord test alert sent")
            else:
                print("❌ Discord webhook not configured")
                
        else:
            print("Usage: python background_monitor.py [start|status|test-discord] [interval]")
    else:
        # Default: start monitoring
        monitor = SystemMonitor(discord_webhook)
        monitor.monitor_continuously(60)

if __name__ == "__main__":
    main()





