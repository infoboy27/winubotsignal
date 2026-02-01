"""
Gradual Scaling System for Production Deployment
"""

import sys
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class GradualScaler:
    """Gradually scale position sizes based on performance."""
    
    def __init__(self):
        self.base_position_size = 0.001  # Start with very small positions
        self.max_position_size = 0.01   # Maximum position size
        self.scaling_factor = 1.5       # Multiply by this factor on success
        self.reduction_factor = 0.7     # Multiply by this factor on failure
        
        self.performance_thresholds = {
            "excellent": {"win_rate": 60, "min_trades": 10},
            "good": {"win_rate": 50, "min_trades": 5},
            "poor": {"win_rate": 40, "min_trades": 3}
        }
        
        self.current_position_size = self.base_position_size
        self.scaling_history = []
        
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def get_recent_performance(self, days: int = 3) -> Dict:
        """Get recent performance for scaling decisions."""
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
                    SUM(realized_pnl) as total_pnl
                FROM signals 
                WHERE created_at >= $1 AND realized_pnl != 0
            """, since)
            
            if not metrics or metrics['total_trades'] < 3:
                return {"status": "insufficient_data", "trades": metrics['total_trades'] if metrics else 0}
            
            win_rate = (metrics['winning_trades'] / metrics['total_trades']) * 100
            total_pnl = float(metrics['total_pnl']) if metrics['total_pnl'] else 0
            
            return {
                "status": "success",
                "total_trades": metrics['total_trades'],
                "winning_trades": metrics['winning_trades'],
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_pnl": float(metrics['avg_pnl']) if metrics['avg_pnl'] else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting recent performance: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    def calculate_performance_grade(self, performance: Dict) -> str:
        """Calculate performance grade for scaling decisions."""
        if performance.get("status") != "success":
            return "insufficient_data"
        
        win_rate = performance.get("win_rate", 0)
        total_trades = performance.get("total_trades", 0)
        
        if total_trades >= self.performance_thresholds["excellent"]["min_trades"]:
            if win_rate >= self.performance_thresholds["excellent"]["win_rate"]:
                return "excellent"
        
        if total_trades >= self.performance_thresholds["good"]["min_trades"]:
            if win_rate >= self.performance_thresholds["good"]["win_rate"]:
                return "good"
        
        if total_trades >= self.performance_thresholds["poor"]["min_trades"]:
            if win_rate < self.performance_thresholds["poor"]["win_rate"]:
                return "poor"
        
        return "insufficient_data"
    
    def calculate_new_position_size(self, performance_grade: str, current_size: float) -> Dict:
        """Calculate new position size based on performance grade."""
        if performance_grade == "insufficient_data":
            return {
                "status": "no_change",
                "reason": "Insufficient data for scaling decision",
                "new_size": current_size
            }
        
        new_size = current_size
        
        if performance_grade == "excellent":
            # Scale up significantly
            new_size = min(self.max_position_size, current_size * (self.scaling_factor ** 1.5))
            action = "scale_up_aggressive"
            reason = "Excellent performance - aggressive scaling"
            
        elif performance_grade == "good":
            # Scale up moderately
            new_size = min(self.max_position_size, current_size * self.scaling_factor)
            action = "scale_up_moderate"
            reason = "Good performance - moderate scaling"
            
        elif performance_grade == "poor":
            # Scale down
            new_size = max(self.base_position_size, current_size * self.reduction_factor)
            action = "scale_down"
            reason = "Poor performance - scaling down"
            
        else:
            return {
                "status": "no_change",
                "reason": "Unknown performance grade",
                "new_size": current_size
            }
        
        # Ensure we don't go below base or above max
        new_size = max(self.base_position_size, min(self.max_position_size, new_size))
        
        return {
            "status": "change",
            "action": action,
            "reason": reason,
            "old_size": current_size,
            "new_size": new_size,
            "change_factor": new_size / current_size if current_size > 0 else 1.0
        }
    
    async def apply_position_scaling(self, scaling_decision: Dict) -> bool:
        """Apply position size scaling to the system."""
        if scaling_decision.get("status") != "change":
            logger.info(f"ℹ️ No position scaling needed: {scaling_decision.get('reason', '')}")
            return True
        
        try:
            # Update current position size
            old_size = self.current_position_size
            new_size = scaling_decision["new_size"]
            
            self.current_position_size = new_size
            
            # Record scaling action
            scaling_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": scaling_decision["action"],
                "reason": scaling_decision["reason"],
                "old_size": old_size,
                "new_size": new_size,
                "change_factor": scaling_decision["change_factor"]
            }
            
            self.scaling_history.append(scaling_record)
            
            # Save to database
            conn = await self.connect_db()
            await conn.execute("""
                INSERT INTO scaling_log (
                    timestamp, action, reason, old_size, new_size, change_factor
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, 
                datetime.utcnow(),
                scaling_decision["action"],
                scaling_decision["reason"],
                old_size,
                new_size,
                scaling_decision["change_factor"]
            )
            await conn.close()
            
            logger.info(f"📈 Position scaling applied:")
            logger.info(f"   Action: {scaling_decision['action']}")
            logger.info(f"   Reason: {scaling_decision['reason']}")
            logger.info(f"   Size: {old_size:.4f} → {new_size:.4f} ({scaling_decision['change_factor']:.2f}x)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error applying position scaling: {e}")
            return False
    
    async def get_scaling_recommendations(self) -> Dict:
        """Get current scaling recommendations."""
        try:
            # Get recent performance
            performance = await self.get_recent_performance()
            
            if performance.get("status") != "success":
                return {
                    "status": "insufficient_data",
                    "message": "Need more trading data for scaling recommendations",
                    "current_trades": performance.get("trades", 0)
                }
            
            # Calculate performance grade
            grade = self.calculate_performance_grade(performance)
            
            # Calculate scaling decision
            scaling_decision = self.calculate_new_position_size(grade, self.current_position_size)
            
            return {
                "status": "success",
                "current_position_size": self.current_position_size,
                "performance_grade": grade,
                "performance_metrics": performance,
                "scaling_decision": scaling_decision,
                "scaling_history": self.scaling_history[-5:]  # Last 5 scaling actions
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting scaling recommendations: {e}")
            return {"status": "error", "error": str(e)}
    
    async def run_scaling_cycle(self) -> Dict:
        """Run complete scaling cycle."""
        try:
            logger.info("📈 Starting gradual scaling cycle...")
            
            # Get scaling recommendations
            recommendations = await self.get_scaling_recommendations()
            
            if recommendations.get("status") != "success":
                return recommendations
            
            # Apply scaling if recommended
            scaling_decision = recommendations["scaling_decision"]
            success = await self.apply_position_scaling(scaling_decision)
            
            if success:
                return {
                    "status": "success",
                    "scaling_applied": scaling_decision.get("status") == "change",
                    "current_position_size": self.current_position_size,
                    "performance_grade": recommendations["performance_grade"],
                    "scaling_decision": scaling_decision
                }
            else:
                return {"status": "error", "message": "Failed to apply position scaling"}
            
        except Exception as e:
            logger.error(f"❌ Scaling cycle failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_scaling_status(self) -> Dict:
        """Get current scaling status and history."""
        return {
            "status": "success",
            "current_position_size": self.current_position_size,
            "base_position_size": self.base_position_size,
            "max_position_size": self.max_position_size,
            "scaling_factor": self.scaling_factor,
            "reduction_factor": self.reduction_factor,
            "scaling_history": self.scaling_history[-10:]  # Last 10 actions
        }


async def main():
    """Main function to run gradual scaling."""
    scaler = GradualScaler()
    
    # Show current status
    status = await scaler.get_scaling_status()
    print(f"\n📈 GRADUAL SCALING STATUS:")
    print(f"   Current Position Size: {status['current_position_size']:.4f}")
    print(f"   Base Position Size: {status['base_position_size']:.4f}")
    print(f"   Max Position Size: {status['max_position_size']:.4f}")
    print(f"   Scaling Factor: {status['scaling_factor']:.1f}x")
    print(f"   Reduction Factor: {status['reduction_factor']:.1f}x")
    
    # Run scaling cycle
    result = await scaler.run_scaling_cycle()
    
    if result["status"] == "success":
        print(f"\n✅ SCALING CYCLE COMPLETED")
        
        if result.get("scaling_applied"):
            decision = result["scaling_decision"]
            print(f"📈 Scaling Applied:")
            print(f"   Action: {decision['action']}")
            print(f"   Reason: {decision['reason']}")
            print(f"   Size: {decision['old_size']:.4f} → {decision['new_size']:.4f}")
            print(f"   Factor: {decision['change_factor']:.2f}x")
        else:
            print(f"ℹ️ No scaling changes needed")
        
        print(f"\n📊 Performance Grade: {result.get('performance_grade', 'unknown').upper()}")
        print(f"📈 Current Position Size: {result.get('current_position_size', 0):.4f}")
    
    elif result["status"] == "insufficient_data":
        print(f"\n⚠️ INSUFFICIENT DATA FOR SCALING")
        print(f"   {result.get('message', '')}")
        print(f"   Current trades: {result.get('current_trades', 0)}")
    
    else:
        print(f"\n❌ SCALING FAILED: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(main())
