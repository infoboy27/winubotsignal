#!/usr/bin/env python3
"""Create sample data for the dashboard."""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import random

# Add packages to path
sys.path.append('/packages')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import insert, select

from common.config import get_settings
from common.database import Asset, Signal, User, SignalDirection, TimeFrame, SignalType
from common.schemas import SignalDirection as SchemaSignalDirection, TimeFrame as SchemaTimeFrame, SignalType as SchemaSignalType

settings = get_settings()

# Database setup
engine = create_async_engine(settings.database.url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_sample_data():
    """Create sample data for testing."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if assets exist, create if not
            existing_assets = await session.execute(select(Asset))
            if not existing_assets.scalars().all():
                assets_data = [
                    {"symbol": "BTC/USDT", "name": "Bitcoin", "base": "BTC", "quote": "USDT", "exchange": "binance", "active": True},
                    {"symbol": "ETH/USDT", "name": "Ethereum", "base": "ETH", "quote": "USDT", "exchange": "binance", "active": True},
                    {"symbol": "SOL/USDT", "name": "Solana", "base": "SOL", "quote": "USDT", "exchange": "binance", "active": True},
                    {"symbol": "ADA/USDT", "name": "Cardano", "base": "ADA", "quote": "USDT", "exchange": "binance", "active": True},
                    {"symbol": "DOT/USDT", "name": "Polkadot", "base": "DOT", "quote": "USDT", "exchange": "binance", "active": True},
                ]
                
                for asset_data in assets_data:
                    asset = Asset(**asset_data)
                    session.add(asset)
                
                await session.commit()
                print("Created sample assets")
            else:
                print("Assets already exist, skipping...")
            
            # Create sample signals
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT"]
            timeframes = [TimeFrame.ONE_MINUTE, TimeFrame.FIVE_MINUTES, TimeFrame.FIFTEEN_MINUTES, TimeFrame.ONE_HOUR, TimeFrame.FOUR_HOURS]
            directions = [SignalDirection.LONG, SignalDirection.SHORT]
            
            # Create signals for the last 30 days
            now = datetime.utcnow()
            for i in range(50):  # Create 50 sample signals
                # Random time within last 30 days
                signal_time = now - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                symbol = random.choice(symbols)
                timeframe = random.choice(timeframes)
                direction = random.choice(directions)
                
                # Generate realistic price levels
                base_price = random.uniform(100, 50000)  # Varies by symbol
                if symbol == "BTC/USDT":
                    base_price = random.uniform(40000, 70000)
                elif symbol == "ETH/USDT":
                    base_price = random.uniform(2000, 4000)
                elif symbol == "SOL/USDT":
                    base_price = random.uniform(50, 200)
                elif symbol == "ADA/USDT":
                    base_price = random.uniform(0.3, 1.0)
                elif symbol == "DOT/USDT":
                    base_price = random.uniform(5, 20)
                
                entry_price = base_price
                stop_loss = entry_price * (0.95 if direction == SignalDirection.LONG else 1.05)
                take_profit_1 = entry_price * (1.05 if direction == SignalDirection.LONG else 0.95)
                take_profit_2 = entry_price * (1.1 if direction == SignalDirection.LONG else 0.9)
                take_profit_3 = entry_price * (1.2 if direction == SignalDirection.LONG else 0.8)
                
                risk_reward_ratio = abs(take_profit_1 - entry_price) / abs(entry_price - stop_loss)
                
                signal = Signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=SignalType.ENTRY,
                    direction=direction,
                    score=random.uniform(0.6, 0.95),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit_1=take_profit_1,
                    take_profit_2=take_profit_2,
                    take_profit_3=take_profit_3,
                    risk_reward_ratio=risk_reward_ratio,
                    confluences={
                        "trend": random.choice([True, False]),
                        "smooth_trail": random.choice([True, False]),
                        "liquidity": random.choice([True, False]),
                        "smart_money": random.choice([True, False]),
                        "volume": random.choice([True, False])
                    },
                    created_at=signal_time,
                    updated_at=signal_time
                )
                session.add(signal)
            
            await session.commit()
            print("Created sample signals")
            
            # Create a demo user
            user = User(
                username="demo",
                email="demo@example.com",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBdPz7Y5k7QjW.",  # password: demo123
                is_active=True,
                is_admin=False,
                risk_percent=2.0,
                max_positions=5,
                telegram_enabled=False,
                discord_enabled=False,
                email_enabled=True,
                min_signal_score=0.7
            )
            session.add(user)
            
            await session.commit()
            print("Created demo user")
            
            print("Sample data creation completed successfully!")
            
        except Exception as e:
            print(f"Error creating sample data: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

if __name__ == "__main__":
    asyncio.run(create_sample_data())
