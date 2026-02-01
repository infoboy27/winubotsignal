"""
Automatic Parameter Tuning System for Live Results
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


class ParameterTuner:
    """Automatically tune parameters based on live performance."""
    
    def __init__(self):
        self.current_params = {
            "min_score": 0.8,
            "risk_per_trade": 0.015,
            "take_profit": 0.015,
            "stop_loss": 0.015,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "momentum_threshold": 0.5
        }
        
        self.parameter_ranges = {
            "min_score": (0.7, 0.9),
            "risk_per_trade": (0.01, 0.02),
            "take_profit": (0.01, 0.02),
            "stop_loss": (0.01, 0.02),
            "rsi_oversold": (25, 35),
            "rsi_overbought": (65, 75),
            "momentum_threshold": (0.3, 0.7)
        }
        
        self.target_win_rate = 53.8
        self.min_trades_for_analysis = 10
        
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def get_recent_performance(self, days: int = 7) -> Dict:
        """Get recent performance data for parameter tuning."""
        conn = None
        try:
            conn = await self.connect_db()
            
            since = datetime.utcnow() - timedelta(days=days)
            
            # Get performance metrics
            metrics = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as winning_trades,
                    AVG(realized_pnl) as avg_pnl,
                    AVG(score) as avg_score,
                    MIN(score) as min_score,
                    MAX(score) as max_score,
                    STDDEV(score) as score_stddev
                FROM signals 
                WHERE created_at >= $1 AND realized_pnl != 0
            """, since)
            
            if not metrics or metrics['total_trades'] < self.min_trades_for_analysis:
                return {"status": "insufficient_data", "trades": metrics['total_trades'] if metrics else 0}
            
            win_rate = (metrics['winning_trades'] / metrics['total_trades']) * 100
            
            return {
                "status": "success",
                "total_trades": metrics['total_trades'],
                "winning_trades": metrics['winning_trades'],
                "win_rate": win_rate,
                "avg_pnl": float(metrics['avg_pnl']) if metrics['avg_pnl'] else 0,
                "avg_score": float(metrics['avg_score']) if metrics['avg_score'] else 0,
                "score_range": {
                    "min": float(metrics['min_score']) if metrics['min_score'] else 0,
                    "max": float(metrics['max_score']) if metrics['max_score'] else 0,
                    "stddev": float(metrics['score_stddev']) if metrics['score_stddev'] else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting recent performance: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    def calculate_parameter_adjustments(self, performance: Dict) -> Dict:
        """Calculate parameter adjustments based on performance."""
        if performance.get("status") != "success":
            return {"status": "insufficient_data"}
        
        win_rate = performance.get("win_rate", 0)
        avg_score = performance.get("avg_score", 0)
        score_stddev = performance.get("score_range", {}).get("stddev", 0)
        
        adjustments = {}
        
        # Adjust minimum score based on win rate
        if win_rate < self.target_win_rate - 5:  # Win rate too low
            if avg_score > 0.85:  # High scores but low win rate
                adjustments["min_score"] = min(0.9, self.current_params["min_score"] + 0.05)
                logger.info("📈 Increasing min_score due to low win rate with high scores")
            else:  # Low scores and low win rate
                adjustments["min_score"] = max(0.7, self.current_params["min_score"] - 0.05)
                logger.info("📉 Decreasing min_score due to low win rate with low scores")
        
        elif win_rate > self.target_win_rate + 10:  # Win rate too high
            adjustments["min_score"] = max(0.7, self.current_params["min_score"] - 0.02)
            logger.info("📉 Decreasing min_score due to very high win rate")
        
        # Adjust risk parameters based on performance
        if win_rate > self.target_win_rate + 5:  # Good performance
            # Increase position size slightly
            adjustments["risk_per_trade"] = min(0.02, self.current_params["risk_per_trade"] + 0.002)
            logger.info("📈 Increasing risk_per_trade due to good performance")
        
        elif win_rate < self.target_win_rate - 10:  # Poor performance
            # Decrease position size
            adjustments["risk_per_trade"] = max(0.01, self.current_params["risk_per_trade"] - 0.003)
            logger.info("📉 Decreasing risk_per_trade due to poor performance")
        
        # Adjust TP/SL based on score consistency
        if score_stddev < 0.05:  # Very consistent scores
            # Tighten TP/SL
            adjustments["take_profit"] = max(0.01, self.current_params["take_profit"] - 0.002)
            adjustments["stop_loss"] = max(0.01, self.current_params["stop_loss"] - 0.002)
            logger.info("🎯 Tightening TP/SL due to consistent high scores")
        
        elif score_stddev > 0.15:  # Inconsistent scores
            # Widen TP/SL
            adjustments["take_profit"] = min(0.02, self.current_params["take_profit"] + 0.003)
            adjustments["stop_loss"] = min(0.02, self.current_params["stop_loss"] + 0.003)
            logger.info("📊 Widening TP/SL due to inconsistent scores")
        
        # Adjust RSI thresholds based on performance
        if win_rate < self.target_win_rate - 5:
            # Widen RSI range to get more signals
            adjustments["rsi_oversold"] = max(25, self.current_params["rsi_oversold"] - 2)
            adjustments["rsi_overbought"] = min(75, self.current_params["rsi_overbought"] + 2)
            logger.info("📊 Widening RSI range due to low win rate")
        
        return {
            "status": "success",
            "adjustments": adjustments,
            "reasoning": {
                "win_rate": win_rate,
                "target_win_rate": self.target_win_rate,
                "score_consistency": score_stddev,
                "total_trades": performance.get("total_trades", 0)
            }
        }
    
    def apply_parameter_adjustments(self, adjustments: Dict) -> Dict:
        """Apply parameter adjustments with safety checks."""
        if adjustments.get("status") != "success":
            return adjustments
        
        new_params = self.current_params.copy()
        applied_changes = {}
        
        for param, new_value in adjustments["adjustments"].items():
            if param in self.parameter_ranges:
                min_val, max_val = self.parameter_ranges[param]
                
                # Ensure value is within acceptable range
                safe_value = max(min_val, min(max_val, new_value))
                
                if abs(safe_value - self.current_params[param]) > 0.001:  # Only apply if significant change
                    new_params[param] = safe_value
                    applied_changes[param] = {
                        "old": self.current_params[param],
                        "new": safe_value,
                        "change": safe_value - self.current_params[param]
                    }
        
        if applied_changes:
            self.current_params = new_params
            logger.info(f"🔧 Applied {len(applied_changes)} parameter adjustments:")
            for param, change in applied_changes.items():
                logger.info(f"   {param}: {change['old']:.3f} → {change['new']:.3f} ({change['change']:+.3f})")
        
        return {
            "status": "success",
            "applied_changes": applied_changes,
            "new_parameters": new_params
        }
    
    async def save_parameters(self, parameters: Dict) -> bool:
        """Save tuned parameters to database."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Save parameters as JSON
            await conn.execute("""
                INSERT INTO parameter_tuning_log (
                    timestamp, parameters, tuning_reason, applied
                ) VALUES ($1, $2, $3, $4)
            """, 
                datetime.utcnow(),
                json.dumps(parameters),
                "Automatic tuning based on live performance",
                True
            )
            
            logger.info("💾 Saved tuned parameters to database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving parameters: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    async def run_parameter_tuning(self) -> Dict:
        """Run complete parameter tuning cycle."""
        try:
            logger.info("🔧 Starting parameter tuning cycle...")
            
            # Get recent performance
            performance = await self.get_recent_performance()
            
            if performance.get("status") == "insufficient_data":
                return {
                    "status": "insufficient_data",
                    "message": f"Need at least {self.min_trades_for_analysis} trades for analysis",
                    "current_trades": performance.get("trades", 0)
                }
            
            if performance.get("status") != "success":
                return performance
            
            # Calculate adjustments
            adjustments = self.calculate_parameter_adjustments(performance)
            
            if adjustments.get("status") != "success":
                return adjustments
            
            # Apply adjustments
            result = self.apply_parameter_adjustments(adjustments)
            
            if result.get("status") == "success" and result.get("applied_changes"):
                # Save parameters
                await self.save_parameters(result["new_parameters"])
                
                logger.info("✅ Parameter tuning completed successfully")
                return {
                    "status": "success",
                    "applied_changes": result["applied_changes"],
                    "performance_analysis": adjustments["reasoning"]
                }
            else:
                logger.info("ℹ️ No parameter adjustments needed")
                return {
                    "status": "no_changes_needed",
                    "message": "Current parameters are performing well",
                    "performance_analysis": adjustments["reasoning"]
                }
            
        except Exception as e:
            logger.error(f"❌ Parameter tuning failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_current_parameters(self) -> Dict:
        """Get current parameter values."""
        return {
            "status": "success",
            "parameters": self.current_params,
            "ranges": self.parameter_ranges
        }


async def main():
    """Main function to run parameter tuning."""
    tuner = ParameterTuner()
    
    # Show current parameters
    current = await tuner.get_current_parameters()
    print(f"\n🔧 CURRENT PARAMETERS:")
    for param, value in current["parameters"].items():
        print(f"   {param}: {value}")
    
    # Run tuning
    result = await tuner.run_parameter_tuning()
    
    if result["status"] == "success":
        print(f"\n✅ PARAMETER TUNING COMPLETED")
        print(f"📊 Applied changes: {len(result.get('applied_changes', {}))}")
        
        if result.get("applied_changes"):
            for param, change in result["applied_changes"].items():
                print(f"   {param}: {change['old']:.3f} → {change['new']:.3f}")
        
        print(f"\n📈 Performance Analysis:")
        analysis = result.get("performance_analysis", {})
        print(f"   Win Rate: {analysis.get('win_rate', 0):.1f}% (Target: {analysis.get('target_win_rate', 0):.1f}%)")
        print(f"   Total Trades: {analysis.get('total_trades', 0)}")
        print(f"   Score Consistency: {analysis.get('score_consistency', 0):.3f}")
    
    elif result["status"] == "insufficient_data":
        print(f"\n⚠️ INSUFFICIENT DATA FOR TUNING")
        print(f"   Current trades: {result.get('current_trades', 0)}")
        print(f"   Required: {tuner.min_trades_for_analysis}")
    
    elif result["status"] == "no_changes_needed":
        print(f"\n✅ NO CHANGES NEEDED")
        print(f"   {result.get('message', '')}")
    
    else:
        print(f"\n❌ TUNING FAILED: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(main())
