"""
Real-time Performance Monitor for Production Strategy
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


class PerformanceMonitor:
    """Monitor real-time performance vs backtest results."""
    
    def __init__(self):
        self.backtest_win_rate = 53.8
        self.backtest_return = 1.76
        self.target_win_rate_min = 45.0  # Minimum acceptable win rate
        self.target_win_rate_max = 65.0  # Maximum expected win rate
        
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def get_live_performance_metrics(self) -> Dict:
        """Get current live performance metrics."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get signals from last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            
            # Count total signals
            total_signals = await conn.fetchval("""
                SELECT COUNT(*) FROM signals 
                WHERE created_at >= $1
            """, since)
            
            # Count completed signals (with realized PnL)
            completed_signals = await conn.fetchval("""
                SELECT COUNT(*) FROM signals 
                WHERE created_at >= $1 AND realized_pnl != 0
            """, since)
            
            # Calculate win rate
            winning_trades = await conn.fetchval("""
                SELECT COUNT(*) FROM signals 
                WHERE created_at >= $1 AND realized_pnl > 0
            """, since)
            
            # Calculate total PnL
            total_pnl = await conn.fetchval("""
                SELECT COALESCE(SUM(realized_pnl), 0) FROM signals 
                WHERE created_at >= $1
            """, since)
            
            # Calculate average score
            avg_score = await conn.fetchval("""
                SELECT COALESCE(AVG(score), 0) FROM signals 
                WHERE created_at >= $1
            """, since)
            
            # Get recent signals for analysis
            recent_signals = await conn.fetch("""
                SELECT symbol, direction, score, realized_pnl, created_at
                FROM signals 
                WHERE created_at >= $1
                ORDER BY created_at DESC
                LIMIT 10
            """, since)
            
            # Calculate win rate
            win_rate = (winning_trades / completed_signals * 100) if completed_signals > 0 else 0
            
            return {
                "period_hours": 24,
                "total_signals": total_signals,
                "completed_signals": completed_signals,
                "winning_trades": winning_trades,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_score": avg_score,
                "recent_signals": [dict(signal) for signal in recent_signals]
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting performance metrics: {e}")
            return {}
        finally:
            if conn:
                await conn.close()
    
    async def analyze_performance_vs_backtest(self, live_metrics: Dict) -> Dict:
        """Analyze live performance vs backtest expectations."""
        if not live_metrics:
            return {"status": "error", "message": "No live metrics available"}
        
        analysis = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "live_metrics": live_metrics,
            "comparison": {},
            "alerts": [],
            "recommendations": []
        }
        
        # Compare win rate
        live_win_rate = live_metrics.get("win_rate", 0)
        win_rate_diff = live_win_rate - self.backtest_win_rate
        
        analysis["comparison"]["win_rate"] = {
            "live": live_win_rate,
            "backtest": self.backtest_win_rate,
            "difference": win_rate_diff,
            "status": "good" if abs(win_rate_diff) < 10 else "warning"
        }
        
        # Check if win rate is within acceptable range
        if live_win_rate < self.target_win_rate_min:
            analysis["alerts"].append({
                "type": "warning",
                "message": f"Win rate {live_win_rate:.1f}% below minimum target {self.target_win_rate_min}%"
            })
            analysis["recommendations"].append("Consider tightening signal filters")
        
        elif live_win_rate > self.target_win_rate_max:
            analysis["alerts"].append({
                "type": "info",
                "message": f"Win rate {live_win_rate:.1f}% above maximum expected {self.target_win_rate_max}%"
            })
            analysis["recommendations"].append("Consider increasing position sizes")
        
        # Analyze signal quality
        avg_score = live_metrics.get("avg_score", 0)
        if avg_score < 0.8:
            analysis["alerts"].append({
                "type": "warning",
                "message": f"Average signal score {avg_score:.2f} below target 0.8"
            })
            analysis["recommendations"].append("Review signal generation parameters")
        
        # Check signal frequency
        total_signals = live_metrics.get("total_signals", 0)
        if total_signals == 0:
            analysis["alerts"].append({
                "type": "error",
                "message": "No signals generated in the last 24 hours"
            })
            analysis["recommendations"].append("Check signal generation system")
        
        elif total_signals < 5:
            analysis["alerts"].append({
                "type": "warning",
                "message": f"Low signal frequency: {total_signals} signals in 24h"
            })
            analysis["recommendations"].append("Consider relaxing filters slightly")
        
        # Overall performance assessment
        if len(analysis["alerts"]) == 0:
            analysis["overall_status"] = "excellent"
            analysis["summary"] = "Performance is meeting or exceeding backtest expectations"
        elif any(alert["type"] == "error" for alert in analysis["alerts"]):
            analysis["overall_status"] = "critical"
            analysis["summary"] = "Critical issues detected - immediate attention required"
        else:
            analysis["overall_status"] = "good"
            analysis["summary"] = "Performance is good with minor optimizations needed"
        
        return analysis
    
    async def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        try:
            logger.info("📊 Generating performance report...")
            
            # Get live metrics
            live_metrics = await self.get_live_performance_metrics()
            
            if not live_metrics:
                return {"status": "error", "message": "Unable to retrieve live metrics"}
            
            # Analyze performance
            analysis = await self.analyze_performance_vs_backtest(live_metrics)
            
            # Log results
            logger.info(f"📈 Live Performance Report:")
            logger.info(f"   Win Rate: {live_metrics.get('win_rate', 0):.1f}% (Target: {self.backtest_win_rate}%)")
            logger.info(f"   Total Signals: {live_metrics.get('total_signals', 0)}")
            logger.info(f"   Total PnL: ${live_metrics.get('total_pnl', 0):.2f}")
            logger.info(f"   Avg Score: {live_metrics.get('avg_score', 0):.2f}")
            
            if analysis.get("alerts"):
                logger.warning(f"⚠️ Alerts: {len(analysis['alerts'])}")
                for alert in analysis["alerts"]:
                    logger.warning(f"   {alert['type'].upper()}: {alert['message']}")
            
            if analysis.get("recommendations"):
                logger.info(f"💡 Recommendations: {len(analysis['recommendations'])}")
                for rec in analysis["recommendations"]:
                    logger.info(f"   - {rec}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error generating performance report: {e}")
            return {"status": "error", "error": str(e)}
    
    async def monitor_continuously(self, interval_minutes: int = 60):
        """Monitor performance continuously."""
        logger.info(f"🔄 Starting continuous performance monitoring (every {interval_minutes} minutes)")
        
        while True:
            try:
                report = await self.generate_performance_report()
                
                if report.get("status") == "success":
                    status = report.get("overall_status", "unknown")
                    logger.info(f"📊 Performance Status: {status.upper()}")
                    
                    # If critical issues, log more frequently
                    if status == "critical":
                        logger.error("🚨 CRITICAL PERFORMANCE ISSUES DETECTED!")
                        # In production, you might send alerts here
                
                # Wait for next check
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"❌ Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry


async def main():
    """Main function to run performance monitoring."""
    monitor = PerformanceMonitor()
    
    # Generate single report
    report = await monitor.generate_performance_report()
    
    if report.get("status") == "success":
        print(f"\n📊 PERFORMANCE MONITORING REPORT")
        print(f"📈 Status: {report.get('overall_status', 'unknown').upper()}")
        print(f"📝 Summary: {report.get('summary', 'No summary available')}")
        
        if report.get("alerts"):
            print(f"\n⚠️ ALERTS ({len(report['alerts'])}):")
            for alert in report["alerts"]:
                print(f"   {alert['type'].upper()}: {alert['message']}")
        
        if report.get("recommendations"):
            print(f"\n💡 RECOMMENDATIONS ({len(report['recommendations'])}):")
            for rec in report["recommendations"]:
                print(f"   - {rec}")
    else:
        print(f"\n❌ Monitoring failed: {report.get('message', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(main())
