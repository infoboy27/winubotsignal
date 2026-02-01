#!/usr/bin/env python3
"""
Test NOWPayments Payment Flow
Simulates the complete payment process from creation to confirmation
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
API_BASE = "http://localhost:8001"
USER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbmZvYm95MjciLCJ1c2VyX2lkIjoxLCJleHAiOjE3NjA0NTYxMzF9.bOz28vYb_KiGH5msZIBFlOZPALfur8rmCeV8vBov-og"

async def test_payment_flow():
    """Test complete payment flow."""
    
    print("=" * 70)
    print("🧪 NOWPayments Payment Flow Test")
    print("=" * 70)
    print()
    
    async with httpx.AsyncClient() as client:
        
        # Step 1: Get subscription plans
        print("📋 Step 1: Fetching subscription plans...")
        response = await client.get(f"{API_BASE}/onboarding/plans")
        
        if response.status_code == 200:
            data = response.json()
            plans = data.get("plans", [])
            print(f"   ✅ Found {len(plans)} plans")
            for plan in plans:
                print(f"      - {plan['name']}: ${plan['price']}")
        else:
            print(f"   ❌ Failed to get plans: {response.status_code}")
            return False
        
        print()
        
        # Step 2: Create payment for professional plan
        print("💳 Step 2: Creating payment for Professional plan ($14.99)...")
        
        payment_data = {
            "plan_id": "professional",
            "payment_method": "nowpayments",
            "pay_currency": "btc"
        }
        
        headers = {
            "Authorization": f"Bearer {USER_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = await client.post(
            f"{API_BASE}/api/crypto-subscriptions/create-payment",
            json=payment_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Payment created successfully!")
            print(f"   📝 Response:")
            print(json.dumps(result, indent=6))
            
            payment_details = result.get("payment_data", {})
            
            if payment_details.get("invoice_url"):
                print(f"\n   🌐 Invoice URL: {payment_details['invoice_url']}")
                print(f"   💰 Amount: ${payment_details.get('amount')} USD")
                print(f"   🆔 Invoice ID: {payment_details.get('invoice_id')}")
                print(f"   📦 Order ID: {payment_details.get('order_id')}")
                
                # Save details for webhook testing
                test_data = {
                    "invoice_id": payment_details.get("invoice_id"),
                    "order_id": payment_details.get("order_id"),
                    "amount": payment_details.get("amount"),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                with open("/tmp/nowpayments_test_payment.json", "w") as f:
                    json.dump(test_data, f, indent=2)
                
                print(f"\n   💾 Payment details saved to: /tmp/nowpayments_test_payment.json")
                
                return test_data
            elif payment_details.get("pay_address"):
                print(f"\n   📍 Pay Address: {payment_details['pay_address']}")
                print(f"   💰 Amount: {payment_details.get('amount')} {payment_details.get('currency')}")
                print(f"   🆔 Payment ID: {payment_details.get('payment_id')}")
                return payment_details
            
        else:
            print(f"   ❌ Payment creation failed: {response.status_code}")
            print(f"   📝 Response: {response.text}")
            return None
        
        print()

async def simulate_webhook_payment(payment_data):
    """Simulate a successful payment webhook."""
    
    print("\n" + "=" * 70)
    print("🔔 Simulating Payment Webhook (Payment Confirmation)")
    print("=" * 70)
    print()
    
    webhook_payload = {
        "invoice_id": payment_data.get("invoice_id"),
        "invoice_status": "paid",
        "order_id": payment_data.get("order_id"),
        "payment_id": payment_data.get("invoice_id"),
        "payment_status": "finished",
        "pay_address": "test_address",
        "price_amount": payment_data.get("amount"),
        "price_currency": "usd",
        "pay_amount": 0.00015,
        "pay_currency": "btc",
        "actually_paid": 0.00015,
        "purchase_id": payment_data.get("order_id")
    }
    
    print("📤 Webhook payload:")
    print(json.dumps(webhook_payload, indent=3))
    print()
    
    # Note: In sandbox mode, you can manually trigger this webhook
    print("⚠️  To complete the test:")
    print("   1. In NOWPayments sandbox dashboard, mark the invoice as 'paid'")
    print("   2. Or manually trigger the webhook by sending the payload above to:")
    print("      POST http://localhost:8001/api/crypto-subscriptions/webhooks/nowpayments")
    print()
    
    # For testing, we can directly call the webhook
    try:
        async with httpx.AsyncClient() as client:
            # Generate a test signature (in sandbox mode signature verification is usually skipped)
            headers = {
                "Content-Type": "application/json",
                "x-nowpayments-sig": "test_signature_for_sandbox"
            }
            
            print("🔔 Sending test webhook...")
            response = await client.post(
                f"{API_BASE}/api/crypto-subscriptions/webhooks/nowpayments",
                json=webhook_payload,
                headers=headers
            )
            
            print(f"   📬 Webhook response: {response.status_code}")
            print(f"   📝 Response: {response.text}")
            
    except Exception as e:
        print(f"   ⚠️  Webhook test note: {e}")
        print("   💡 This is expected if signature verification is enforced")

async def main():
    """Run the complete test suite."""
    
    print("\n🎯 Testing NOWPayments Integration")
    print()
    print("⚙️  Configuration:")
    print("   - API Base: http://localhost:8001")
    print("   - Mode: Sandbox (Testing)")
    print()
    
    # Run payment flow test
    payment_data = await test_payment_flow()
    
    if payment_data:
        print("\n✅ Payment creation test passed!")
        
        # Optionally simulate webhook
        user_input = input("\n❓ Simulate payment webhook confirmation? (y/n): ")
        if user_input.lower() == 'y':
            await simulate_webhook_payment(payment_data)
    else:
        print("\n❌ Payment creation test failed!")
    
    print("\n" + "=" * 70)
    print("🏁 Test Complete")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())












