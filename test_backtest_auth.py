#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - Test Backtest with Authentication
======================================================

This script tests the backtest API with proper authentication.
"""

import requests
import json
from datetime import datetime, timedelta

def test_backtest_with_auth():
    """Test the backtest API with authentication."""
    
    print("🧪 Testing Backtest API with Authentication...")
    
    # First, let's try to get a token by logging in
    login_data = {
        "username": "admin",
        "password": "winu2024!"
    }
    
    try:
        # Try to login to get a token
        login_response = requests.post(
            "http://localhost:3000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📡 Login Status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get('access_token', '')
            print(f"✅ Login successful, token: {token[:20]}...")
            
            # Now test the backtest API with the token
            backtest_request = {
                "symbol": "BTC/USDT",
                "startDate": "2025-08-01",
                "endDate": "2025-09-26",
                "initialBalance": 10000,
                "riskPercent": 2.0,
                "maxPositions": 5,
                "minScore": 0.7
            }
            
            backtest_response = requests.post(
                "http://localhost:3000/api/backtest/run",
                json=backtest_request,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                },
                timeout=60
            )
            
            print(f"📡 Backtest Status: {backtest_response.status_code}")
            
            if backtest_response.status_code == 200:
                result = backtest_response.json()
                print("✅ Backtest API working with authentication!")
                print(f"📈 Results: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ Backtest API Error: {backtest_response.text}")
        else:
            print(f"❌ Login failed: {login_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_backtest_with_auth()

