"""Modern signal worker with multi-source analysis."""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from loguru import logger

sys.path.append('/packages')

from common.config import get_settings
from common.database import Asset, Signal, Alert
from common.schemas import SignalType, SignalDirection, AlertChannel
from packages.signals.multi_source_analyzer import MultiSourceAnalyzer
from packages.signals.modern_signal import ModernSignal
from tasks.alert_sender import AlertSenderTask


class ModernSignalWorker:
    """Enhanced signal worker with modern analysis and multi-source data."""
    
    def __init__(self):
        self.settings = get_settings()
        self.alert_sender = AlertSenderTask()
        
        # Initialize multi-source analyzer
        self.analyzer = MultiSourceAnalyzer(
            binance_api_key=self.settings.exchange.binance_api_key,
            binance_secret=self.settings.exchange.binance_api_secret,
            gate_api_key=self.settings.exchange.gate_api_key,
            gate_secret=self.settings.exchange.gate_api_secret,
            cmc_api_key=self.settings.market_data.cmc_api_key
        )
    
    async def scan_markets_modern(self, db_session) -> Dict:
        """Scan markets using modern multi-source analysis."""
        logger.info("Starting modern market scan...")
        
        try:
            # Get active assets
            assets = db_session.execute(
                "SELECT * FROM assets WHERE active = true LIMIT 10"
            ).fetchall()
            
            if not assets:
                logger.warning("No active assets found")
                return {"status": "no_assets", "signals_generated": 0}
            
            # Extract symbols
            symbols = [asset.symbol for asset in assets]
            
            # Analyze all symbols concurrently
            signals = await self.analyzer.analyze_multiple_symbols(symbols)
            
            signals_generated = 0
            
            for signal in signals:
                if signal and signal.confidence_score >= 0.65:
                    # Save signal to database
                    signal_id = await self._save_modern_signal(db_session, signal)
                    
                    if signal_id:
                        signals_generated += 1
                        # Send alerts
                        await self._send_modern_alerts(signal, signal_id)
            
            logger.info(f"Modern market scan completed. Generated {signals_generated} signals")
            return {"status": "success", "signals_generated": signals_generated}
            
        except Exception as e:
            logger.error(f"Modern market scan failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _save_modern_signal(self, db_session, signal: ModernSignal) -> Optional[int]:
        """Save modern signal to database."""
        try:
            # Convert modern signal to database format
            signal_data = {
                'symbol': signal.symbol,
                'timeframe': signal.timeframe.upper(),
                'signal_type': SignalType.ENTRY,
                'direction': SignalDirection.LONG if signal.direction == 'LONG' else SignalDirection.SHORT,
                'score': signal.confidence_score,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit_1': signal.take_profit_1,
                'take_profit_2': signal.take_profit_2,
                'take_profit_3': signal.take_profit_3,
                'risk_reward_ratio': signal.risk_metrics.risk_reward_ratio,
                'confluences': {
                    'strength': signal.strength.value,
                    'market_condition': signal.market_condition.value,
                    'confluence_score': signal.confluence_analysis.confluence_score,
                    'technical_indicators': signal.technical_indicators.__dict__,
                    'smart_money_flow': signal.smart_money_flow.__dict__
                },
                'context': {
                    'market_data': signal.market_data.__dict__,
                    'risk_metrics': signal.risk_metrics.__dict__,
                    'support_resistance': signal.support_resistance_levels,
                    'fibonacci_levels': signal.fibonacci_levels,
                    'pivot_points': signal.pivot_points,
                    'volume_profile': signal.volume_profile,
                    'market_sentiment': signal.market_sentiment,
                    'data_sources': signal.data_sources,
                    'analysis_version': signal.analysis_version
                },
                'is_active': True,
                'created_at': signal.timestamp,
                'updated_at': signal.timestamp
            }
            
            # Insert signal
            result = db_session.execute(
                """
                INSERT INTO signals (symbol, timeframe, signal_type, direction, score, 
                                   entry_price, stop_loss, take_profit_1, take_profit_2, 
                                   take_profit_3, risk_reward_ratio, confluences, context, 
                                   is_active, created_at, updated_at)
                VALUES (:symbol, :timeframe, :signal_type, :direction, :score,
                        :entry_price, :stop_loss, :take_profit_1, :take_profit_2,
                        :take_profit_3, :risk_reward_ratio, :confluences, :context,
                        :is_active, :created_at, :updated_at)
                RETURNING id
                """,
                signal_data
            )
            
            signal_id = result.fetchone()[0]
            db_session.commit()
            
            logger.info(f"Saved modern signal {signal_id} for {signal.symbol}")
            return signal_id
            
        except Exception as e:
            logger.error(f"Error saving modern signal: {e}")
            db_session.rollback()
            return None
    
    async def _send_modern_alerts(self, signal: ModernSignal, signal_id: int):
        """Send modern alerts for the signal."""
        try:
            # Create enhanced alert message
            alert_message = self._create_modern_alert_message(signal)
            
            # Send Telegram alert
            telegram_sent = await self._send_telegram_modern_alert(signal, alert_message)
            
            # Send Discord alert
            discord_sent = await self._send_discord_modern_alert(signal, alert_message)
            
            logger.info(f"Modern alerts sent for signal {signal_id}: Telegram={telegram_sent}, Discord={discord_sent}")
            
        except Exception as e:
            logger.error(f"Error sending modern alerts: {e}")
    
    def _create_modern_alert_message(self, signal: ModernSignal) -> str:
        """Create enhanced alert message."""
        emoji = "🚀" if signal.direction == "LONG" else "📉"
        strength_emoji = {
            "weak": "⚡",
            "moderate": "🔥", 
            "strong": "💪",
            "very_strong": "🚀"
        }
        
        return f"""
{emoji} <b>{signal.symbol} {signal.direction} SIGNAL</b> {strength_emoji.get(signal.strength.value, "⚡")}

📊 <b>Analysis Summary:</b>
• Strength: {signal.strength.value.upper()}
• Confidence: {signal.confidence_score:.1%}
• Market: {signal.market_condition.value.replace('_', ' ').title()}
• Confluence: {signal.confluence_analysis.confluence_score:.1%}

💰 <b>Price Levels:</b>
• Entry: ${signal.entry_price:,.2f}
• Stop Loss: ${signal.stop_loss:,.2f}
• Take Profit 1: ${signal.take_profit_1:,.2f}
• Take Profit 2: ${signal.take_profit_2:,.2f}
• Take Profit 3: ${signal.take_profit_3:,.2f}

⚡ <b>Risk Metrics:</b>
• Risk/Reward: {signal.risk_metrics.risk_reward_ratio:.2f}
• Volatility 24h: {signal.risk_metrics.volatility_24h:.1%}
• Position Size: {signal.risk_metrics.position_size:.1%}

🔗 <b>Data Sources:</b> {', '.join(signal.data_sources)}
📈 <b>Sentiment:</b> {signal.market_sentiment.title()}

<i>Generated by Million Trader AI v{signal.analysis_version}</i>
        """.strip()
    
    async def _send_telegram_modern_alert(self, signal: ModernSignal, message: str) -> bool:
        """Send enhanced Telegram alert."""
        try:
            # Use the existing alert sender but with enhanced message
            return self.alert_sender.send_telegram_alert(signal)
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def _send_discord_modern_alert(self, signal: ModernSignal, message: str) -> bool:
        """Send enhanced Discord alert."""
        try:
            # Create rich Discord embed
            embed = {
                "title": f"🚨 {signal.symbol} {signal.direction} Signal",
                "description": message,
                "color": 0x00ff00 if signal.direction == "LONG" else 0xff0000,
                "timestamp": signal.timestamp.isoformat(),
                "fields": [
                    {
                        "name": "📊 Technical Analysis",
                        "value": f"RSI: {signal.technical_indicators.rsi_14:.1f}\nMACD: {signal.technical_indicators.macd:.4f}\nADX: {signal.technical_indicators.adx:.1f}",
                        "inline": True
                    },
                    {
                        "name": "💰 Price Action",
                        "value": f"Entry: ${signal.entry_price:,.2f}\nStop: ${signal.stop_loss:,.2f}\nTP1: ${signal.take_profit_1:,.2f}",
                        "inline": True
                    },
                    {
                        "name": "⚡ Risk Metrics",
                        "value": f"R/R: {signal.risk_metrics.risk_reward_ratio:.2f}\nVol: {signal.risk_metrics.volatility_24h:.1%}\nSize: {signal.risk_metrics.position_size:.1%}",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Million Trader AI v{signal.analysis_version} • {', '.join(signal.data_sources)}"
                }
            }
            
            return self.alert_sender.send_discord_alert(signal)
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False






