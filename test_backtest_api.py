#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - Test Backtest API
======================================

This script tests the backtest API functionality.
"""

import requests
import json
from datetime import datetime, timedelta

def test_backtest_api():
    """Test the backtest API."""
    
    # Test data
    backtest_request = {
        "symbol": "BTC/USDT",
        "startDate": "2025-08-01",
        "endDate": "2025-09-26",
        "initialBalance": 10000,
        "riskPercent": 2.0,
        "maxPositions": 5,
        "minScore": 0.7
    }
    
    print("🧪 Testing Backtest API...")
    print(f"📊 Request: {json.dumps(backtest_request, indent=2)}")
    
    try:
        # Test the API endpoint
        response = requests.post(
            "http://localhost:8001/backtest/run",
            json=backtest_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Backtest API working!")
            print(f"📈 Results: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ API Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API - service may not be running")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_backtest_api()

