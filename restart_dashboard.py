#!/usr/bin/env python3
"""
Restart the dashboard service
"""

import subprocess
import time
import os

def restart_dashboard():
    """Restart the dashboard service."""
    print("🔄 Restarting Dashboard Service...")
    
    # Change to bot directory
    os.chdir('/home/ubuntu/winubotsignal/bot')
    
    # Start dashboard in background
    try:
        subprocess.Popen([
            'python3', 'dashboard/app.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("✅ Dashboard started in background")
        print("🌐 Access at: http://localhost:8000")
        print("🔑 Login: admin / admin123")
        
        # Wait a moment and test
        time.sleep(3)
        
        import requests
        try:
            response = requests.get("http://localhost:8000", timeout=5)
            if response.status_code in [200, 302]:
                print("✅ Dashboard is responding")
            else:
                print(f"⚠️ Dashboard responded with status: {response.status_code}")
        except Exception as e:
            print(f"❌ Dashboard not responding: {e}")
            
    except Exception as e:
        print(f"❌ Failed to start dashboard: {e}")

if __name__ == "__main__":
    restart_dashboard()

