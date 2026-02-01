#!/usr/bin/env python3
"""Check signal statistics and confidence levels."""

import asyncio
import asyncpg
import os
from datetime import datetime, timedelta

async def check_signal_stats():
    """Check signal statistics."""
    
    # Database connection
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database=os.getenv('POSTGRES_DB', 'winudb'),
        user=os.getenv('POSTGRES_USER', 'winu'),
        password=os.getenv('POSTGRES_PASSWORD', 'winu250420')
    )
    
    try:
        # Get signal counts by confidence level
        print("\n" + "="*80)
        print("📊 SIGNAL CONFIDENCE ANALYSIS")
        print("="*80)
        
        # Total signals
        total = await conn.fetchval("SELECT COUNT(*) FROM signals")
        print(f"\n📈 Total Signals in Database: {total}")
        
        # Active signals
        active = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE is_active = true")
        print(f"✅ Active Signals: {active}")
        
        # Signals by confidence level
        high_conf = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE score >= 0.80"
        )
        medium_conf = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE score >= 0.60 AND score < 0.80"
        )
        low_conf = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE score < 0.60"
        )
        
        print(f"\n📊 By Confidence Level:")
        print(f"   🔴 HIGH (≥80%):    {high_conf:>6} signals ({high_conf/total*100:.1f}%)" if total > 0 else "   🔴 HIGH (≥80%):         0 signals")
        print(f"   🟠 MEDIUM (60-80%): {medium_conf:>6} signals ({medium_conf/total*100:.1f}%)" if total > 0 else "   🟠 MEDIUM (60-80%):     0 signals")
        print(f"   🟡 LOW (<60%):      {low_conf:>6} signals ({low_conf/total*100:.1f}%)" if total > 0 else "   🟡 LOW (<60%):          0 signals")
        
        # Recent signals (last 24 hours)
        recent_24h = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '24 hours'"
        )
        recent_high = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '24 hours' AND score >= 0.80"
        )
        recent_medium = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '24 hours' AND score >= 0.60 AND score < 0.80"
        )
        
        print(f"\n⏰ Last 24 Hours:")
        print(f"   Total:   {recent_24h} signals")
        print(f"   🔴 HIGH:  {recent_high} signals")
        print(f"   🟠 MEDIUM: {recent_medium} signals")
        
        # Recent signals (last 7 days)
        recent_7d = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '7 days'"
        )
        recent_7d_high = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '7 days' AND score >= 0.80"
        )
        
        print(f"\n📅 Last 7 Days:")
        print(f"   Total:   {recent_7d} signals")
        print(f"   🔴 HIGH:  {recent_7d_high} signals")
        
        # Top 10 highest confidence signals
        top_signals = await conn.fetch("""
            SELECT symbol, direction, score, entry_price, created_at, is_active
            FROM signals
            ORDER BY score DESC, created_at DESC
            LIMIT 10
        """)
        
        print(f"\n🏆 Top 10 Highest Confidence Signals:")
        print("-" * 80)
        for i, signal in enumerate(top_signals, 1):
            status = "✅" if signal['is_active'] else "⏹️"
            age = datetime.utcnow() - signal['created_at']
            if age.days > 0:
                age_str = f"{age.days}d ago"
            elif age.seconds >= 3600:
                age_str = f"{age.seconds//3600}h ago"
            else:
                age_str = f"{age.seconds//60}m ago"
            
            print(f"{i:2}. {status} {signal['symbol']:12} {signal['direction']:5} "
                  f"Score: {signal['score']:.3f} ({signal['score']*100:.1f}%) "
                  f"Entry: ${signal['entry_price']:>10,.2f} - {age_str}")
        
        # Signals by direction
        long_signals = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE direction = 'LONG'")
        short_signals = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE direction = 'SHORT'")
        
        print(f"\n📊 By Direction:")
        print(f"   📈 LONG:  {long_signals} signals ({long_signals/total*100:.1f}%)" if total > 0 else "   📈 LONG:  0 signals")
        print(f"   📉 SHORT: {short_signals} signals ({short_signals/total*100:.1f}%)" if total > 0 else "   📉 SHORT: 0 signals")
        
        # Signals by symbol
        by_symbol = await conn.fetch("""
            SELECT symbol, COUNT(*) as count, AVG(score) as avg_score, MAX(score) as max_score
            FROM signals
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print(f"\n💰 Top Symbols by Signal Count:")
        print("-" * 80)
        for i, row in enumerate(by_symbol, 1):
            print(f"{i:2}. {row['symbol']:12} - {row['count']:>4} signals | "
                  f"Avg: {row['avg_score']:.3f} | Max: {row['max_score']:.3f}")
        
        # Average scores
        avg_score = await conn.fetchval("SELECT AVG(score) FROM signals")
        avg_active = await conn.fetchval("SELECT AVG(score) FROM signals WHERE is_active = true")
        
        print(f"\n📊 Average Scores:")
        print(f"   Overall:       {avg_score:.3f} ({avg_score*100:.1f}%)" if avg_score else "   Overall:       N/A")
        print(f"   Active Only:   {avg_active:.3f} ({avg_active*100:.1f}%)" if avg_active else "   Active Only:   N/A")
        
        # Score distribution
        print(f"\n📈 Score Distribution:")
        score_ranges = [
            (0.90, 1.00, "90-100%"),
            (0.80, 0.90, "80-90%"),
            (0.70, 0.80, "70-80%"),
            (0.60, 0.70, "60-70%"),
            (0.50, 0.60, "50-60%"),
            (0.00, 0.50, "0-50%"),
        ]
        
        for min_score, max_score, label in score_ranges:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM signals WHERE score >= $1 AND score < $2",
                min_score, max_score
            )
            if total > 0:
                bar = "█" * int(count / total * 50) if count > 0 else ""
                print(f"   {label:8} {count:>6} {bar}")
        
        print("\n" + "="*80 + "\n")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_signal_stats())





