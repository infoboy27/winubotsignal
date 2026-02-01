#!/usr/bin/env python3
"""Migration: Add email verification table and user email_verified field."""

import asyncio
import sys
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the packages directory to the path
sys.path.append('/home/ubuntu/winubotsignal/packages')

from common.config import get_settings

async def run_migration():
    """Run the migration to add email verification support."""
    settings = get_settings()
    
    # Create database engine
    engine = create_async_engine(settings.database.url)
    
    async with engine.begin() as conn:
        print("🔄 Running migration: Add email verification table...")
        
        # Create email_verifications table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_verifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                email VARCHAR(255) NOT NULL,
                code VARCHAR(10) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_used BOOLEAN DEFAULT FALSE NOT NULL,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            );
        """))
        
        # Add email_verified column to users table if it doesn't exist
        await conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE NOT NULL;
        """))
        
        # Create indexes for better performance
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_verifications_user_id 
            ON email_verifications(user_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_verifications_email 
            ON email_verifications(email);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_verifications_code 
            ON email_verifications(code);
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_verifications_expires_at 
            ON email_verifications(expires_at);
        """))
        
        print("✅ Migration completed successfully!")
        print("   - Created email_verifications table")
        print("   - Added email_verified column to users table")
        print("   - Created performance indexes")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
