#!/usr/bin/env python3
"""
Test script to verify multi-account environment configuration
Run this to check if accounts are loaded correctly from production.env
"""

import os
import sys

# Load environment from production.env
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/winubotsignal/production.env')

def test_env_multi_account():
    """Test the environment-based multi-account system."""
    
    print("🔍 Testing Environment-Based Multi-Account Configuration\n")
    print("=" * 60)
    
    # Check primary account
    api_key_1 = os.getenv('BINANCE_API_KEY')
    api_secret_1 = os.getenv('BINANCE_API_SECRET')
    
    accounts_found = []
    
    if api_key_1 and api_secret_1:
        accounts_found.append({
            'num': 1,
            'key': api_key_1[:10] + '...' + api_key_1[-10:] if len(api_key_1) > 20 else api_key_1,
            'secret': '*' * 10
        })
        print("✅ Account 1 (Primary):")
        print(f"   API Key: {api_key_1[:10]}...{api_key_1[-10:]}")
        print(f"   Secret:  {'*' * 20}\n")
    else:
        print("❌ Account 1: NOT FOUND\n")
    
    # Check additional accounts
    account_num = 2
    while account_num <= 10:  # Check up to 10 accounts
        api_key = os.getenv(f'BINANCE_API_KEY_{account_num}')
        api_secret = os.getenv(f'BINANCE_API_SECRET_{account_num}')
        
        if not api_key or not api_secret:
            if account_num == 2:
                print(f"ℹ️  Account 2: Not configured (optional)")
                print(f"   To add Account 2, set BINANCE_API_KEY_2 and BINANCE_API_SECRET_2 in production.env\n")
            break
        
        accounts_found.append({
            'num': account_num,
            'key': api_key[:10] + '...' + api_key[-10:] if len(api_key) > 20 else api_key,
            'secret': '*' * 10
        })
        
        print(f"✅ Account {account_num}:")
        print(f"   API Key: {api_key[:10]}...{api_key[-10:]}")
        print(f"   Secret:  {'*' * 20}\n")
        
        account_num += 1
    
    print("=" * 60)
    print(f"\n📊 Summary: {len(accounts_found)} account(s) configured\n")
    
    if len(accounts_found) == 0:
        print("❌ No accounts found!")
        print("   Please add BINANCE_API_KEY and BINANCE_API_SECRET to production.env\n")
        return False
    
    if len(accounts_found) == 1:
        print("ℹ️  Single account mode")
        print("   To enable multi-account trading:")
        print("   1. Add BINANCE_API_KEY_2=... to production.env")
        print("   2. Add BINANCE_API_SECRET_2=... to production.env")
        print("   3. Restart the bot\n")
    else:
        print(f"🎯 Multi-account mode: {len(accounts_found)} accounts will trade simultaneously")
        print("   When a signal is generated:")
        for acc in accounts_found:
            print(f"   • Account {acc['num']} will execute the trade")
        print()
    
    # Check other relevant settings
    print("=" * 60)
    print("\n⚙️  Trading Settings:\n")
    
    leverage = os.getenv('BOT_LEVERAGE', 'Not set (default: 10.0)')
    test_mode = os.getenv('BOT_TEST_MODE', 'Not set (default: false)')
    discord = os.getenv('DISCORD_WEBHOOK_URL', 'Not configured')
    
    print(f"   Leverage:     {leverage}")
    print(f"   Test Mode:    {test_mode}")
    print(f"   Discord:      {'✅ Configured' if discord != 'Not configured' else '❌ Not configured'}")
    print()
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" WINU BOT - Multi-Account Environment Test")
    print("=" * 60 + "\n")
    
    success = test_env_multi_account()
    
    if success:
        print("=" * 60)
        print("\n✅ Test completed successfully!")
        print("\n💡 Next steps:")
        print("   1. If you need to add more accounts, edit production.env")
        print("   2. Restart the bot: docker-compose -f docker-compose.traefik.yml restart bot")
        print("   3. Check logs: docker logs winu-bot-signal-bot -f\n")
    else:
        print("=" * 60)
        print("\n❌ Test failed. Please check your production.env configuration.\n")
        sys.exit(1)





