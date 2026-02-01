#!/usr/bin/env python3
"""
Test script for signal selector debugging
"""

import sys
import asyncio
import asyncpg
from datetime import datetime

# Add packages to path
sys.path.append('/packages')

async def test_signal_selector():
    """Test the signal selector step by step."""
    
    # Connect to database
    conn = await asyncpg.connect(
        host='winu-bot-signal-postgres',
        port=5432,
        user='winu',
        password='winu250420',
        database='winudb'
    )
    
    print("🔍 Testing Signal Selector Step by Step...")
    
    # Step 1: Check basic query
    print("\n📊 Step 1: Basic signal query")
    signals = await conn.fetch("""
        SELECT id, symbol, direction, score, entry_price, take_profit_1, stop_loss, 
               created_at, confluences, context
        FROM signals 
        WHERE is_active = true 
        AND score >= 0.8
        AND created_at >= NOW() - INTERVAL '24 hours'
        ORDER BY score DESC, created_at DESC
        LIMIT 10
    """)
    
    print(f"Found {len(signals)} signals with score >= 0.8")
    
    if not signals:
        print("❌ No signals found in basic query")
        await conn.close()
        return
    
    # Step 2: Test each signal individually
    print(f"\n📈 Step 2: Testing {len(signals)} signals individually")
    
    for i, signal in enumerate(signals):
        print(f"\n--- Signal {i+1}: {signal['symbol']} {signal['direction']} (Score: {signal['score']}) ---")
        
        # Check performance data
        performance = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_trades,
                COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as winning_trades,
                AVG(realized_pnl) as avg_pnl,
                AVG(score) as avg_score
            FROM signals 
            WHERE symbol = $1 AND created_at >= NOW() - INTERVAL '7 days' AND realized_pnl != 0
        """, signal['symbol'])
        
        if performance and performance['total_trades'] > 0:
            win_rate = (performance['winning_trades'] / performance['total_trades']) * 100
            print(f"  Performance: {win_rate:.1f}% win rate, {performance['total_trades']} trades")
        else:
            print(f"  Performance: No historical data")
        
        # Check market conditions (simplified)
        print(f"  Market: Entry ${signal['entry_price']:.2f}, TP ${signal['take_profit_1']:.2f}, SL ${signal['stop_loss']:.2f}")
        
        # Calculate quality score
        base_score = signal['score']
        performance_bonus = 0.05 if performance and performance['total_trades'] > 0 and (performance['winning_trades'] / performance['total_trades']) > 0.5 else 0
        market_bonus = 0.05  # Assume good market conditions
        trend_bonus = 0.05   # Assume trend alignment
        
        quality_score = base_score + performance_bonus + market_bonus + trend_bonus
        quality_score = min(1.0, quality_score)
        
        print(f"  Quality Score: {quality_score:.3f} (Base: {base_score:.2f} + Bonuses: {performance_bonus + market_bonus + trend_bonus:.2f})")
        
        if quality_score > 0.8:
            print(f"  ✅ This signal would be selected!")
            break
        else:
            print(f"  ❌ Quality score too low")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_signal_selector())
















