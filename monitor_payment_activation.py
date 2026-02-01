#!/usr/bin/env python3
"""
Payment & Subscription Activation Monitor
Monitors user activation process after payment and logs issues
"""

import asyncio
import asyncpg
import os
from datetime import datetime, timedelta
from typing import Dict, List
import json
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich import box
import time

console = Console()

# Discord webhook URL for payment notifications
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1425572155751399616/i5VBCt_sm4eYpcUJ8aG3AoFJuDfEAAlV1asqqbURnqGjTP4H2KkzXwrsAk2DbSXVOH-y"

# Database configuration
# First try to get from environment, then use production values
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    # Use production.env values
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'winu')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'winu250420')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'winudb')
    DATABASE_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

class PaymentMonitor:
    def __init__(self):
        self.db_pool = None
        self.alert_logs = []
        self.notified_payment_ids = set()  # Track which payments we've already notified about
        
    async def connect_db(self):
        """Connect to database."""
        try:
            self.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
            console.print("✅ [green]Connected to database[/green]")
            return True
        except Exception as e:
            console.print(f"❌ [red]Database connection failed: {e}[/red]")
            return False
    
    async def close_db(self):
        """Close database connection."""
        if self.db_pool:
            await self.db_pool.close()
            console.print("🔌 [yellow]Database connection closed[/yellow]")
    
    async def send_discord_notification(self, message_type: str, data: Dict):
        """Send notification to Discord webhook."""
        try:
            # Determine color based on message type
            colors = {
                "payment_gap": 0xFF0000,      # Red - Critical
                "payment_success": 0x00FF00,  # Green - Success
                "payment_failed": 0xFF6600,   # Orange - Warning
                "payment_pending": 0xFFFF00,  # Yellow - Pending
            }
            
            color = colors.get(message_type, 0x0099FF)  # Default blue
            
            # Build embed based on type
            if message_type == "payment_gap":
                embed = {
                    "title": "🚨 Payment Activation Gap Detected!",
                    "description": f"Payment completed but user subscription NOT activated",
                    "color": color,
                    "fields": [
                        {"name": "User ID", "value": str(data.get('user_id')), "inline": True},
                        {"name": "Username", "value": data.get('username', 'N/A'), "inline": True},
                        {"name": "Plan", "value": data.get('plan_id', 'N/A'), "inline": True},
                        {"name": "Payment Status", "value": data.get('payment_status'), "inline": True},
                        {"name": "User Subscription", "value": data.get('subscription_status', 'N/A'), "inline": True},
                        {"name": "Transaction ID", "value": data.get('transaction_id', 'N/A'), "inline": False},
                        {"name": "Payment Time", "value": data.get('payment_created', 'N/A'), "inline": True},
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "Winu Bot Payment Monitor"}
                }
            elif message_type == "payment_success":
                embed = {
                    "title": "✅ Payment Successful & Activated",
                    "description": f"User subscription activated successfully",
                    "color": color,
                    "fields": [
                        {"name": "User ID", "value": str(data.get('user_id')), "inline": True},
                        {"name": "Username", "value": data.get('username', 'N/A'), "inline": True},
                        {"name": "Plan", "value": data.get('plan_id', 'N/A'), "inline": True},
                        {"name": "Amount", "value": data.get('amount', 'N/A'), "inline": True},
                        {"name": "Transaction ID", "value": data.get('transaction_id', 'N/A'), "inline": False},
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "Winu Bot Payment Monitor"}
                }
            elif message_type == "payment_failed":
                embed = {
                    "title": "❌ Payment Failed",
                    "description": f"Payment attempt failed",
                    "color": color,
                    "fields": [
                        {"name": "User ID", "value": str(data.get('user_id')), "inline": True},
                        {"name": "Username", "value": data.get('username', 'N/A'), "inline": True},
                        {"name": "Plan", "value": data.get('plan_id', 'N/A'), "inline": True},
                        {"name": "Reason", "value": data.get('reason', 'Unknown'), "inline": False},
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "Winu Bot Payment Monitor"}
                }
            else:
                # Generic message
                embed = {
                    "title": f"📊 Payment Update",
                    "description": json.dumps(data, indent=2),
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            
            payload = {
                "embeds": [embed]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
                    if response.status == 204:
                        console.print(f"✅ [green]Discord notification sent ({message_type})[/green]")
                    else:
                        error_text = await response.text()
                        console.print(f"⚠️  [yellow]Discord notification failed: {response.status} - {error_text}[/yellow]")
        except Exception as e:
            console.print(f"❌ [red]Error sending Discord notification: {e}[/red]")
    
    async def get_recent_payments(self, minutes: int = 30) -> List[Dict]:
        """Get recent payment transactions."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id,
                        user_id,
                        plan_id,
                        amount_usd,
                        amount_usdt,
                        status,
                        payment_method,
                        transaction_id,
                        payment_data,
                        created_at,
                        completed_at,
                        updated_at
                    FROM payment_transactions
                    WHERE created_at >= $1
                    ORDER BY created_at DESC
                    LIMIT 50
                """, cutoff_time)
                
                return [dict(row) for row in rows]
        except Exception as e:
            console.print(f"❌ [red]Error fetching payments: {e}[/red]")
            return []
    
    async def get_user_subscription_status(self, user_id: int) -> Dict:
        """Get user's current subscription status."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT 
                        id,
                        username,
                        email,
                        subscription_status,
                        subscription_tier,
                        plan_id,
                        last_payment_date,
                        payment_due_date,
                        subscription_renewal_date,
                        access_revoked_at,
                        created_at
                    FROM users
                    WHERE id = $1
                """, user_id)
                
                if row:
                    return dict(row)
                return {}
        except Exception as e:
            console.print(f"❌ [red]Error fetching user {user_id}: {e}[/red]")
            return {}
    
    async def get_subscription_events(self, user_id: int, hours: int = 24) -> List[Dict]:
        """Get subscription events for user."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id,
                        user_id,
                        event_type,
                        event_data,
                        created_at
                    FROM subscription_events
                    WHERE user_id = $1 AND created_at >= $2
                    ORDER BY created_at DESC
                """, user_id, cutoff_time)
                
                return [dict(row) for row in rows]
        except Exception as e:
            console.print(f"❌ [red]Error fetching events for user {user_id}: {e}[/red]")
            return []
    
    async def check_payment_activation_gaps(self) -> List[Dict]:
        """
        Find payments that completed but subscription wasn't activated.
        This is the main issue: Payment succeeded but activation failed.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Find completed payments in last hour where user is still inactive
                rows = await conn.fetch("""
                    SELECT 
                        pt.id as payment_id,
                        pt.user_id,
                        pt.plan_id,
                        pt.status as payment_status,
                        pt.transaction_id,
                        pt.created_at as payment_created,
                        pt.completed_at,
                        pt.updated_at as payment_updated,
                        u.username,
                        u.email,
                        u.subscription_status,
                        u.subscription_tier,
                        u.last_payment_date
                    FROM payment_transactions pt
                    JOIN users u ON pt.user_id = u.id
                    WHERE pt.status IN ('completed', 'confirmed', 'finished', 'paid')
                    AND pt.created_at >= NOW() - INTERVAL '2 hours'
                    AND (u.subscription_status != 'active' OR u.subscription_tier != pt.plan_id)
                    ORDER BY pt.created_at DESC
                """)
                
                gaps = []
                for row in rows:
                    gap = dict(row)
                    # Check if activation event exists
                    events = await self.get_subscription_events(row['user_id'], hours=2)
                    activation_events = [e for e in events if e['event_type'] == 'activated']
                    gap['has_activation_event'] = len(activation_events) > 0
                    gaps.append(gap)
                
                return gaps
        except Exception as e:
            console.print(f"❌ [red]Error checking payment gaps: {e}[/red]")
            return []
    
    async def check_webhook_logs(self, minutes: int = 30):
        """Check if webhooks are being received (would need webhook logging table)."""
        # This would check a webhook_logs table if it exists
        # For now, we'll infer from payment status updates
        pass
    
    def display_payment_gaps(self, gaps: List[Dict]):
        """Display payment activation gaps in a table."""
        if not gaps:
            console.print("✅ [green]No payment activation gaps found![/green]")
            return
        
        table = Table(title="⚠️  PAYMENT ACTIVATION GAPS", box=box.ROUNDED, show_header=True, header_style="bold red")
        table.add_column("User ID", style="cyan")
        table.add_column("Username", style="yellow")
        table.add_column("Plan ID", style="magenta")
        table.add_column("Payment Status", style="green")
        table.add_column("User Status", style="red")
        table.add_column("Activation Event", style="blue")
        table.add_column("Payment Time", style="white")
        
        for gap in gaps:
            table.add_row(
                str(gap['user_id']),
                gap['username'] or "N/A",
                gap['plan_id'],
                gap['payment_status'],
                f"{gap['subscription_status']} / {gap['subscription_tier']}",
                "✅ Yes" if gap['has_activation_event'] else "❌ No",
                gap['payment_created'].strftime("%Y-%m-%d %H:%M:%S")
            )
        
        console.print(table)
        
        # Add alert
        alert_msg = f"🚨 ALERT: {len(gaps)} payment(s) completed but subscription not activated!"
        self.alert_logs.append({
            "time": datetime.utcnow().isoformat(),
            "message": alert_msg,
            "count": len(gaps)
        })
    
    async def notify_payment_gaps(self, gaps: List[Dict]):
        """Send Discord notifications for payment gaps."""
        for gap in gaps:
            payment_id = gap.get('payment_id')
            
            # Only notify once per payment
            if payment_id in self.notified_payment_ids:
                continue
            
            # Send Discord notification
            await self.send_discord_notification("payment_gap", {
                "user_id": gap['user_id'],
                "username": gap.get('username', 'N/A'),
                "email": gap.get('email', 'N/A'),
                "plan_id": gap['plan_id'],
                "payment_status": gap['payment_status'],
                "subscription_status": gap['subscription_status'],
                "subscription_tier": gap.get('subscription_tier', 'N/A'),
                "transaction_id": gap.get('transaction_id', 'N/A'),
                "payment_created": gap['payment_created'].strftime("%Y-%m-%d %H:%M:%S") if gap.get('payment_created') else 'N/A'
            })
            
            # Mark as notified
            self.notified_payment_ids.add(payment_id)
    
    def display_recent_payments(self, payments: List[Dict]):
        """Display recent payments."""
        table = Table(title="💰 Recent Payments (Last 30 min)", box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim")
        table.add_column("User ID", style="cyan")
        table.add_column("Plan", style="magenta")
        table.add_column("Amount", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Method", style="blue")
        table.add_column("Time", style="white")
        
        for payment in payments[:10]:  # Show last 10
            amount_str = f"${payment['amount_usd']:.2f}" if payment.get('amount_usd') else f"{payment.get('amount_usdt', 0):.2f} USDT"
            table.add_row(
                str(payment['id']),
                str(payment['user_id']),
                payment['plan_id'],
                amount_str,
                payment['status'],
                payment['payment_method'],
                payment['created_at'].strftime("%H:%M:%S")
            )
        
        console.print(table)
    
    async def display_user_detail(self, user_id: int):
        """Display detailed user subscription info."""
        user = await self.get_user_subscription_status(user_id)
        if not user:
            console.print(f"[red]User {user_id} not found[/red]")
            return
        
        events = await self.get_subscription_events(user_id, hours=24)
        
        # User info panel
        user_info = f"""
