"""Trending coins data fetcher and analyzer."""

import asyncio
import aiohttp
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger

sys.path.append('/packages')

from common.config import get_settings
from common.database import Asset
from packages.signals.multi_source_analyzer import MultiSourceAnalyzer


class TrendingCoinsAnalyzer:
    """Analyzer for trending coins with real-time data."""
    
    def __init__(self):
        self.settings = get_settings()
        self.analyzer = MultiSourceAnalyzer(
            binance_api_key=self.settings.exchange.binance_api_key,
            binance_secret=self.settings.exchange.binance_api_secret,
            gate_api_key=self.settings.exchange.gate_api_key,
            gate_secret=self.settings.exchange.gate_api_secret,
            cmc_api_key=self.settings.market_data.cmc_api_key
        )
    
    async def get_trending_coins(self, count: int = 10) -> List[Dict]:
        """Get trending coins from CoinMarketCap."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'X-CMC_PRO_API_KEY': self.settings.market_data.cmc_api_key,
                    'Accept': 'application/json'
                }
                
                # Get trending coins
                url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/trending/most-visited"
                params = {'limit': count}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        trending_coins = []
                        
                        for coin in data.get('data', []):
                            symbol = coin['symbol']
                            name = coin['name']
                            
                            # Create trading pair symbol
                            trading_symbol = f"{symbol}/USDT"
                            
                            trending_coins.append({
                                'symbol': trading_symbol,
                                'name': name,
                                'cmc_rank': coin.get('cmc_rank', 0),
                                'market_cap': coin.get('quote', {}).get('USD', {}).get('market_cap', 0),
                                'price': coin.get('quote', {}).get('USD', {}).get('price', 0),
                                'change_24h': coin.get('quote', {}).get('USD', {}).get('percent_change_24h', 0),
                                'volume_24h': coin.get('quote', {}).get('USD', {}).get('volume_24h', 0)
                            })
                        
                        # Add SYRUP/USDT if requested
                        if self.settings.trading.include_syrup_usdt:
                            syrup_data = await self._get_syrup_data()
                            if syrup_data:
                                trending_coins.append(syrup_data)
                        
                        logger.info(f"Found {len(trending_coins)} trending coins")
                        return trending_coins
                        
        except Exception as e:
            logger.error(f"Error fetching trending coins: {e}")
            return []
    
    async def _get_syrup_data(self) -> Optional[Dict]:
        """Get SYRUP/USDT data specifically."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'X-CMC_PRO_API_KEY': self.settings.market_data.cmc_api_key,
                    'Accept': 'application/json'
                }
                
                # Get SYRUP data
                url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
                params = {'symbol': 'SYRUP'}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'data' in data and 'SYRUP' in data['data']:
                            coin = data['data']['SYRUP']
                            quote = coin['quote']['USD']
                            
                            return {
                                'symbol': 'SYRUP/USDT',
                                'name': 'Syrup',
                                'cmc_rank': coin.get('cmc_rank', 0),
                                'market_cap': quote.get('market_cap', 0),
                                'price': quote.get('price', 0),
                                'change_24h': quote.get('percent_change_24h', 0),
                                'volume_24h': quote.get('volume_24h', 0)
                            }
        except Exception as e:
            logger.error(f"Error fetching SYRUP data: {e}")
            return None
    
    def analyze_trending_coins(self, db_session) -> Dict:
        """Analyze all trending coins for signals."""
        logger.info("Starting trending coins analysis...")
        
        try:
            # Get trending coins
            trending_coins = asyncio.run(self.get_trending_coins(
                count=self.settings.trading.trending_coins_count
            ))
            
            if not trending_coins:
                logger.warning("No trending coins found")
                return {"status": "no_coins", "signals_generated": 0}
            
            # Update database with trending coins
            self._update_trending_assets(db_session, trending_coins)
            
            # Analyze each coin for signals
            signals_generated = 0
            analysis_results = []
            
            for coin in trending_coins:
                try:
                    symbol = coin['symbol']
                    logger.info(f"Analyzing {symbol}...")
                    
                    # Generate signal using multi-source analyzer
                    signal = asyncio.run(self.analyzer.analyze_symbol(symbol))
                    
                    if signal and signal.confidence_score >= 0.65:
                        # Save signal to database
                        signal_id = self._save_trending_signal(db_session, signal, coin)
                        
                        if signal_id:
                            signals_generated += 1
                            analysis_results.append({
                                'symbol': symbol,
                                'signal_id': signal_id,
                                'confidence': signal.confidence_score,
                                'direction': signal.direction,
                                'strength': signal.strength.value
                            })
                            
                            # Send alerts
                            self._send_trending_alerts(signal, signal_id)
                    
                except Exception as e:
                    logger.error(f"Error analyzing {coin['symbol']}: {e}")
                    continue
            
            logger.info(f"Trending coins analysis completed. Generated {signals_generated} signals")
            return {
                "status": "success",
                "signals_generated": signals_generated,
                "coins_analyzed": len(trending_coins),
                "results": analysis_results
            }
            
        except Exception as e:
            logger.error(f"Trending coins analysis failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _update_trending_assets(self, db_session, trending_coins: List[Dict]):
        """Update database with trending coins."""
        try:
            for coin in trending_coins:
                # Check if asset exists
                existing_asset = db_session.execute(
                    "SELECT * FROM assets WHERE symbol = :symbol",
                    {"symbol": coin['symbol']}
                ).fetchone()
                
                if existing_asset:
                    # Update existing asset
                    db_session.execute(
                        """
                        UPDATE assets 
                        SET name = :name, active = true, updated_at = :updated_at
                        WHERE symbol = :symbol
                        """,
                        {
                            "name": coin['name'],
                            "symbol": coin['symbol'],
                            "updated_at": datetime.now()
                        }
                    )
                else:
                    # Create new asset
                    db_session.execute(
                        """
                        INSERT INTO assets (symbol, name, base, quote, exchange, active, created_at, updated_at)
                        VALUES (:symbol, :name, :base, :quote, :exchange, :active, :created_at, :updated_at)
                        """,
                        {
                            "symbol": coin['symbol'],
                            "name": coin['name'],
                            "base": coin['symbol'].split('/')[0],
                            "quote": coin['symbol'].split('/')[1],
                            "exchange": "binance",
                            "active": True,
                            "created_at": datetime.now(),
                            "updated_at": datetime.now()
                        }
                    )
            
            db_session.commit()
            logger.info(f"Updated {len(trending_coins)} trending assets in database")
            
        except Exception as e:
            logger.error(f"Error updating trending assets: {e}")
            db_session.rollback()
    
    def _save_trending_signal(self, db_session, signal, coin_data: Dict) -> Optional[int]:
        """Save trending coin signal to database."""
        try:
            signal_data = {
                'symbol': signal.symbol,
                'timeframe': signal.timeframe.upper(),
                'signal_type': 'ENTRY',
                'direction': 'LONG' if signal.direction == 'LONG' else 'SHORT',
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
                    'trending_data': coin_data
                },
                'context': {
                    'market_data': signal.market_data.__dict__,
                    'risk_metrics': signal.risk_metrics.__dict__,
                    'trending_analysis': True,
                    'data_sources': signal.data_sources,
                    'analysis_version': signal.analysis_version
                },
                'is_active': True,
                'created_at': signal.timestamp,
                'updated_at': signal.timestamp
            }
            
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
            
            logger.info(f"Saved trending signal {signal_id} for {signal.symbol}")
            return signal_id
            
        except Exception as e:
            logger.error(f"Error saving trending signal: {e}")
            db_session.rollback()
            return None
    
    def _send_trending_alerts(self, signal, signal_id: int):
        """Send alerts for trending coin signals."""
        try:
            from tasks.alert_sender import AlertSenderTask
            alert_sender = AlertSenderTask()
            
            # Create enhanced alert message for trending coins
            alert_message = self._create_trending_alert_message(signal)
            
            # Send alerts
            telegram_sent = alert_sender.send_telegram_alert(signal)
            discord_sent = alert_sender.send_discord_alert(signal)
            
            logger.info(f"Trending alerts sent for signal {signal_id}: Telegram={telegram_sent}, Discord={discord_sent}")
            
        except Exception as e:
            logger.error(f"Error sending trending alerts: {e}")
    
    def _create_trending_alert_message(self, signal) -> str:
        """Create enhanced alert message for trending coins."""
        emoji = "🚀" if signal.direction == "LONG" else "📉"
        strength_emoji = {
            "weak": "⚡",
            "moderate": "🔥", 
            "strong": "💪",
            "very_strong": "🚀"
        }
        
        return f"""
{emoji} <b>TRENDING COIN ALERT</b> {strength_emoji.get(signal.strength.value, "⚡")}

🔥 <b>{signal.symbol} - TRENDING SIGNAL</b>

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
🔥 <b>Status:</b> TRENDING COIN

<i>Generated by Million Trader AI v{signal.analysis_version}</i>
        """.strip()
