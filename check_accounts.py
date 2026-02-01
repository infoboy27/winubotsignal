#!/usr/bin/env python3
"""
Check balance and positions for all configured Binance accounts
"""

import os
import sys
import ccxt
import asyncio
from datetime import datetime

# Load environment from production.env
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/winubotsignal/production.env')


def get_account_info(api_key, api_secret, account_name):
    """Get balance and position info for a Binance account."""
    try:
        print(f"\n{'='*60}")
        print(f"📊 {account_name}")
        print(f"{'='*60}")
        
        # Initialize Binance
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        
        # Get account balance
        print("\n💰 Account Balance:")
        balance = exchange.fetch_balance()
        
        usdt_free = balance.get('USDT', {}).get('free', 0)
        usdt_used = balance.get('USDT', {}).get('used', 0)
        usdt_total = balance.get('USDT', {}).get('total', 0)
        
        print(f"   Free USDT:     ${usdt_free:,.2f}")
        print(f"   Used USDT:     ${usdt_used:,.2f}")
        print(f"   Total USDT:    ${usdt_total:,.2f}")
        
        # Get positions
        print("\n📈 Open Positions:")
        try:
            positions = exchange.fetch_positions()
            
            open_positions = [p for p in positions if p.get('contracts') and float(p.get('contracts', 0)) != 0]
            
            if open_positions:
                for pos in open_positions:
                    symbol = pos.get('symbol', 'Unknown')
                    side = pos.get('side', 'Unknown')
                    contracts = float(pos.get('contracts', 0))
                    entry_price = float(pos.get('entryPrice', 0))
                    unrealized_pnl = float(pos.get('unrealizedPnl', 0))
                    percentage = float(pos.get('percentage', 0)) if pos.get('percentage') else 0
                    leverage = float(pos.get('leverage', 1)) if pos.get('leverage') else 1
                    
                    pnl_emoji = "📈" if unrealized_pnl > 0 else "📉"
                    
                    print(f"\n   {pnl_emoji} {symbol} - {side.upper()}")
                    print(f"      Contracts:     {contracts:.4f}")
                    print(f"      Entry Price:   ${entry_price:,.2f}")
                    print(f"      Leverage:      {leverage}x")
                    print(f"      Unrealized PNL: ${unrealized_pnl:,.2f} ({percentage:.2f}%)")
            else:
                print("   ℹ️  No open positions")
        except Exception as e:
            print(f"   ⚠️  Could not fetch positions: {e}")
        
        # Get account information
        print("\n⚙️  Account Info:")
        try:
            # Use the correct method for Binance Futures
            account_info = exchange.fapiPrivateGetAccount()
            
            total_wallet_balance = float(account_info.get('totalWalletBalance', 0))
            total_unrealized_profit = float(account_info.get('totalUnrealizedProfit', 0))
            total_margin_balance = float(account_info.get('totalMarginBalance', 0))
            available_balance = float(account_info.get('availableBalance', 0))
        except:
            # Fallback to balance info
            total_wallet_balance = usdt_total
            total_unrealized_profit = 0
            total_margin_balance = usdt_total
            available_balance = usdt_free
        
        print(f"   Wallet Balance:    ${total_wallet_balance:,.2f}")
        print(f"   Margin Balance:    ${total_margin_balance:,.2f}")
        print(f"   Available:         ${available_balance:,.2f}")
        print(f"   Unrealized PNL:    ${total_unrealized_profit:,.2f}")
        
        # Calculate position size for bot (2% or $100 max)
        position_size = min(available_balance * 0.02, 100)
        leverage = float(os.getenv('BOT_LEVERAGE', '20.0'))
        notional_size = position_size * leverage
        
        print(f"\n🤖 Bot Trading Settings:")
        print(f"   Position Size:     ${position_size:.2f} (2% of available)")
        print(f"   With {leverage}x Leverage: ${notional_size:,.2f} notional")
        print(f"   Status:            {'✅ Ready' if available_balance >= 10 else '⚠️ Low balance (min $10)'}")
        
        return {
            'success': True,
            'balance': usdt_total,
            'available': available_balance,
            'positions': len(open_positions),
            'unrealized_pnl': total_unrealized_profit
        }
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def main():
    print("\n" + "="*60)
    print(" 🔍 MULTI-ACCOUNT VERIFICATION")
    print("="*60)
    
    accounts = []
    results = []
    
    # Check Account 1
    api_key_1 = os.getenv('BINANCE_API_KEY')
    api_secret_1 = os.getenv('BINANCE_API_SECRET')
    
    if api_key_1 and api_secret_1:
        result = get_account_info(api_key_1, api_secret_1, "Account 1 (Primary)")
        results.append(result)
        accounts.append("Account 1")
    
    # Check Account 2
    api_key_2 = os.getenv('BINANCE_API_KEY_2')
    api_secret_2 = os.getenv('BINANCE_API_SECRET_2')
    
    if api_key_2 and api_secret_2:
        result = get_account_info(api_key_2, api_secret_2, "Account 2")
        results.append(result)
        accounts.append("Account 2")
    
    # Check Account 3
    api_key_3 = os.getenv('BINANCE_API_KEY_3')
    api_secret_3 = os.getenv('BINANCE_API_SECRET_3')
    
    if api_key_3 and api_secret_3:
        result = get_account_info(api_key_3, api_secret_3, "Account 3")
        results.append(result)
        accounts.append("Account 3")
    
    # Summary
    print("\n" + "="*60)
    print(" 📊 SUMMARY")
    print("="*60)
    
    total_balance = sum(r.get('balance', 0) for r in results if r.get('success'))
    total_available = sum(r.get('available', 0) for r in results if r.get('success'))
    total_positions = sum(r.get('positions', 0) for r in results if r.get('success'))
    total_pnl = sum(r.get('unrealized_pnl', 0) for r in results if r.get('success'))
    
    print(f"\n✅ Configured Accounts: {len(accounts)}")
    for acc in accounts:
        print(f"   • {acc}")
    
    print(f"\n💰 Combined Balances:")
    print(f"   Total Balance:     ${total_balance:,.2f}")
    print(f"   Total Available:   ${total_available:,.2f}")
    
    print(f"\n📈 Combined Positions:")
    print(f"   Open Positions:    {total_positions}")
    print(f"   Total Unrealized:  ${total_pnl:,.2f}")
    
    # Bot trading calculation
    leverage = float(os.getenv('BOT_LEVERAGE', '20.0'))
    combined_position_size = sum(min(r.get('available', 0) * 0.02, 100) for r in results if r.get('success'))
    combined_notional = combined_position_size * leverage
    
    print(f"\n🤖 Next Signal Will Trade:")
    print(f"   Combined Position: ${combined_position_size:.2f}")
    print(f"   With {leverage}x Leverage: ${combined_notional:,.2f} notional")
    print(f"   Across {len(accounts)} accounts")
    
    print("\n" + "="*60)
    print(" ✅ VERIFICATION COMPLETE")
    print("="*60)
    
    # Status
    all_success = all(r.get('success') for r in results)
    
    if all_success:
        print("\n✅ All accounts are configured correctly!")
        print("✅ Multi-account trading is ready!")
        print("\n💡 The bot will execute signals on all accounts automatically.")
    else:
        print("\n⚠️  Some accounts had errors. Check the output above.")
    
    print()


if __name__ == "__main__":
    main()

