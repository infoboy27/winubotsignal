#!/usr/bin/env python3
"""
Comprehensive System Audit
Performs detailed checks on all Winu Bot components and sends report to Discord.
"""

import sys
import os
import subprocess
import json
from datetime import datetime, timedelta

sys.path.append('/home/ubuntu/winubotsignal/packages')
from monitoring.error_monitor import error_monitor


def run_cmd(cmd, timeout=5):
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Exception: {str(e)}"


def check_docker_containers():
    """Check all Docker containers."""
    containers = {}
    
    container_names = [
        'winu-bot-signal-api',
        'winu-bot-signal-web',
        'winu-bot-signal-worker',
        'winu-bot-signal-celery-beat',
        'winu-bot-signal-trading-bot',
        'winu-bot-signal-postgres',
        'winu-bot-signal-redis',
        'winu-bot-signal-grafana',
        'winu-bot-signal-prometheus',
        'winu-bot-signal-traefik'
    ]
    
    for container in container_names:
        status = run_cmd(f"docker ps -a --filter name={container} --format '{{{{.Status}}}}'")
        containers[container] = {
            'status': status,
            'healthy': 'Up' in status
        }
    
    return containers


def check_database_stats():
    """Get database statistics."""
    stats = {}
    
    # Signal counts
    stats['total_signals'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c 'SELECT COUNT(*) FROM signals;'"
    )
    
    stats['signals_last_24h'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c \"SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '24 hours';\""
    )
    
    stats['signals_last_hour'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c \"SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '1 hour';\""
    )
    
    # User counts
    stats['total_users'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c 'SELECT COUNT(*) FROM users;'"
    )
    
    stats['active_subscriptions'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c \"SELECT COUNT(*) FROM users WHERE subscription_status = 'active';\""
    )
    
    # Recent signals by type
    stats['long_signals_24h'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c \"SELECT COUNT(*) FROM signals WHERE direction = 'LONG' AND created_at >= NOW() - INTERVAL '24 hours';\""
    )
    
    stats['short_signals_24h'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c \"SELECT COUNT(*) FROM signals WHERE direction = 'SHORT' AND created_at >= NOW() - INTERVAL '24 hours';\""
    )
    
    return stats


def check_worker_logs():
    """Check recent worker activity."""
    logs = {}
    
    # Check last scan_markets execution
    scan_logs = run_cmd("docker logs winu-bot-signal-worker 2>&1 | grep 'Market scan completed' | tail -5")
    logs['recent_scans'] = scan_logs
    
    # Check for recent errors
    error_logs = run_cmd("docker logs winu-bot-signal-worker 2>&1 | grep -i 'error\\|exception' | tail -10")
    logs['recent_errors'] = error_logs if error_logs else "No recent errors"
    
    # Check data ingestion
    ingestion_logs = run_cmd("docker logs winu-bot-signal-worker 2>&1 | grep 'Data ingestion completed' | tail -3")
    logs['recent_ingestion'] = ingestion_logs
    
    return logs


def check_api_health():
    """Check API health endpoint."""
    import requests
    try:
        response = requests.get('http://localhost:8001/health', timeout=10)
        return {
            'status_code': response.status_code,
            'healthy': response.status_code == 200,
            'data': response.json() if response.status_code == 200 else None
        }
    except Exception as e:
        return {'healthy': False, 'error': str(e)}


def check_celery_beat_schedule():
    """Check Celery Beat schedule."""
    schedule = run_cmd("docker logs winu-bot-signal-celery-beat 2>&1 | grep 'Scheduler: Sending due task' | tail -10")
    return schedule


def check_system_resources():
    """Check system resources."""
    resources = {}
    
    # Disk usage
    resources['disk_usage'] = run_cmd("df -h / | tail -1 | awk '{print $5}'")
    
    # Memory usage
    resources['memory_usage'] = run_cmd("free -h | grep Mem | awk '{print $3 \"/\" $2}'")
    
    # CPU load
    resources['cpu_load'] = run_cmd("uptime | awk -F'load average:' '{print $2}'")
    
    # Docker stats
    resources['docker_containers_running'] = run_cmd("docker ps -q | wc -l")
    
    return resources


def check_trading_bot_activity():
    """Check trading bot recent activity."""
    activity = {}
    
    # Recent signals executed
    activity['recent_executions'] = run_cmd(
        "docker logs winu-bot-signal-trading-bot 2>&1 | grep 'Selected best signal' | tail -5"
    )
    
    # Position status
    activity['positions'] = run_cmd(
        "docker exec winu-bot-signal-postgres psql -U winu -d winudb -t -c \"SELECT COUNT(*) FROM paper_positions WHERE status = 'open';\""
    )
    
    return activity


