#!/usr/bin/env python3
"""Add new trading pairs to the database."""

import asyncio
import sys
import os
from datetime import datetime

# Add packages to path
sys.path.append('/packages')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from common.config import get_settings
from common.database import Asset

settings = get_settings()

# Database setup
engine = create_async_engine(settings.database.url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def add_new_pairs():
    """Add NEAR/USDT, SUI/USDT, and TRX/USDT to the database."""
    async with AsyncSessionLocal() as session:
        try:
            # New pairs to add
            new_pairs = [
                {"symbol": "NEAR/USDT", "name": "NEAR Protocol", "base": "NEAR", "quote": "USDT", "exchange": "binance", "active": True},
                {"symbol": "SUI/USDT", "name": "Sui", "base": "SUI", "quote": "USDT", "exchange": "binance", "active": True},
                {"symbol": "TRX/USDT", "name": "TRON", "base": "TRX", "quote": "USDT", "exchange": "binance", "active": True},
            ]
            
            added_count = 0
            updated_count = 0
            
            for pair_data in new_pairs:
                # Check if asset already exists
                result = await session.execute(
                    select(Asset).where(Asset.symbol == pair_data["symbol"])
                )
                existing_asset = result.scalar_one_or_none()
                
                if existing_asset:
                    # Update existing asset to ensure it's active
                    existing_asset.active = True
                    existing_asset.name = pair_data["name"]
                    existing_asset.updated_at = datetime.utcnow()
                    updated_count += 1
                    print(f"✓ Updated existing asset: {pair_data['symbol']}")
                else:
                    # Create new asset
                    asset = Asset(
                        symbol=pair_data["symbol"],
                        name=pair_data["name"],
                        base=pair_data["base"],
                        quote=pair_data["quote"],
                        exchange=pair_data["exchange"],
                        active=pair_data["active"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(asset)
                    added_count += 1
                    print(f"✓ Added new asset: {pair_data['symbol']}")
            
            await session.commit()
            
            print(f"\n✅ Successfully processed {len(new_pairs)} pairs:")
            print(f"   - Added: {added_count}")
            print(f"   - Updated: {updated_count}")
            print("\nThe following pairs are now active:")
            for pair in new_pairs:
                print(f"   • {pair['symbol']} ({pair['name']})")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error adding pairs: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_new_pairs())
