"""
Environment-Based Multi-Account Executor
Automatically detects and trades on multiple Binance accounts from production.env
"""

import sys
import os
import ccxt
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Add packages to path
sys.path.append('/packages')

from common.logging import get_logger

logger = get_logger(__name__)


class EnvMultiAccountExecutor:
    """Executes trades on multiple Binance accounts from environment variables."""
    
    def __init__(self, test_mode: bool = False):
        """
        Initialize multi-account executor from environment variables.
        
        Reads:
        - BINANCE_API_KEY / BINANCE_API_SECRET (Account 1)
        - BINANCE_API_KEY_2 / BINANCE_API_SECRET_2 (Account 2)
        - BINANCE_API_KEY_3 / BINANCE_API_SECRET_3 (Account 3)
        ... and so on
        
        Args:
            test_mode: Use testnet if True
        """
        self.test_mode = test_mode
        self.accounts = []
        self._load_accounts_from_env()
        
    def _load_accounts_from_env(self):
        """Load all Binance accounts from environment variables."""
        # Load primary account (no suffix)
        api_key_1 = os.getenv('BINANCE_API_KEY')
        api_secret_1 = os.getenv('BINANCE_API_SECRET')
        
        if api_key_1 and api_secret_1:
            self.accounts.append({
                'name': 'Account 1',
                'api_key': api_key_1,
                'api_secret': api_secret_1,
                'exchange': None
            })
            logger.info("✅ Loaded Account 1 from BINANCE_API_KEY")
        
        # Load additional accounts (with _2, _3, _4, etc. suffixes)
        account_num = 2
        while True:
            api_key = os.getenv(f'BINANCE_API_KEY_{account_num}')
            api_secret = os.getenv(f'BINANCE_API_SECRET_{account_num}')
            
            if not api_key or not api_secret:
                break  # No more accounts
                
            self.accounts.append({
                'name': f'Account {account_num}',
                'api_key': api_key,
                'api_secret': api_secret,
                'exchange': None
            })
            logger.info(f"✅ Loaded Account {account_num} from BINANCE_API_KEY_{account_num}")
            account_num += 1
        
        if not self.accounts:
            logger.error("❌ No Binance accounts found in environment variables!")
            logger.error("Add BINANCE_API_KEY/BINANCE_API_SECRET to production.env")
        else:
            logger.info(f"🎯 Total accounts loaded: {len(self.accounts)}")
        
        # Initialize exchanges for all accounts
        for account in self.accounts:
            account['exchange'] = self._initialize_exchange(
                account['api_key'], 
                account['api_secret']
            )
    
    def _initialize_exchange(self, api_key: str, api_secret: str):
        """Initialize Binance exchange connection for an account."""
        try:
            if self.test_mode:
                exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': True,
                    'options': {
                        'defaultType': 'future',
                        'test': True
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
            else:
                exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': False,
                    'options': {
                        'defaultType': 'future'
                    },
                    'rateLimit': 1200,
                    'enableRateLimit': True
                })
            
            return exchange
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            return None
    
    async def execute_signal_on_all_accounts(self, signal: Dict) -> Dict:
        """
        Execute a trading signal on all accounts in parallel.
        
        Args:
            signal: Trading signal with entry_price, stop_loss, take_profit, etc.
            
        Returns:
            Dict with execution results for all accounts
        """
        if not self.accounts:
            return {
                'success': False,
                'error': 'No accounts configured',
                'results': []
            }
        
        logger.info(f"🚀 Executing signal on {len(self.accounts)} accounts...")
        
        # Execute on all accounts in parallel
        tasks = [
            self._execute_on_account(account, signal) 
            for account in self.accounts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        failed = len(results) - successful
        
        summary = {
            'success': successful > 0,
            'total_accounts': len(self.accounts),
            'successful_accounts': successful,
            'failed_accounts': failed,
            'results': results,
            'signal': {
                'symbol': signal.get('symbol'),
                'direction': signal.get('direction'),
                'entry_price': signal.get('entry_price')
            }
        }
        
        logger.info(f"✅ Multi-account execution complete: {successful}/{len(self.accounts)} successful")
        
        # Send summary notification
        await self._send_summary_notification(summary)
        
        return summary
    
    async def _execute_on_account(self, account: Dict, signal: Dict) -> Dict:
        """Execute signal on a single account."""
        try:
            exchange = account['exchange']
            if not exchange:
                return {
                    'success': False,
                    'account': account['name'],
                    'error': 'Exchange not initialized'
                }
            
            # Get account balance (check both free and total)
            balance = await asyncio.get_event_loop().run_in_executor(
                None, exchange.fetch_balance
            )
            
            usdt_info = balance.get('USDT', {})
            usdt_balance = usdt_info.get('free', 0)
            total_balance = usdt_info.get('total', 0)
            
            # If free is 0 but total is available, log warning
            if usdt_balance < 10:
                if total_balance > 10:
                    logger.warning(f"{account['name']}: Low free balance (${usdt_balance:.2f}) but total is ${total_balance:.2f}")
                return {
                    'success': False,
                    'account': account['name'],
                    'error': f'Insufficient balance: ${usdt_balance:.2f}'
                }
            
            # Calculate position size (2% of balance or $100, whichever is smaller)
            position_size_usd = min(usdt_balance * 0.02, 100)
            
            # Get leverage from environment (default 10x)
            leverage = float(os.getenv('BOT_LEVERAGE', '10.0'))
            
            # Set leverage on the exchange
            symbol = signal.get('symbol', 'BTC/USDT')
            
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: exchange.set_leverage(int(leverage), symbol)
                )
            except Exception as lev_error:
                logger.warning(f"Could not set leverage for {symbol}: {lev_error}")
            
            # Calculate quantity
            entry_price = float(signal.get('entry_price', 0))
            if entry_price == 0:
                return {
                    'success': False,
                    'account': account['name'],
                    'error': 'Invalid entry price'
                }
            
            quantity = (position_size_usd * leverage) / entry_price
            
            # Get market info for precision and limits
            markets = await asyncio.get_event_loop().run_in_executor(
                None, lambda: exchange.load_markets()
            )
            market_info = markets.get(symbol, {})
            
            # Get precision and limits
            precision = market_info.get('precision', {}).get('amount', 3)
            min_amount = market_info.get('limits', {}).get('amount', {}).get('min', 0.001)
            
            # Round quantity to precision
            quantity = round(quantity, precision)
            
            # Check minimum amount
            if quantity < min_amount:
                logger.warning(f"{account['name']}: Calculated quantity {quantity} is below minimum {min_amount}")
                return {
                    'success': False,
                    'account': account['name'],
                    'error': f'Quantity {quantity} below minimum {min_amount} for {symbol}'
                }
            
            # Determine order side
            direction = signal.get('direction', 'LONG').upper()
            side = 'buy' if direction == 'LONG' else 'sell'
            
            # Place market order
            order = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=quantity,
                    params={'reduceOnly': False}
                )
            )
            
            # Get actual fill price from the order
            actual_entry = float(order.get('average') or order.get('price') or entry_price)
            
            # DISABLED: Automatic Stop Loss and Take Profit orders
            # User requested manual management only - bot will just place the trade
            logger.info(f"⚠️  Auto SL/TP disabled - Manual management required on exchange")
            
            logger.info(f"✅ {account['name']}: Order executed - {side.upper()} {quantity:.4f} {symbol} @ ${entry_price:.2f}")
            
            # Send individual notification
            await self._send_order_notification(account['name'], signal, order, position_size_usd)
            
            return {
                'success': True,
                'account': account['name'],
                'order': order,
                'quantity': quantity,
                'position_size_usd': position_size_usd,
                'leverage': leverage
            }
            
        except Exception as e:
            logger.error(f"❌ {account['name']}: Execution failed - {e}")
            return {
                'success': False,
                'account': account['name'],
                'error': str(e)
            }
    
    async def _send_order_notification(self, account_name: str, signal: Dict, order: Dict, position_size: float):
        """Send Discord notification for individual order."""
        try:
            import aiohttp
            
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                return
            
            symbol = signal.get('symbol', 'Unknown')
            direction = signal.get('direction', 'UNKNOWN').upper()
            entry_price = signal.get('entry_price', 0)
            
            color = 0x00ff00 if direction == 'LONG' else 0xff0000
            
            embed = {
                'title': f'🎯 Order Executed - {account_name}',
                'description': f'**{symbol} {direction}**',
                'color': color,
                'fields': [
                    {'name': 'Entry Price', 'value': f'${entry_price:.2f}', 'inline': True},
                    {'name': 'Position Size', 'value': f'${position_size:.2f}', 'inline': True},
                    {'name': 'Stop Loss', 'value': f'${signal.get("stop_loss", 0):.2f}', 'inline': True},
                    {'name': 'Take Profit', 'value': f'${signal.get("take_profit_1", 0):.2f}', 'inline': True},
                ],
                'timestamp': datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json={'embeds': [embed]})
                
        except Exception as e:
            logger.error(f"Failed to send order notification: {e}")
    
    async def _send_summary_notification(self, summary: Dict):
        """Send Discord summary notification for all accounts."""
        try:
            import aiohttp
            
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                return
            
            total = summary['total_accounts']
            successful = summary['successful_accounts']
            failed = summary['failed_accounts']
            
            signal_info = summary['signal']
            symbol = signal_info.get('symbol', 'Unknown')
            direction = signal_info.get('direction', 'UNKNOWN')
            
            # Build success/failure lists
            success_list = []
            failure_list = []
            
            for result in summary['results']:
                if isinstance(result, dict):
                    account = result.get('account', 'Unknown')
                    if result.get('success'):
                        success_list.append(f"✅ {account}")
                    else:
                        error = result.get('error', 'Unknown error')
                        failure_list.append(f"❌ {account}: {error}")
            
            description = f"**Signal: {symbol} {direction}**\n\n"
            description += f"**Success Rate: {successful}/{total}**\n\n"
            
            if success_list:
                description += "**Successful:**\n" + "\n".join(success_list) + "\n\n"
            
            if failure_list:
                description += "**Failed:**\n" + "\n".join(failure_list)
            
            color = 0x00ff00 if successful > failed else 0xffaa00
            
            embed = {
                'title': '📊 Multi-Account Execution Summary',
                'description': description,
                'color': color,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json={'embeds': [embed]})
                
        except Exception as e:
            logger.error(f"Failed to send summary notification: {e}")
    
    async def get_all_balances(self) -> List[Dict]:
        """Get balances from all accounts."""
        balances = []
        
        for account in self.accounts:
            try:
                exchange = account['exchange']
                if not exchange:
                    continue
                
                balance = await asyncio.get_event_loop().run_in_executor(
                    None, exchange.fetch_balance
                )
                
                usdt_balance = balance.get('USDT', {}).get('free', 0)
                
                balances.append({
                    'account': account['name'],
                    'balance': usdt_balance,
                    'currency': 'USDT'
                })
                
            except Exception as e:
                logger.error(f"Failed to get balance for {account['name']}: {e}")
                balances.append({
                    'account': account['name'],
                    'balance': 0,
                    'error': str(e)
                })
        
        return balances
    
    def get_account_count(self) -> int:
        """Get number of configured accounts."""
        return len(self.accounts)


# Helper function to get the executor instance
_executor_instance = None

def get_env_multi_account_executor(test_mode: bool = False) -> EnvMultiAccountExecutor:
    """Get or create the multi-account executor instance."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = EnvMultiAccountExecutor(test_mode=test_mode)
    return _executor_instance




