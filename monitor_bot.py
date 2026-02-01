#!/usr/bin/env python3
"""
Winu Bot Signal Monitoring System
Real-time monitoring of bot activity, data ingestion, and signal generation
"""

import requests
import json
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import subprocess

class WinuBotMonitor:
    def __init__(self):
        self.api_base = "https://winu.app/api"
        self.dashboard_url = "https://dashboard.winu.app"
        self.admin_url = "https://winu.app/admin"
        
    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "data_ingestion": {},
            "signal_generation": {},
            "alerts": {},
            "overall_status": "unknown"
        }
        
        # Check API health
        try:
            response = requests.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                health_status["services"]["api"] = response.json()
            else:
                health_status["services"]["api"] = {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            health_status["services"]["api"] = {"status": "error", "error": str(e)}
        
        # Check Docker services
        try:
            result = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"], 
                                  capture_output=True, text=True, timeout=10)
            services = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    name, status = line.split('\t', 1)
                    services[name] = status
            health_status["services"]["docker"] = services
        except Exception as e:
            health_status["services"]["docker"] = {"error": str(e)}
        
        return health_status
    
    def check_data_ingestion(self) -> Dict[str, Any]:
        """Check data ingestion status"""
        try:
            # Get recent OHLCV data count
            response = requests.get(f"{self.api_base}/admin/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                return {
                    "status": "success",
                    "total_candles": stats.get("totalCandles", 0),
                    "last_data_update": stats.get("lastDataUpdate"),
                    "active_assets": stats.get("activeAssets", 0),
                    "total_assets": stats.get("totalAssets", 0)
                }
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_signal_generation(self) -> Dict[str, Any]:
        """Check signal generation status"""
        try:
            # Get recent signals
            response = requests.get(f"{self.api_base}/signals/recent?limit=10", timeout=10)
            if response.status_code == 200:
                signals = response.json()
                return {
                    "status": "success",
                    "recent_signals": len(signals),
                    "latest_signal": signals[0] if signals else None,
                    "signals_today": len([s for s in signals if s.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
                }
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_worker_logs(self) -> Dict[str, Any]:
        """Check worker logs for recent activity"""
        try:
            # Get recent worker logs
            result = subprocess.run([
                "docker", "logs", "winu-bot-signal-worker", "--tail", "50"
            ], capture_output=True, text=True, timeout=10)
            
            logs = result.stdout
            return {
                "status": "success",
                "recent_logs": logs,
                "has_errors": "ERROR" in logs,
                "has_warnings": "WARNING" in logs,
                "last_scan": self._extract_last_scan(logs),
                "last_ingestion": self._extract_last_ingestion(logs)
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
    
    def trigger_data_ingestion(self) -> Dict[str, Any]:
        """Manually trigger data ingestion"""
        try:
            response = requests.post(f"{self.api_base}/admin/ingest-data", timeout=30)
            if response.status_code == 200:
                return {"status": "success", "message": "Data ingestion triggered"}
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def trigger_signal_generation(self) -> Dict[str, Any]:
        """Manually trigger signal generation"""
        try:
            response = requests.post(f"{self.api_base}/admin/generate-signals", timeout=30)
            if response.status_code == 200:
                return {"status": "success", "message": "Signal generation triggered"}
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        print("🔍 Checking system health...")
        health = self.check_system_health()
        
        print("📊 Checking data ingestion...")
        data_status = self.check_data_ingestion()
        
        print("📈 Checking signal generation...")
        signal_status = self.check_signal_generation()
        
        print("📋 Checking worker logs...")
        log_status = self.check_worker_logs()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "data_ingestion": data_status,
            "signal_generation": signal_status,
            "worker_logs": log_status
        }
    
    def print_status_report(self, status: Dict[str, Any]):
        """Print a formatted status report"""
        print("\n" + "="*60)
        print("🤖 WINU BOT SIGNAL - SYSTEM STATUS REPORT")
        print("="*60)
        print(f"📅 Time: {status['timestamp']}")
        
        # Health Status
        print("\n🏥 SYSTEM HEALTH:")
        api_status = status['health']['services'].get('api', {})
        if api_status.get('status') == 'healthy':
            print("   ✅ API: Healthy")
        else:
            print(f"   ❌ API: {api_status.get('status', 'Unknown')}")
        
        # Data Ingestion Status
        print("\n📊 DATA INGESTION:")
        data = status['data_ingestion']
        if data['status'] == 'success':
            print(f"   📈 Total Candles: {data.get('total_candles', 0):,}")
            print(f"   🔄 Active Assets: {data.get('active_assets', 0)}")
            print(f"   📅 Last Update: {data.get('last_data_update', 'Unknown')}")
        else:
            print(f"   ❌ Error: {data.get('message', 'Unknown error')}")
        
        # Signal Generation Status
        print("\n📈 SIGNAL GENERATION:")
        signals = status['signal_generation']
        if signals['status'] == 'success':
            print(f"   📊 Recent Signals: {signals.get('recent_signals', 0)}")
            print(f"   📅 Signals Today: {signals.get('signals_today', 0)}")
            if signals.get('latest_signal'):
                latest = signals['latest_signal']
                print(f"   🎯 Latest: {latest.get('symbol', 'N/A')} - {latest.get('direction', 'N/A')}")
        else:
            print(f"   ❌ Error: {signals.get('message', 'Unknown error')}")
        
        # Worker Logs Status
        print("\n🔧 WORKER STATUS:")
        logs = status['worker_logs']
        if logs['status'] == 'success':
            print(f"   📋 Last Scan: {logs.get('last_scan', 'Unknown')}")
            print(f"   📊 Last Ingestion: {logs.get('last_ingestion', 'Unknown')}")
            if logs.get('has_errors'):
                print("   ⚠️  Has Errors: Yes")
            if logs.get('has_warnings'):
                print("   ⚠️  Has Warnings: Yes")
        else:
            print(f"   ❌ Error: {logs.get('message', 'Unknown error')}")
        
        print("\n" + "="*60)
    
    def monitor_continuously(self, interval: int = 60):
        """Continuously monitor the system"""
        print(f"🔄 Starting continuous monitoring (every {interval} seconds)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                status = self.get_comprehensive_status()
                self.print_status_report(status)
                
                # Check if system needs attention
                if self._needs_attention(status):
                    print("\n🚨 ATTENTION NEEDED!")
                    self._handle_issues(status)
                
                print(f"\n⏰ Next check in {interval} seconds...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
    
    def _needs_attention(self, status: Dict[str, Any]) -> bool:
        """Check if system needs attention"""
        # Check for errors
        if status['worker_logs'].get('has_errors'):
            return True
        
        # Check if no data is being ingested
        data = status['data_ingestion']
        if data.get('total_candles', 0) == 0:
            return True
        
        # Check if no signals are being generated
        signals = status['signal_generation']
        if signals.get('recent_signals', 0) == 0:
            return True
        
        return False
    
    def _handle_issues(self, status: Dict[str, Any]):
        """Handle detected issues"""
        print("🔧 Attempting to fix issues...")
        
        # Try to trigger data ingestion
        print("📊 Triggering data ingestion...")
        result = self.trigger_data_ingestion()
        if result['status'] == 'success':
            print("   ✅ Data ingestion triggered")
        else:
            print(f"   ❌ Failed: {result['message']}")
        
        # Try to trigger signal generation
        print("📈 Triggering signal generation...")
        result = self.trigger_signal_generation()
        if result['status'] == 'success':
            print("   ✅ Signal generation triggered")
        else:
            print(f"   ❌ Failed: {result['message']}")

def main():
    monitor = WinuBotMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            status = monitor.get_comprehensive_status()
            monitor.print_status_report(status)
            
        elif command == "ingest":
            result = monitor.trigger_data_ingestion()
            print(f"Data ingestion: {result}")
            
        elif command == "signals":
            result = monitor.trigger_signal_generation()
            print(f"Signal generation: {result}")
            
        elif command == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            monitor.monitor_continuously(interval)
            
        else:
            print("Usage: python monitor_bot.py [status|ingest|signals|monitor] [interval]")
    else:
        # Default: show status
        status = monitor.get_comprehensive_status()
        monitor.print_status_report(status)

if __name__ == "__main__":
    main()





