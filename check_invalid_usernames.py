#!/usr/bin/env python3
"""
Script to check for users with invalid usernames in the database.
"""

import asyncio
import asyncpg
import re
import os
from typing import List, Dict

# Username validation pattern: alphanumeric, underscore, hyphen only
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')

async def check_invalid_usernames():
    """Check for users with invalid usernames."""
    
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
        valid_users = []
        
        for user in users:
            username = user['username']
            
            # Check if username is valid
            if not USERNAME_PATTERN.match(username):
                invalid_users.append({
                    'id': user['id'],
                    'username': username,
                    'email': user['email'],
                    'is_admin': user['is_admin'],
                    'reason': get_invalid_reason(username)
                })
            else:
                valid_users.append(username)
        
        # Print results
        print("\n" + "="*80)
        print("USERNAME VALIDATION CHECK RESULTS")
        print("="*80)
        print(f"\nTotal users: {len(users)}")
        print(f"Valid usernames: {len(valid_users)}")
        print(f"Invalid usernames: {len(invalid_users)}")
        
        if invalid_users:
            print("\n" + "-"*80)
            print("USERS WITH INVALID USERNAMES:")
            print("-"*80)
            for user in invalid_users:
                print(f"\nID: {user['id']}")
                print(f"  Username: '{user['username']}'")
                print(f"  Email: {user['email']}")
                print(f"  Is Admin: {user['is_admin']}")
                print(f"  Reason: {user['reason']}")
                print(f"  Safe chars: {repr(user['username'])}")
        else:
            print("\n✅ All usernames are valid!")
        
        print("\n" + "="*80 + "\n")
        
        return invalid_users
        
    finally:
        await conn.close()

def get_invalid_reason(username: str) -> str:
    """Get reason why username is invalid."""
    reasons = []
    
    if len(username) < 3:
        reasons.append("too short (< 3 chars)")
    if len(username) > 30:
        reasons.append("too long (> 30 chars)")
    
    # Check for special characters
    invalid_chars = set()
    for char in username:
        if not (char.isalnum() or char in '_-'):
            invalid_chars.add(char)
    
    if invalid_chars:
        reasons.append(f"contains invalid chars: {', '.join(repr(c) for c in invalid_chars)}")
    
    return "; ".join(reasons) if reasons else "unknown"

if __name__ == "__main__":
    asyncio.run(check_invalid_usernames())

