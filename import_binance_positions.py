#!/usr/bin/env python3
"""
Import open positions from Binance to the dashboard database.
This helps sync manually placed orders with the bot's tracking system.
"""

import ccxt
import asyncpg
import asyncio
from datetime import datetime
import os

# Load environment variables from production.env
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/winubotsignal/production.env')

# Get Binance credentials
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')


async def import_binance_positions():
    """Fetch positions from Binance and import them to database."""
    
    # Initialize Binance exchange
    exchange = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET_KEY,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        }
    })
    
    # Connect to database
    conn = await asyncpg.connect(
        host='winu-bot-signal-postgres',
        port=5432,
        user='winu',
        password='winu250420',
        database='winudb'
    )
    
    try:
        print("\n🔍 Fetching positions from Binance...")
        
        # Get futures positions
        positions = exchange.fetch_positions()
        open_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
        
        print(f"✅ Found {len(open_positions)} open positions on Binance\n")
        
        if not open_positions:
            print("No open positions to import.")
            return
        
        imported = 0
        for pos in open_positions:
            try:
                symbol = pos['symbol']
                side = 'LONG' if pos['side'] == 'long' else 'SHORT'
                entry_price = float(pos.get('entryPrice', 0))
                contracts = float(pos.get('contracts', 0))
                unrealized_pnl = float(pos.get('unrealizedPnl', 0))
                leverage = float(pos.get('leverage', 1))
                
                # Check if position already exists in DB
                existing = await conn.fetchrow(
                    "SELECT id FROM paper_positions WHERE symbol = $1 AND is_open = true",
                    symbol
                )
                
                if existing:
                    print(f"⏭️  {symbol} already in database, skipping...")
                    continue
                
                # Insert position into database
                await conn.execute("""
                    INSERT INTO paper_positions (
                        symbol, side, entry_price, quantity, current_price,
                        unrealized_pnl, stop_loss, take_profit, market_type,
                        is_open, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    symbol, side, entry_price, abs(contracts), entry_price,
                    unrealized_pnl, None, None, 'futures',
                    True, datetime.utcnow(), datetime.utcnow()
                )
                
                print(f"✅ Imported: {symbol} {side} @ ${entry_price} ({abs(contracts)} contracts)")
                print(f"   Unrealized PnL: ${unrealized_pnl:.2f}")
                print()
                imported += 1
                
            except Exception as e:
                print(f"❌ Error importing {pos.get('symbol', 'unknown')}: {e}")
        
        print(f"\n🎉 Successfully imported {imported} positions!")
        print(f"They should now be visible on bot.winu.app dashboard")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(import_binance_positions())