def perform_audit():
    """Perform comprehensive system audit."""
    print(f"\n{'='*70}")
    print(f"WINU BOT SYSTEM AUDIT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    audit_results = {
        'timestamp': datetime.now().isoformat(),
        'containers': check_docker_containers(),
        'database': check_database_stats(),
        'api': check_api_health(),
        'worker_logs': check_worker_logs(),
        'celery_schedule': check_celery_beat_schedule(),
        'system_resources': check_system_resources(),
        'trading_bot': check_trading_bot_activity()
    }
    
    # Print results
    print("📦 DOCKER CONTAINERS:")
    for container, info in audit_results['containers'].items():
        icon = "✅" if info['healthy'] else "❌"
        name = container.replace('winu-bot-signal-', '')
        print(f"  {icon} {name}: {info['status']}")
    
    print("\n📊 DATABASE STATISTICS:")
    for key, value in audit_results['database'].items():
        print(f"  • {key}: {value.strip()}")
    
    print("\n🌐 API HEALTH:")
    if audit_results['api']['healthy']:
        print(f"  ✅ Status: Healthy (Code: {audit_results['api']['status_code']})")
        if audit_results['api']['data']:
            services = audit_results['api']['data'].get('services', {})
            for svc, status in services.items():
                print(f"    • {svc}: {status}")
    else:
        print(f"  ❌ Status: Unhealthy - {audit_results['api'].get('error', 'Unknown')}")
    
    print("\n💻 SYSTEM RESOURCES:")
    for key, value in audit_results['system_resources'].items():
        print(f"  • {key}: {value}")
    
    print(f"\n{'='*70}\n")
    
    return audit_results


def send_audit_to_discord(audit_results):
    """Send audit report to Discord."""
    
    # Container status
    containers_healthy = sum(1 for c in audit_results['containers'].values() if c['healthy'])
    containers_total = len(audit_results['containers'])
    
    # Determine overall health
    all_healthy = containers_healthy == containers_total and audit_results['api']['healthy']
    
    # Build message
    title = "✅ System Audit - All Systems Operational" if all_healthy else "⚠️ System Audit - Issues Detected"
    severity = "SUCCESS" if all_healthy else "WARNING"
    color = 0x00FF00 if all_healthy else 0xFFCC00
    
    # Container status field
    container_status = []
    for name, info in audit_results['containers'].items():
        icon = "✅" if info['healthy'] else "❌"
        short_name = name.replace('winu-bot-signal-', '')
        container_status.append(f"{icon} {short_name}")
    
    fields = [
        {
            "name": "📦 Containers Status",
            "value": f"**{containers_healthy}/{containers_total} Running**\n" + "\n".join(container_status[:5]),
            "inline": False
        },
        {
            "name": "📊 Signal Statistics (24h)",
            "value": f"**Total**: {audit_results['database']['signals_last_24h'].strip()}\n" +
                     f"**LONG**: {audit_results['database']['long_signals_24h'].strip()}\n" +
                     f"**SHORT**: {audit_results['database']['short_signals_24h'].strip()}",
            "inline": True
        },
        {
            "name": "👥 User Statistics",
            "value": f"**Total Users**: {audit_results['database']['total_users'].strip()}\n" +
                     f"**Active Subs**: {audit_results['database']['active_subscriptions'].strip()}",
            "inline": True
        },
        {
            "name": "💻 System Resources",
            "value": f"**Disk**: {audit_results['system_resources']['disk_usage']}\n" +
                     f"**Memory**: {audit_results['system_resources']['memory_usage']}\n" +
                     f"**Containers**: {audit_results['system_resources']['docker_containers_running']}",
            "inline": True
        }
    ]
    
    # Add API status
    if audit_results['api']['healthy']:
        fields.append({
            "name": "🌐 API Health",
            "value": "✅ **Operational**",
            "inline": True
        })
    else:
        fields.append({
            "name": "🌐 API Health",
            "value": f"❌ **Down**: {audit_results['api'].get('error', 'Unknown')}",
            "inline": True
        })
    
    # Add recent activity
    signals_1h = audit_results['database']['signals_last_hour'].strip()
    fields.append({
        "name": "⏰ Recent Activity (1h)",
        "value": f"**{signals_1h} signals generated**",
        "inline": True
    })
    
    # Add trading bot activity
    open_positions = audit_results['trading_bot']['positions'].strip()
    fields.append({
        "name": "📈 Trading Bot",
        "value": f"**Open Positions**: {open_positions}",
        "inline": True
    })
    
    # Send to Discord
    message = f"Comprehensive system audit completed at {datetime.now().strftime('%H:%M:%S UTC')}"
    
    error_monitor.send_custom_alert(
        title=title,
        message=message,
        severity=severity,
        fields=fields
    )
    
    # Send additional details if there are errors
    if audit_results['worker_logs']['recent_errors'] != "No recent errors":
        error_monitor.send_custom_alert(
            title="⚠️ Recent Worker Errors Detected",
            message="Recent errors found in worker logs:",
            severity="WARNING",
            fields=[{
                "name": "Error Log Sample",
                "value": audit_results['worker_logs']['recent_errors'][:1000],
                "inline": False
            }]
        )


if __name__ == "__main__":
    try:
        audit_results = perform_audit()
        send_audit_to_discord(audit_results)
        print("✅ Audit complete and sent to Discord!")
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        error_monitor.send_error_alert(
            error=e,
            context="System Audit Failure",
            severity="ERROR"
        )
        sys.exit(1)





