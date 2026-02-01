"""Global error monitoring and Discord alerting system."""

import os
import requests
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger


class ErrorMonitor:
    """Comprehensive error monitoring with Discord alerts."""
    
    def __init__(self):
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.discord_webhook)
        
        if self.enabled:
            logger.info(f"✅ Error monitoring enabled - Discord webhook configured")
        else:
            logger.warning("⚠️  Error monitoring disabled - No Discord webhook configured")
    
    def send_error_alert(
        self, 
        error: Exception, 
        context: str = "Unknown",
        severity: str = "ERROR",
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send error alert to Discord.
        
        Args:
            error: The exception that occurred
            context: Where the error occurred (e.g., "Signal Generation", "API Request")
            severity: ERROR, CRITICAL, WARNING
            additional_info: Extra information to include in the alert
        """
        if not self.enabled:
            logger.warning(f"Discord alert skipped (not configured): {context} - {error}")
            return False
        
        try:
            # Get error details
            error_type = type(error).__name__
            error_message = str(error)
            error_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            
            # Truncate traceback if too long (Discord has character limits)
            if len(error_traceback) > 1500:
                error_traceback = error_traceback[-1500:] + "\n...(truncated)"
            
            # Determine color based on severity
            color_map = {
                "CRITICAL": 0xFF0000,  # Red
                "ERROR": 0xFF6600,     # Orange-Red
                "WARNING": 0xFFCC00,   # Yellow
            }
            color = color_map.get(severity, 0xFF6600)
            
            # Build embed
            embed = {
                "title": f"🚨 {severity}: {error_type}",
                "description": f"**Context:** {context}\n**Error:** {error_message}",
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {
                        "name": "Traceback",
                        "value": f"```python\n{error_traceback[-1000:]}\n```",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Winu Bot Error Monitor"
                }
            }
            
            # Add additional info if provided
            if additional_info:
                for key, value in additional_info.items():
                    embed["fields"].append({
                        "name": key,
                        "value": str(value),
                        "inline": True
                    })
            
            payload = {
                "username": "Winu Bot Monitor",
                "embeds": [embed]
            }
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✅ Discord error alert sent: {context} - {error_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send Discord error alert: {e}")
            return False
    
    def send_custom_alert(
        self,
        title: str,
        message: str,
        severity: str = "INFO",
        fields: Optional[list] = None
    ) -> bool:
        """Send custom alert to Discord.
        
        Args:
            title: Alert title
            message: Alert message
            severity: INFO, SUCCESS, WARNING, ERROR, CRITICAL
            fields: List of {"name": "...", "value": "...", "inline": True/False}
        """
        if not self.enabled:
            return False
        
        try:
            color_map = {
                "SUCCESS": 0x00FF00,   # Green
                "INFO": 0x3498DB,      # Blue
                "WARNING": 0xFFCC00,   # Yellow
                "ERROR": 0xFF6600,     # Orange-Red
                "CRITICAL": 0xFF0000,  # Red
            }
            color = color_map.get(severity, 0x3498DB)
            
            # Icon map
            icon_map = {
                "SUCCESS": "✅",
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "🚨",
                "CRITICAL": "🔥",
            }
            icon = icon_map.get(severity, "📢")
            
            embed = {
                "title": f"{icon} {title}",
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Winu Bot Monitor"
                }
            }
            
            if fields:
                embed["fields"] = fields
            
            payload = {
                "username": "Winu Bot Monitor",
                "embeds": [embed]
            }
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✅ Discord alert sent: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send Discord alert: {e}")
            return False
    
    def send_system_status(self, services_status: Dict[str, Any]) -> bool:
        """Send system status update to Discord."""
        if not self.enabled:
            return False
        
        try:
            # Determine overall status
            all_healthy = all(
                status.get("status") == "healthy" or status.get("healthy") == True
                for status in services_status.values()
            )
            
            title = "✅ System Status: All Services Healthy" if all_healthy else "⚠️ System Status: Issues Detected"
            color = 0x00FF00 if all_healthy else 0xFF6600
            
            fields = []
            for service_name, status in services_status.items():
                is_healthy = status.get("status") == "healthy" or status.get("healthy") == True
                icon = "✅" if is_healthy else "❌"
                
                value = f"{icon} {status.get('message', 'OK')}"
                fields.append({
                    "name": service_name.replace("_", " ").title(),
                    "value": value,
                    "inline": True
                })
            
            embed = {
                "title": title,
                "description": f"System check performed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "fields": fields,
                "footer": {
                    "text": "Winu Bot System Monitor"
                }
            }
            
            payload = {
                "username": "Winu Bot Monitor",
                "embeds": [embed]
            }
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info("✅ Discord system status sent")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send Discord system status: {e}")
            return False


# Global instance
error_monitor = ErrorMonitor()


def monitor_errors(context: str = "Unknown", severity: str = "ERROR"):
    """Decorator to automatically monitor and report errors."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_monitor.send_error_alert(
                    error=e,
                    context=f"{context} ({func.__name__})",
                    severity=severity,
                    additional_info={
                        "Function": func.__name__,
                        "Args": str(args)[:100] if args else "None",
                        "Kwargs": str(kwargs)[:100] if kwargs else "None"
                    }
                )
                raise  # Re-raise the exception after reporting
        return wrapper
    return decorator


async def async_monitor_errors(context: str = "Unknown", severity: str = "ERROR"):
    """Async decorator to automatically monitor and report errors."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_monitor.send_error_alert(
                    error=e,
                    context=f"{context} ({func.__name__})",
                    severity=severity,
                    additional_info={
                        "Function": func.__name__,
                        "Args": str(args)[:100] if args else "None",
                        "Kwargs": str(kwargs)[:100] if kwargs else "None"
                    }
                )
                raise  # Re-raise the exception after reporting
        return wrapper
    return decorator