[cyan]User ID:[/cyan] {user['id']}
[cyan]Username:[/cyan] {user['username']}
[cyan]Email:[/cyan] {user['email']}
[cyan]Status:[/cyan] [{'green' if user['subscription_status'] == 'active' else 'red'}]{user['subscription_status']}[/]
[cyan]Tier:[/cyan] {user['subscription_tier']}
[cyan]Plan ID:[/cyan] {user['plan_id'] or 'N/A'}
[cyan]Last Payment:[/cyan] {user['last_payment_date'].strftime("%Y-%m-%d %H:%M:%S") if user['last_payment_date'] else 'Never'}
[cyan]Payment Due:[/cyan] {user['payment_due_date'].strftime("%Y-%m-%d") if user['payment_due_date'] else 'N/A'}
[cyan]Renewal:[/cyan] {user['subscription_renewal_date'].strftime("%Y-%m-%d") if user['subscription_renewal_date'] else 'N/A'}
[cyan]Access Revoked:[/cyan] {user['access_revoked_at'] or 'No'}
        """
        
        console.print(Panel(user_info, title=f"👤 User Details - {user['username']}", border_style="cyan"))
        
        # Events table
        if events:
            table = Table(title="📋 Recent Subscription Events", box=box.SIMPLE)
            table.add_column("Event Type", style="yellow")
            table.add_column("Time", style="white")
            table.add_column("Data", style="dim")
            
            for event in events:
                event_data_str = json.dumps(event['event_data'], indent=2) if event['event_data'] else "N/A"
                table.add_row(
                    event['event_type'],
                    event['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
                    event_data_str[:100] + "..." if len(event_data_str) > 100 else event_data_str
                )
            
            console.print(table)
        else:
            console.print("[yellow]No recent subscription events found[/yellow]")
    
    async def monitor_loop(self, interval: int = 10):
        """Main monitoring loop."""
        console.print(f"\n🔍 [bold blue]Starting Payment Activation Monitor[/bold blue]")
        console.print(f"Checking every {interval} seconds...\n")
        
        iteration = 0
        while True:
            try:
                iteration += 1
                console.print(f"\n[bold]{'='*80}[/bold]")
                console.print(f"[bold cyan]Check #{iteration} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}[/bold cyan]")
                console.print(f"[bold]{'='*80}[/bold]\n")
                
                # Check for payment activation gaps (CRITICAL)
                gaps = await self.check_payment_activation_gaps()
                self.display_payment_gaps(gaps)
                
                # Send Discord notifications for gaps
                if gaps:
                    await self.notify_payment_gaps(gaps)
                
                console.print()
                
                # Show recent payments
                payments = await self.get_recent_payments(minutes=30)
                if payments:
                    self.display_recent_payments(payments)
                else:
                    console.print("[yellow]No recent payments found[/yellow]")
                
                # If gaps found, show details for each affected user
                if gaps:
                    console.print("\n[bold red]⚠️  DETAILED USER INFO FOR AFFECTED USERS:[/bold red]\n")
                    for gap in gaps:
                        await self.display_user_detail(gap['user_id'])
                        console.print()
                
                # Display alert summary
                if self.alert_logs:
                    console.print(f"\n[bold red]🚨 ALERT LOG ({len(self.alert_logs)} alerts):[/bold red]")
                    for alert in self.alert_logs[-5:]:  # Show last 5
                        console.print(f"  {alert['time']} - {alert['message']}")
                
                console.print(f"\n[dim]Next check in {interval} seconds... (Press Ctrl+C to stop)[/dim]")
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Monitoring stopped by user[/yellow]")
                break
            except Exception as e:
                console.print(f"\n❌ [red]Error in monitoring loop: {e}[/red]")
                await asyncio.sleep(interval)
    
    async def run_single_check(self):
        """Run a single check without loop."""
        console.print(f"\n🔍 [bold blue]Running Single Payment Activation Check[/bold blue]\n")
        
        # Check for payment activation gaps
        gaps = await self.check_payment_activation_gaps()
        self.display_payment_gaps(gaps)
        
        # Send Discord notifications for gaps
        if gaps:
            await self.notify_payment_gaps(gaps)
        
        console.print()
        
        # Show recent payments
        payments = await self.get_recent_payments(minutes=30)
        if payments:
            self.display_recent_payments(payments)
        else:
            console.print("[yellow]No recent payments found[/yellow]")
        
        # If gaps found, show details
        if gaps:
            console.print("\n[bold red]⚠️  DETAILED USER INFO:[/bold red]\n")
            for gap in gaps:
                await self.display_user_detail(gap['user_id'])
                console.print()


async def main():
    """Main entry point."""
    import sys
    
    monitor = PaymentMonitor()
    
    if not await monitor.connect_db():
        console.print("[red]Failed to connect to database. Exiting.[/red]")
        return
    
    try:
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "check":
                # Single check
                await monitor.run_single_check()
            elif command == "watch":
                # Continuous monitoring
                interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
                await monitor.monitor_loop(interval=interval)
            elif command == "user":
                # Check specific user
                if len(sys.argv) > 2:
                    user_id = int(sys.argv[2])
                    await monitor.display_user_detail(user_id)
                else:
                    console.print("[red]Please provide user ID: python monitor_payment_activation.py user USER_ID[/red]")
            else:
                console.print(f"[red]Unknown command: {command}[/red]")
                print_usage()
        else:
            # Default: continuous monitoring
            await monitor.monitor_loop(interval=10)
    finally:
        await monitor.close_db()


def print_usage():
    """Print usage instructions."""
    console.print("""
[bold cyan]Payment Activation Monitor - Usage:[/bold cyan]

  [yellow]python monitor_payment_activation.py[/yellow]              - Start continuous monitoring (10s interval)
  [yellow]python monitor_payment_activation.py watch[/yellow]        - Start continuous monitoring (10s interval)
  [yellow]python monitor_payment_activation.py watch 30[/yellow]     - Start continuous monitoring (30s interval)
  [yellow]python monitor_payment_activation.py check[/yellow]        - Run single check
  [yellow]python monitor_payment_activation.py user USER_ID[/yellow] - Check specific user details

[bold red]What it monitors:[/bold red]
  • Payments completed but subscription NOT activated (PRIMARY ISSUE)
  • Recent payment transactions
  • User subscription status
  • Subscription events log
  • Payment-to-activation time gaps
  
[bold green]The monitor will alert you when:[/bold green]
  ✅ Payment is marked as completed/confirmed/finished
  ❌ But user subscription_status is still 'inactive'
  ❌ Or user subscription_tier doesn't match the paid plan
  ❌ Or no activation event was created
  
This helps identify the "payment invalid session" issue!
    """)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")

