#!/usr/bin/env python3
"""
Health Monitoring Script
Checks all Winu Bot services and sends Discord alerts if issues are detected.
Run this script periodically (e.g., every 5 minutes via cron).
"""

import sys
import os
import requests
import subprocess
from datetime import datetime, timedelta

# Add packages to path
sys.path.append('/home/ubuntu/winubotsignal/packages')
from monitoring.error_monitor import error_monitor


def check_api_health() -> dict:
    """Check if API is responding."""
    try:
        response = requests.get('http://localhost:8001/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {"healthy": True, "status": data.get('status'), "services": data.get('services')}
        return {"healthy": False, "error": f"Status code: {response.status_code}"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_docker_container(container_name: str) -> dict:
    """Check if a Docker container is running."""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Status}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            status = result.stdout.strip()
            is_up = 'Up' in status
            return {"healthy": is_up, "status": status}
        return {"healthy": False, "error": "Container not found"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_database() -> dict:
    """Check database connectivity."""
    try:
        result = subprocess.run(
            ['docker', 'exec', 'winu-bot-signal-postgres', 'pg_isready', '-U', 'winu'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return {"healthy": True, "status": "accepting connections"}
        return {"healthy": False, "error": result.stderr}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_recent_signals() -> dict:
    """Check if signals have been generated recently."""
    try:
        result = subprocess.run(
            [
                'docker', 'exec', 'winu-bot-signal-postgres',
                'psql', '-U', 'winu', '-d', 'winudb', '-t', '-c',
                "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '2 hours';"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            count = int(result.stdout.strip())
            return {"healthy": count > 0, "count": count, "message": f"{count} signals in last 2 hours"}
        return {"healthy": False, "error": result.stderr}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def main():
    """Run health checks and send alerts if needed."""
    print(f"\n{'='*60}")
    print(f"Winu Bot Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    services = {
        "API": check_api_health(),
        "Web": check_docker_container("winu-bot-signal-web"),
        "Worker": check_docker_container("winu-bot-signal-worker"),
        "Trading Bot": check_docker_container("winu-bot-signal-trading-bot"),
        "Database": check_database(),
        "Redis": check_docker_container("winu-bot-signal-redis"),
        "Recent Signals": check_recent_signals()
    }
    
    # Print status
    all_healthy = True
    issues = []
    
    for service_name, status in services.items():
        icon = "✅" if status.get("healthy") else "❌"
        message = status.get("status") or status.get("message") or status.get("error", "Unknown")
        print(f"{icon} {service_name}: {message}")
        
        if not status.get("healthy"):
            all_healthy = False
            issues.append(f"**{service_name}**: {message}")
    
    print(f"\n{'='*60}\n")
    
    # Send Discord alert if there are issues
    if not all_healthy:
        error_monitor.send_custom_alert(
            title="⚠️ System Health Check - Issues Detected",
            message=f"**{len(issues)} issue(s) detected:**\n" + "\n".join(issues),
            severity="WARNING",
            fields=[
                {"name": service_name, "value": "✅ OK" if status["healthy"] else f"❌ {status.get('error', 'Error')}", "inline": True}
                for service_name, status in services.items()
            ]
        )
        print("❌ Issues detected - Discord alert sent")
    else:
        print("✅ All services healthy!")
    
    return 0 if all_healthy else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        error_monitor.send_error_alert(
            error=e,
            context="Health Monitor Script Failure",
            severity="CRITICAL"
        )
        sys.exit(1)





