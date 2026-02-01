#!/usr/bin/env python3
"""
Data Ingestion Cron - Fetches fresh market data every 10 minutes.
"""

import asyncio
import aiohttp
import sys
import os
from datetime import datetime

class DataIngestionCron:
    def __init__(self):
        # Use HTTPS API endpoint
        self.api_url = "https://api.winu.app"
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        # SSL context to allow self-signed certificates
        import ssl
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    async def trigger_data_ingestion(self):
        """Trigger data ingestion via API."""
        try:
            import aiohttp
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(f"{self.api_url}/admin/ingest-data", timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Data ingestion triggered: {data.get('message', 'Success')}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Data ingestion failed: HTTP {response.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Error triggering data ingestion: {e}")
            return False
    
    async def send_success_notification(self):
        """Send success notification to Discord."""
        if not self.discord_webhook:
            return
            
        payload = {
            "content": "📊 **Data Ingestion Complete**",
            "embeds": [{
                "title": "Market Data Updated",
                "description": "Fresh market data has been ingested from Binance, Gate.io, and CoinMarketCap",
                "color": 3066993,  # Green color
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {"name": "Status", "value": "✅ Success", "inline": True},
                    {"name": "Time", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
                ]
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook, json=payload, timeout=10) as response:
                    if response.status == 204:
                        print("✅ Discord notification sent")
        except Exception as e:
            print(f"⚠️  Could not send Discord notification: {e}")

async def main():
    """Main data ingestion function."""
    print(f"📊 Starting data ingestion at {datetime.utcnow()}")
    
    cron = DataIngestionCron()
    success = await cron.trigger_data_ingestion()
    
    if success:
        await cron.send_success_notification()
        print("✅ Data ingestion completed successfully")
    else:
        print("❌ Data ingestion failed")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
