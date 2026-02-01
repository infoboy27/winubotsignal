#!/usr/bin/env python3
"""
System Monitor - Checks system health every 5 minutes and sends Discord alerts if down.
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add packages to path
sys.path.append('/packages')

class SystemMonitor:
    def __init__(self):
        self.api_url = "https://api.winu.app"
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.alert_cooldown = {}  # Track last alert time per service
        
    async def check_api_health(self) -> Dict[str, Any]:
        """Check API health status."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "healthy",
                            "data": data,
                            "response_time": response.headers.get('X-Response-Time', 'N/A')
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}",
                            "data": None
                        }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "data": None
            }
    
    async def check_services(self) -> Dict[str, Any]:
        """Check all critical services."""
        services = {}
        
        # Check API
        api_health = await self.check_api_health()
        services['api'] = api_health
        
        # Check if we can get recent signals (indicates worker is running)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/signals/recent", timeout=10) as response:
                    if response.status == 200:
                        signals = await response.json()
                        services['worker'] = {
                            "status": "healthy",
                            "recent_signals": len(signals),
                            "data": signals[:3] if signals else []
                        }
                    else:
                        services['worker'] = {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            services['worker'] = {
                "status": "error",
                "error": str(e)
            }
        
        return services
    
    async def send_discord_alert(self, message: str, service: str = "system"):
        """Send alert to Discord."""
        if not self.discord_webhook:
            print(f"⚠️  Discord webhook not configured. Alert: {message}")
            return
        
        # Check cooldown (don't spam alerts)
        now = datetime.utcnow()
        last_alert = self.alert_cooldown.get(service)
        if last_alert and (now - last_alert).seconds < 300:  # 5 minutes cooldown
            return
        
        self.alert_cooldown[service] = now
        
        payload = {
            "content": f"🚨 **WINU BOT ALERT** 🚨\n{message}",
            "embeds": [{
                "title": "System Alert",
                "description": message,
                "color": 15158332,  # Red color
                "timestamp": now.isoformat(),
                "fields": [
                    {"name": "Service", "value": service, "inline": True},
                    {"name": "Time", "value": now.strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
                ]
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook, json=payload, timeout=10) as response:
                    if response.status == 204:
                        print(f"✅ Discord alert sent: {message}")
                    else:
                        print(f"❌ Failed to send Discord alert: {response.status}")
        except Exception as e:
            print(f"❌ Error sending Discord alert: {e}")
    
    async def run_monitor(self):
        """Run system monitoring."""
        print(f"🔍 Starting system monitor at {datetime.utcnow()}")
        
        services = await self.check_services()
        
        # Check for issues
        issues = []
        
        for service_name, service_data in services.items():
            if service_data['status'] != 'healthy':
                issues.append(f"{service_name.upper()}: {service_data.get('error', 'Unknown error')}")
        
        if issues:
            alert_message = f"System issues detected:\n" + "\n".join(f"• {issue}" for issue in issues)
            await self.send_discord_alert(alert_message, "system")
            print(f"❌ System issues: {', '.join(issues)}")
        else:
            print("✅ All systems healthy")
        
        # Log status
        print(f"📊 System Status:")
        for service_name, service_data in services.items():
            status_emoji = "✅" if service_data['status'] == 'healthy' else "❌"
            print(f"  {status_emoji} {service_name.upper()}: {service_data['status']}")
        
        return len(issues) == 0

async def main():
    """Main monitoring function."""
    monitor = SystemMonitor()
    success = await monitor.run_monitor()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())





