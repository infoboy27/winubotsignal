#!/usr/bin/env python3
"""
Script to fix users with invalid usernames in the database.
"""

import asyncio
import asyncpg
import re
import os
from typing import List, Dict, Optional

# Username validation pattern: alphanumeric, underscore, hyphen only
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')

async def fix_invalid_usernames(dry_run: bool = True):
    """Fix users with invalid usernames."""
    
    # Database connection
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'winudb')
    db_user = os.getenv('POSTGRES_USER', 'winu')
    db_password = os.getenv('POSTGRES_PASSWORD', 'winu250420')
    
    conn = await asyncpg.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password
    )
    
    try:
        # Get all users
        users = await conn.fetch("SELECT id, username, email, is_admin FROM users")
        
        invalid_users = []
        
        for user in users:
            username = user['username']
            
            # Check if username is invalid
            if not USERNAME_PATTERN.match(username):
                # Generate a sanitized username
                sanitized = sanitize_username(username, user['email'])
                
                # Make sure the sanitized username is unique
                counter = 1
                final_username = sanitized
                while True:
                    existing = await conn.fetchval(
                        "SELECT COUNT(*) FROM users WHERE username = $1 AND id != $2",
                        final_username,
                        user['id']
                    )
                    if existing == 0:
                        break
                    final_username = f"{sanitized}_{counter}"
                    counter += 1
                
                invalid_users.append({
                    'id': user['id'],
                    'original': username,
                    'sanitized': final_username,
                    'email': user['email'],
                    'is_admin': user['is_admin']
                })
        
        # Print results
        print("\n" + "="*80)
        print("USERNAME SANITIZATION REPORT")
        print("="*80)
        print(f"\nMode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE MODE (will update database)'}")
        print(f"\nTotal users: {len(users)}")
        print(f"Users to update: {len(invalid_users)}")
        
        if invalid_users:
            print("\n" + "-"*80)
            print("PROPOSED USERNAME CHANGES:")
            print("-"*80)
            for user in invalid_users:
                print(f"\nID: {user['id']}")
                print(f"  Email: {user['email']}")
                print(f"  Original: {repr(user['original'])}")
                print(f"  New: '{user['sanitized']}'")
                print(f"  Is Admin: {user['is_admin']}")
            
            if not dry_run:
                print("\n" + "-"*80)
                print("UPDATING DATABASE...")
                print("-"*80)
                
                for user in invalid_users:
                    await conn.execute(
                        "UPDATE users SET username = $1 WHERE id = $2",
                        user['sanitized'],
                        user['id']
                    )
                    print(f"✅ Updated user ID {user['id']}: {repr(user['original'])} → '{user['sanitized']}'")
                
                print("\n✅ All usernames have been sanitized!")
            else:
                print("\n💡 Run with --apply flag to apply these changes")
        else:
            print("\n✅ No invalid usernames found!")
        
        print("\n" + "="*80 + "\n")
        
        return invalid_users
        
    finally:
        await conn.close()

def sanitize_username(username: str, email: str) -> str:
    """
    Generate a sanitized username from an invalid one.
    
    Strategy:
    1. First try to clean the existing username
    2. If that fails, use email local part
    3. If that fails, generate a generic username
    """
    # Try to clean the original username
    cleaned = username.strip()
    # Remove all invalid characters
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '', cleaned)
    
    # If we got a valid username, use it
    if len(cleaned) >= 3 and len(cleaned) <= 30:
        return cleaned
    
    # Try to use email local part
    if '@' in email:
        email_local = email.split('@')[0]
        email_clean = re.sub(r'[^a-zA-Z0-9_-]', '', email_local)
        if len(email_clean) >= 3 and len(email_clean) <= 30:
            return email_clean
    
    # Last resort: generate a generic username
    return f"user_{hash(username) % 100000:05d}"

if __name__ == "__main__":
    import sys
    
    # Check for --apply flag
    dry_run = "--apply" not in sys.argv
    
    if not dry_run:
        print("\n⚠️  WARNING: Running in LIVE MODE - database will be modified!")
        print("Press Ctrl+C within 3 seconds to cancel...\n")
        try:
            import time
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            sys.exit(0)
    
    asyncio.run(fix_invalid_usernames(dry_run=dry_run))





