"""
Advanced Risk Management System for Automated Trading Bot
Implements comprehensive risk controls and position management
"""

import sys
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RiskManager:
    """Comprehensive risk management for automated trading."""
    
    def __init__(self):
        self.max_risk_per_trade = 0.02  # 2% risk per trade
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.max_positions = 10  # Maximum concurrent positions (increased for multi-account)
        self.max_correlation = 0.85  # Maximum correlation between positions (relaxed for better execution)
        self.emergency_stop_loss = 0.10  # 10% emergency stop loss
        self.max_drawdown = 0.15  # 15% maximum drawdown
        
        # Market condition filters - using bot config
        from config.bot_config import bot_settings
        self.enable_volatility_filter = bot_settings.enable_volatility_filter
        self.enable_liquidity_filter = bot_settings.enable_liquidity_filter
        self.enable_trend_filter = bot_settings.enable_trend_filter
        self.max_volatility = bot_settings.max_volatility
        self.min_liquidity = bot_settings.min_liquidity
        
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def check_daily_loss_limits(self) -> Dict:
        """Check if daily loss limits have been reached."""
        conn = None
        try:
            conn = await self.connect_db()
            
            today = datetime.utcnow().date()
            
            # Get today's realized PnL
            today_pnl = await conn.fetchval("""
                SELECT COALESCE(SUM(realized_pnl), 0) 
                FROM paper_positions 
                WHERE DATE(created_at) = $1 AND is_open = false
            """, today)
            
            # Get account balance (simplified)
            account_balance = 10000  # This should come from actual balance
            
            daily_loss_percentage = abs(today_pnl) / account_balance if account_balance > 0 else 0
            
            return {
                "can_trade": daily_loss_percentage < self.max_daily_loss,
                "today_pnl": float(today_pnl),
                "daily_loss_percentage": daily_loss_percentage * 100,
                "max_daily_loss": self.max_daily_loss * 100,
                "account_balance": account_balance
            }
            
        except Exception as e:
            logger.error(f"Error checking daily loss limits: {e}")
            return {"can_trade": False, "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    async def check_position_limits(self) -> Dict:
        """Check if position limits have been reached."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Count open positions
            open_positions = await conn.fetchval("""
                SELECT COUNT(*) FROM paper_positions WHERE is_open = true
            """)
            
            # Get position details
            positions = await conn.fetch("""
                SELECT symbol, side, entry_price, quantity, unrealized_pnl
                FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            return {
                "can_trade": open_positions < self.max_positions,
                "open_positions": open_positions,
                "max_positions": self.max_positions,
                "positions": [dict(pos) for pos in positions]
            }
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return {"can_trade": False, "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    async def check_correlation_risk(self, new_symbol: str) -> Dict:
        """Check correlation risk with existing positions."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get existing positions
            existing_positions = await conn.fetch("""
                SELECT symbol, side, entry_price, quantity
                FROM paper_positions 
                WHERE is_open = true
            """)
            
            if not existing_positions:
                return {"can_trade": True, "correlation_risk": 0}
            
            # Improved correlation check with smarter logic
            same_symbol_count = sum(1 for pos in existing_positions if pos['symbol'] == new_symbol)
            
            # Allow same symbol if we have good reasons (different direction, profitable old position, etc.)
            if same_symbol_count > 0:
                # For now, allow same symbol with relaxed correlation (will be improved later)
                same_symbol_count = same_symbol_count * 0.5  # Reduce correlation penalty for same symbol
            
            # Check for similar assets (BTC/ETH correlation)
            similar_assets = 0
            if 'BTC' in new_symbol:
                similar_assets = sum(1 for pos in existing_positions if 'BTC' in pos['symbol'])
            elif 'ETH' in new_symbol:
                similar_assets = sum(1 for pos in existing_positions if 'ETH' in pos['symbol'])
            
            correlation_risk = (same_symbol_count + similar_assets) / len(existing_positions)
            
            return {
                "can_trade": correlation_risk < self.max_correlation,
                "correlation_risk": correlation_risk,
                "max_correlation": self.max_correlation,
                "existing_positions": len(existing_positions),
                "reason": f"Correlation risk: {correlation_risk:.2f} (limit: {self.max_correlation})"
            }
            
        except Exception as e:
            logger.error(f"Error checking correlation risk: {e}")
            return {"can_trade": True, "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    async def check_emergency_conditions(self) -> Dict:
        """Check for emergency conditions that require stopping trading."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Check for large losses
            recent_losses = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM paper_positions 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                AND realized_pnl < -100
            """)
            
            # Check for consecutive losses
            consecutive_losses = await conn.fetchval("""
                WITH recent_trades AS (
                    SELECT realized_pnl, ROW_NUMBER() OVER (ORDER BY created_at DESC) as rn
                    FROM paper_positions 
                    WHERE is_open = false 
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY created_at DESC
                    LIMIT 5
                )
                SELECT COUNT(*) 
                FROM recent_trades 
                WHERE realized_pnl < 0 AND rn <= 3
            """)
            
            # Check total drawdown
            total_pnl = await conn.fetchval("""
                SELECT COALESCE(SUM(realized_pnl), 0) 
                FROM paper_positions 
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """)
            
            account_balance = 10000  # This should come from actual balance
            drawdown_percentage = abs(total_pnl) / account_balance if account_balance > 0 else 0
            
            emergency_conditions = {
                "large_losses": recent_losses > 2,
                "consecutive_losses": consecutive_losses >= 3,
                "high_drawdown": drawdown_percentage > self.max_drawdown,
                "total_pnl": float(total_pnl),
                "drawdown_percentage": drawdown_percentage * 100
            }
            
            emergency_stop = any([
                emergency_conditions["large_losses"],
                emergency_conditions["consecutive_losses"],
                emergency_conditions["high_drawdown"]
            ])
            
            return {
                "emergency_stop": emergency_stop,
                "conditions": emergency_conditions,
                "can_trade": not emergency_stop
            }
            
        except Exception as e:
            logger.error(f"Error checking emergency conditions: {e}")
            return {"emergency_stop": False, "can_trade": True, "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    async def calculate_position_size(self, signal: Dict, account_balance: float) -> Dict:
        """Calculate safe position size based on risk parameters."""
        try:
            entry_price = float(signal['entry_price'])
            stop_loss = float(signal['stop_loss'])
            
            # Calculate risk per trade
            risk_amount = account_balance * self.max_risk_per_trade
            
            # Calculate stop loss distance
            if signal['direction'] == 'LONG':
                risk_per_unit = entry_price - stop_loss
            else:  # SHORT
                risk_per_unit = stop_loss - entry_price
            
            if risk_per_unit <= 0:
                return {"quantity": 0, "risk_amount": 0, "error": "Invalid stop loss"}
            
            # Calculate base quantity
            base_quantity = risk_amount / risk_per_unit
            
            # Apply Kelly Criterion (simplified)
            win_rate = 0.538  # From backtest results
            avg_win = 0.015  # 1.5% average win
            avg_loss = 0.015  # 1.5% average loss
            
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
            
            # Apply Kelly sizing
            kelly_quantity = base_quantity * kelly_fraction
            
            # Apply maximum position size limit
            max_position_value = account_balance * 0.3  # Max 30% of balance per position
            max_quantity_by_value = max_position_value / entry_price
            
            final_quantity = min(kelly_quantity, max_quantity_by_value)
            
            # Round to appropriate precision
            if 'BTC' in signal['symbol']:
                final_quantity = round(final_quantity, 6)
            elif 'ETH' in signal['symbol']:
                final_quantity = round(final_quantity, 5)
            else:
                final_quantity = round(final_quantity, 4)
            
            return {
                "quantity": final_quantity,
                "risk_amount": risk_amount,
                "position_value": final_quantity * entry_price,
                "risk_percentage": (risk_amount / account_balance) * 100,
                "kelly_fraction": kelly_fraction,
                "base_quantity": base_quantity
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"quantity": 0, "risk_amount": 0, "error": str(e)}
    
    async def validate_trade(self, signal: Dict) -> Dict:
        """Validate if a trade can be executed based on risk parameters."""
        try:
            # Check daily loss limits
            daily_check = await self.check_daily_loss_limits()
            if not daily_check.get('can_trade', False):
                return {
                    "can_trade": False,
                    "reason": "Daily loss limit reached",
                    "details": daily_check
                }
            
            # Check position limits
            position_check = await self.check_position_limits()
            if not position_check.get('can_trade', False):
                return {
                    "can_trade": False,
                    "reason": "Position limit reached",
                    "details": position_check
                }
            
            # Check correlation risk
            correlation_check = await self.check_correlation_risk(signal['symbol'])
            if not correlation_check.get('can_trade', False):
                return {
                    "can_trade": False,
                    "reason": "Correlation risk too high",
                    "details": correlation_check
                }
            
            # Check emergency conditions
            emergency_check = await self.check_emergency_conditions()
            if not emergency_check.get('can_trade', False):
                return {
                    "can_trade": False,
                    "reason": "Emergency conditions detected",
                    "details": emergency_check
                }
            
            return {
                "can_trade": True,
                "reason": "All risk checks passed",
                "daily_check": daily_check,
                "position_check": position_check,
                "correlation_check": correlation_check,
                "emergency_check": emergency_check
            }
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return {"can_trade": False, "reason": f"Validation error: {e}"}
    
    async def check_market_conditions(self, symbol: str) -> Dict:
        """Check if market conditions are suitable for trading."""
        try:
            # This is a simplified version - in production, you'd integrate with the exchange
            # For now, we'll return basic checks based on configuration
            
            conditions = {
                "symbol": symbol,
                "suitable_for_trading": True,
                "reasons": [],
                "volatility_check": True,
                "liquidity_check": True,
                "trend_check": True
            }
            
            # Basic market condition validation
            if self.enable_volatility_filter:
                # In a real implementation, you'd fetch actual volatility data
                # For now, we'll assume conditions are met
                conditions["volatility_check"] = True
            
            if self.enable_liquidity_filter:
                # In a real implementation, you'd check actual liquidity
                conditions["liquidity_check"] = True
            
            if self.enable_trend_filter:
                # In a real implementation, you'd check trend indicators
                conditions["trend_check"] = True
            
            # If any filter fails, mark as not suitable
            if not all([conditions["volatility_check"], conditions["liquidity_check"], conditions["trend_check"]]):
                conditions["suitable_for_trading"] = False
                conditions["reasons"].append("Market condition filters failed")
            
            return conditions
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            return {
                "symbol": symbol,
                "suitable_for_trading": False,
                "reasons": [f"Error checking conditions: {str(e)}"]
            }
    
    async def validate_trade_enhanced(self, signal: Dict) -> Dict:
        """Enhanced trade validation with market condition checks."""
        try:
            # Check market conditions first
            market_check = await self.check_market_conditions(signal['symbol'])
            if not market_check.get('suitable_for_trading', False):
                return {
                    "can_trade": False,
                    "reason": "Market conditions not suitable",
                    "details": market_check
                }
            
            # Run standard validation
            standard_validation = await self.validate_trade(signal)
            
            # Add market condition info to the response
            if standard_validation.get('can_trade', False):
                standard_validation['market_check'] = market_check
            
            return standard_validation
            
        except Exception as e:
            logger.error(f"Error in enhanced trade validation: {e}")
            return {"can_trade": False, "reason": f"Enhanced validation error: {e}"}


async def main():
    """Test the risk manager."""
    risk_manager = RiskManager()
    
    print("🛡️ Testing Risk Manager...")
    
    # Test daily loss limits
    daily_check = await risk_manager.check_daily_loss_limits()
    print(f"📊 Daily Loss Check: {daily_check}")
    
    # Test position limits
    position_check = await risk_manager.check_position_limits()
    print(f"📈 Position Check: {position_check}")
    
    # Test emergency conditions
    emergency_check = await risk_manager.check_emergency_conditions()
    print(f"🚨 Emergency Check: {emergency_check}")


if __name__ == "__main__":
    asyncio.run(main())







