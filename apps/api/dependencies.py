"""Dependencies for FastAPI application."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

import sys
sys.path.append('/packages')

from common.config import get_settings
from common.database import Base

settings = get_settings()

# Database setup
engine = create_async_engine(
    settings.database.url,
    echo=settings.monitoring.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency to get database session
async def get_db():
    """Database session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

