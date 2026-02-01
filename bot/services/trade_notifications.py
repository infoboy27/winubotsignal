"""
Trade Notification Service
Sends trade notifications to Discord with beautiful embeds
"""

import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

# Discord webhook URL for trade notifications
DISCORD_TRADES_WEBHOOK = "https://discord.com/api/webhooks/1425590291473105198/dluoZ5n-eoW_iqn3ZFa64kNQG4GX80946ZmRIvOxOgybS1ufpNlAC4uH5YmMUaEYE3qI"


class TradeNotificationService:
    """Sends trade notifications to Discord."""
    
    def __init__(self, webhook_url: str = DISCORD_TRADES_WEBHOOK):
        self.webhook_url = webhook_url
    
    async def send_order_notification(
        self,
        order_data: Dict,
        status: str = "success"
    ):
        """
        Send order notification to Discord.
        
        Args:
            order_data: Order details
            status: success, failed, pending
        """
        try:
            # Determine color based on status
            colors = {
                "success": 0x00FF00,  # Green
                "filled": 0x00FF00,   # Green
                "failed": 0xFF0000,   # Red
                "error": 0xFF0000,    # Red
                "pending": 0xFFFF00,  # Yellow
                "submitted": 0x0099FF # Blue
            }
            
            color = colors.get(status.lower(), 0x808080)  # Gray default
            
            # Build embed based on status
            if status.lower() in ["success", "filled"]:
                title = "✅ Order Filled"
                description = f"Order executed successfully on **{order_data.get('account_name', 'Unknown')}**"
            elif status.lower() in ["failed", "error"]:
                title = "❌ Order Failed"
                description = f"Order failed on **{order_data.get('account_name', 'Unknown')}**"
            else:
                title = "📊 Order Submitted"
                description = f"Order submitted on **{order_data.get('account_name', 'Unknown')}**"
            
            # Build fields
            fields = [
                {"name": "Symbol", "value": order_data.get('symbol', 'N/A'), "inline": True},
                {"name": "Side", "value": order_data.get('side', 'N/A').upper(), "inline": True},
                {"name": "Type", "value": order_data.get('order_type', 'MARKET'), "inline": True},
            ]
            
            # Add quantity and price
            if order_data.get('quantity'):
                fields.append({
                    "name": "Quantity",
                    "value": f"{float(order_data['quantity']):.6f}",
                    "inline": True
                })
            
            if order_data.get('average_price') or order_data.get('price'):
                price = order_data.get('average_price') or order_data.get('price')
                fields.append({
                    "name": "Price",
                    "value": f"${float(price):,.2f}",
                    "inline": True
                })
            
            # Add position size
            if order_data.get('position_size_usd'):
                fields.append({
                    "name": "Position Size",
                    "value": f"${float(order_data['position_size_usd']):,.2f}",
                    "inline": True
                })
            
            # Add leverage
            if order_data.get('leverage'):
                fields.append({
                    "name": "Leverage",
                    "value": f"{float(order_data['leverage'])}x",
                    "inline": True
                })
            
            # Add stop loss and take profit
            if order_data.get('stop_loss'):
                fields.append({
                    "name": "Stop Loss",
                    "value": f"${float(order_data['stop_loss']):,.2f}",
                    "inline": True
                })
            
            if order_data.get('take_profit'):
                fields.append({
                    "name": "Take Profit",
                    "value": f"${float(order_data['take_profit']):,.2f}",
                    "inline": True
                })
            
            # Add balance if available
            if order_data.get('current_balance'):
                fields.append({
                    "name": "Account Balance",
                    "value": f"${float(order_data['current_balance']):,.2f}",
                    "inline": True
                })
            
            # Add error message if failed
            if status.lower() in ["failed", "error"] and order_data.get('error_message'):
                fields.append({
                    "name": "Error",
                    "value": order_data['error_message'][:1000],  # Limit length
                    "inline": False
                })
            
            # Add exchange order ID if available
            if order_data.get('exchange_order_id'):
                fields.append({
                    "name": "Order ID",
                    "value": str(order_data['exchange_order_id']),
                    "inline": False
                })
            
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": f"User ID: {order_data.get('user_id', 'N/A')} | Account: {order_data.get('account_name', 'N/A')}"
                }
            }
            
            payload = {"embeds": [embed]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info(f"✅ Discord notification sent for {order_data.get('symbol')} on {order_data.get('account_name')}")
                    else:
                        error_text = await response.text()
                        logger.warning(f"⚠️  Discord notification failed: {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"❌ Error sending Discord notification: {e}")
    
    async def send_signal_summary(
        self,
        signal: Dict,
        results: List[Dict]
    ):
        """
        Send summary notification for signal executed across multiple accounts.
        
        Args:
            signal: Signal data
            results: List of execution results per account
        """
        try:
            successful = [r for r in results if r.get('success', False)]
            failed = [r for r in results if not r.get('success', False)]
            
            # Determine color
            if len(failed) == 0:
                color = 0x00FF00  # All success - green
            elif len(successful) == 0:
                color = 0xFF0000  # All failed - red
            else:
                color = 0xFFAA00  # Mixed - orange
            
            title = f"📊 Signal Executed: {signal.get('symbol', 'N/A')} {signal.get('direction', 'N/A')}"
            
            description = f"**Accounts**: {len(successful)}/{len(results)} filled successfully"
            
            fields = []
            
            # Add signal details
            fields.append({
                "name": "Signal Info",
                "value": (
                    f"Score: {signal.get('quality_score', 0)*100:.1f}%\n"
                    f"Timeframe: {signal.get('timeframe', 'N/A')}\n"
                    f"Entry: ${float(signal.get('entry_price', 0)):,.2f}"
                ),
                "inline": True
            })
            
            # Add successful accounts
            if successful:
                success_list = "\n".join([
                    f"✅ {r.get('account_name', 'Unknown')}" 
                    for r in successful[:5]  # Limit to 5
                ])
                if len(successful) > 5:
                    success_list += f"\n... and {len(successful) - 5} more"
                
                fields.append({
                    "name": f"Successful ({len(successful)})",
                    "value": success_list,
                    "inline": True
                })
            
            # Add failed accounts
            if failed:
                failed_list = "\n".join([
                    f"❌ {r.get('account_name', 'Unknown')}: {r.get('error', 'Unknown')[:50]}" 
                    for r in failed[:5]  # Limit to 5
                ])
                if len(failed) > 5:
                    failed_list += f"\n... and {len(failed) - 5} more"
                
                fields.append({
                    "name": f"Failed ({len(failed)})",
                    "value": failed_list,
                    "inline": False
                })
            
            # Calculate total position size
            total_position_size = sum([
                float(r.get('position_size_usd', 0)) 
                for r in successful
            ])
            
            if total_position_size > 0:
                fields.append({
                    "name": "Total Position Size",
                    "value": f"${total_position_size:,.2f}",
                    "inline": True
                })
            
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Multi-Account Trading System"}
            }
            
            payload = {"embeds": [embed]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info(f"✅ Discord signal summary sent: {len(successful)}/{len(results)} accounts")
                    else:
                        error_text = await response.text()
                        logger.warning(f"⚠️  Discord summary failed: {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"❌ Error sending Discord summary: {e}")
    
    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None
    ):
        """
        Send error notification to Discord.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context
        """
        try:
            embed = {
                "title": f"⚠️  {error_type}",
                "description": error_message[:2000],
                "color": 0xFF0000,  # Red
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Multi-Account Trading System"}
            }
            
            if context:
                fields = []
                for key, value in context.items():
                    if len(fields) < 25:  # Discord limit
                        fields.append({
                            "name": str(key),
                            "value": str(value)[:1024],
                            "inline": True
                        })
                embed["fields"] = fields
            
            payload = {"embeds": [embed]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 204:
                        error_text = await response.text()
                        logger.warning(f"⚠️  Discord error notification failed: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ Error sending error notification: {e}")


# Singleton instance
_notification_service = None

def get_notification_service() -> TradeNotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = TradeNotificationService()
    return _notification_service

