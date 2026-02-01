#!/usr/bin/env python3
"""
Database migration to create trading history tables
"""

import asyncio
import asyncpg
import os

async def run_migration():
    """Run the trading history tables migration."""
    
    # Database connection
    db_url = os.getenv('DATABASE_URL', 'postgresql://winu:winu250420@localhost:5432/winudb')
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # Read the SQL file
        with open('bot/sql/create_trading_history_tables.sql', 'r') as f:
            sql_content = f.read()
        
        # Execute the migration
        await conn.execute(sql_content)
        
        print("✅ Trading history tables migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())












