#!/usr/bin/env python3
"""
Signal Analysis Cron - Analyzes data and generates signals every 1 hour.
"""

import asyncio
import aiohttp
import sys
import os
from datetime import datetime

class SignalAnalysisCron:
    def __init__(self):
        self.api_url = "https://api.winu.app"
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        
    async def trigger_signal_generation(self):
        """Trigger signal generation via API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/admin/generate-signals", timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Signal generation triggered: {data.get('message', 'Success')}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Signal generation failed: HTTP {response.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Error triggering signal generation: {e}")
            return False
    
    async def get_recent_signals(self):
        """Get recent signals to check results."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/signals/recent", timeout=10) as response:
                    if response.status == 200:
                        signals = await response.json()
                        return signals
                    else:
                        return []
        except Exception as e:
            print(f"⚠️  Could not fetch recent signals: {e}")
            return []
    
    async def send_signals_notification(self, signals):
        """Send signals notification to Discord."""
        if not self.discord_webhook or not signals:
            return
            
        # Format signals for Discord
        signal_text = ""
        for signal in signals[:5]:  # Show top 5 signals
            direction_emoji = "🟢" if signal.get('direction') == 'LONG' else "🔴"
            signal_text += f"{direction_emoji} **{signal.get('symbol')}** - {signal.get('direction')} (Score: {signal.get('score', 0):.2f})\n"
        
        payload = {
            "content": f"🚀 **NEW TRADING SIGNALS GENERATED** 🚀\n\n{signal_text}",
            "embeds": [{
                "title": "Signal Analysis Complete",
                "description": f"Generated {len(signals)} new trading signals",
                "color": 3447003,  # Blue color
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {"name": "Total Signals", "value": str(len(signals)), "inline": True},
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
    """Main signal analysis function."""
    print(f"🚀 Starting signal analysis at {datetime.utcnow()}")
    
    cron = SignalAnalysisCron()
    success = await cron.trigger_signal_generation()
    
    if success:
        # Wait a moment for signals to be generated
        await asyncio.sleep(5)
        
        # Get and display recent signals
        signals = await cron.get_recent_signals()
        if signals:
            print(f"📈 Generated {len(signals)} signals:")
            for signal in signals[:3]:
                print(f"  • {signal.get('symbol')} - {signal.get('direction')} (Score: {signal.get('score', 0):.2f})")
            
            await cron.send_signals_notification(signals)
        else:
            print("⚠️  No new signals generated")
        
        print("✅ Signal analysis completed successfully")
    else:
        print("❌ Signal analysis failed")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
