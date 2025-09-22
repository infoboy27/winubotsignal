"""Alert sending tasks for Telegram and Discord."""

import json
import sys
from typing import Optional
import requests
from loguru import logger

sys.path.append('/packages')

from common.config import get_settings
from common.database import Signal
from common.utils import create_alert_message

settings = get_settings()


class AlertSenderTask:
    """Handle sending alerts via various channels."""
    
    def __init__(self):
        self.telegram_token = settings.messaging.telegram_bot_token
        self.telegram_chat_id = settings.messaging.telegram_chat_id
        self.discord_webhook = settings.messaging.discord_webhook_url
    
    def send_telegram_alert(self, signal: Signal) -> bool:
        """Send alert via Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        
        try:
            # Create message
            signal_dict = {
                'symbol': signal.symbol,
                'direction': signal.direction,
                'timeframe': signal.timeframe,
                'score': signal.score,
                'entry_price': str(signal.entry_price) if signal.entry_price else 'Market',
                'stop_loss': str(signal.stop_loss) if signal.stop_loss else 'N/A',
                'take_profit_1': str(signal.take_profit_1) if signal.take_profit_1 else 'N/A',
                'take_profit_2': str(signal.take_profit_2) if signal.take_profit_2 else 'N/A',
                'take_profit_3': str(signal.take_profit_3) if signal.take_profit_3 else 'N/A',
                'risk_reward_ratio': signal.risk_reward_ratio or 'N/A',
                'confluences': signal.confluences or {},
                'created_at': signal.created_at.isoformat()
            }
            
            message = create_alert_message(signal_dict)
            
            # Send via Telegram Bot API
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram alert sent for signal {signal.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert for signal {signal.id}: {e}")
            return False
    
    def send_discord_alert(self, signal: Signal) -> bool:
        """Send alert via Discord webhook."""
        if not self.discord_webhook:
            logger.warning("Discord webhook not configured")
            return False
        
        try:
            # Create message
            signal_dict = {
                'symbol': signal.symbol,
                'direction': signal.direction,
                'timeframe': signal.timeframe,
                'score': signal.score,
                'entry_price': str(signal.entry_price) if signal.entry_price else 'Market',
                'stop_loss': str(signal.stop_loss) if signal.stop_loss else 'N/A',
                'take_profit_1': str(signal.take_profit_1) if signal.take_profit_1 else 'N/A',
                'take_profit_2': str(signal.take_profit_2) if signal.take_profit_2 else 'N/A',
                'take_profit_3': str(signal.take_profit_3) if signal.take_profit_3 else 'N/A',
                'risk_reward_ratio': signal.risk_reward_ratio or 'N/A',
                'confluences': signal.confluences or {},
                'created_at': signal.created_at.isoformat()
            }
            
            message = create_alert_message(signal_dict)
            
            # Create Discord embed
            embed = {
                "title": f"🚨 New Trading Signal - {signal.symbol}",
                "description": message,
                "color": 0x00ff00 if signal.direction == 'LONG' else 0xff0000,
                "timestamp": signal.created_at.isoformat(),
                "footer": {
                    "text": "Million Trader - Not financial advice"
                }
            }
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Discord alert sent for signal {signal.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Discord alert for signal {signal.id}: {e}")
            return False

