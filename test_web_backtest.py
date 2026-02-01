#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - Test Web Backtest
=====================================

This script tests the web backtest functionality.
"""

import requests
import json
from datetime import datetime, timedelta

def test_web_backtest():
    """Test the web backtest functionality."""
    
    # Test the web interface
    print("🧪 Testing Web Backtest Interface...")
    
    try:
        # Test the backtest page
        response = requests.get("http://localhost:3000/backtest", timeout=10)
        print(f"📡 Web Interface Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Web interface is accessible")
            
            # Check if the page contains backtest elements
            if "backtest" in response.text.lower():
                print("✅ Backtest page is loading")
            else:
                print("❌ Backtest page content not found")
        else:
            print(f"❌ Web interface error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to web interface")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_api_through_web():
    """Test API through web proxy."""
    
    print("\n🧪 Testing API through Web Proxy...")
    
    # Test the API endpoint through the web proxy
    backtest_request = {
        "symbol": "BTC/USDT",
        "startDate": "2025-08-01",
        "endDate": "2025-09-26",
        "initialBalance": 10000,
        "riskPercent": 2.0,
        "maxPositions": 5,
        "minScore": 0.7
    }
    
    try:
        # Test through the web proxy
        response = requests.post(
            "http://localhost:3000/api/backtest/run",
            json=backtest_request,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📡 API Proxy Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API working through web proxy!")
            print(f"📈 Results: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ API Proxy Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API proxy")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_web_backtest()
    test_api_through_web()

