#!/usr/bin/env python3
"""
Simple test script for NOWPayments API
Tests basic API connectivity without complex dependencies
"""

import asyncio
import os
import httpx
import json


class SimpleNOWPaymentsTest:
    """Simple NOWPayments API tester."""
    
    def __init__(self):
        self.api_key = "NYA9SYH-VM14KRG-KGFX3CJ-FPA23VX"
        self.secret_key = "4e5228a4-c217-4e8a-b333-8091dff0c189"
        self.base_url = "https://api.nowpayments.io/v1"  # Production API
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def test_api_connection(self):
        """Test basic API connection."""
        print("🔗 Testing API connection...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/status",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("   ✅ API connection successful!")
                    print(f"   📊 API Status: {data}")
                    return True
                else:
                    print(f"   ❌ API connection failed: {response.status_code}")
                    print(f"   📝 Response: {response.text}")
                    return False
        except Exception as e:
            print(f"   ❌ API connection error: {e}")
            return False
    
    async def test_currencies(self):
        """Test currencies endpoint."""
        print("\n💰 Testing currencies endpoint...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/currencies",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    currencies = data.get("currencies", [])
                    print(f"   ✅ Currencies endpoint working!")
                    print(f"   📊 Available currencies: {len(currencies)}")
                    
                    # Show first 10 currencies
                    print("   🪙 Sample currencies:")
                    for i, currency in enumerate(currencies[:10], 1):
                        print(f"      {i:2d}. {currency}")
                    
                    return True
                else:
                    print(f"   ❌ Currencies endpoint failed: {response.status_code}")
                    print(f"   📝 Response: {response.text}")
                    return False
        except Exception as e:
            print(f"   ❌ Currencies endpoint error: {e}")
            return False
    
    async def test_minimum_amount(self):
        """Test minimum amount endpoint."""
        print("\n📏 Testing minimum amount endpoint...")
        try:
            params = {
                "currency_from": "usd",
                "currency_to": "btc"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/min-amount",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("   ✅ Minimum amount endpoint working!")
                    print(f"   💵 Min amount: {data}")
                    return True
                else:
                    print(f"   ❌ Minimum amount endpoint failed: {response.status_code}")
                    print(f"   📝 Response: {response.text}")
                    return False
        except Exception as e:
            print(f"   ❌ Minimum amount endpoint error: {e}")
            return False
    
    async def test_estimate(self):
        """Test price estimation endpoint."""
        print("\n📊 Testing price estimation endpoint...")
        try:
            params = {
                "amount": 50.0,
                "currency_from": "usd",
                "currency_to": "btc"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/estimate",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("   ✅ Price estimation endpoint working!")
                    print(f"   💰 $50 USD ≈ {data}")
                    return True
                else:
                    print(f"   ❌ Price estimation endpoint failed: {response.status_code}")
                    print(f"   📝 Response: {response.text}")
                    return False
        except Exception as e:
            print(f"   ❌ Price estimation endpoint error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests."""
        print("🚀 NOWPayments API Test Suite")
        print("=" * 50)
        print(f"🔑 API Key: {self.api_key[:8]}...{self.api_key[-8:]}")
        print(f"🌐 Base URL: {self.base_url}")
        print()
        
        tests = [
            self.test_api_connection,
            self.test_currencies,
            self.test_minimum_amount,
            self.test_estimate
        ]
        
        results = []
        for test in tests:
            result = await test()
            results.append(result)
        
        print("\n📋 Test Summary:")
        print("=" * 50)
        passed = sum(results)
        total = len(results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("\n🎉 All tests passed! NOWPayments API is working correctly.")
            print("\n📝 Next steps:")
            print("1. Set up webhook URL in NOWPayments dashboard")
            print("2. Configure IPN secret for webhook verification")
            print("3. Test payment creation in sandbox mode")
            print("4. Deploy to production when ready")
        else:
            print("\n⚠️  Some tests failed. Please check your API credentials and network connection.")
        
        return passed == total


async def main():
    """Main test function."""
    tester = SimpleNOWPaymentsTest()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
