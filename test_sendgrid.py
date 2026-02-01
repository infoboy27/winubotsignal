#!/usr/bin/env python3
"""
Test SendGrid email functionality
"""

import asyncio
import aiohttp
import json

async def test_sendgrid():
    """Test SendGrid API directly."""
    
    import os
    api_key = os.getenv('SENDGRID_API_KEY', '')
    
    # Test email payload
    payload = {
        "personalizations": [
            {
                "to": [{"email": "test@example.com"}],
                "subject": "Winu Bot Signal - Test Email"
            }
        ],
        "from": {"email": "noreply@winu.app", "name": "Winu Bot Signal"},
        "content": [
            {
                "type": "text/html",
                "value": """
                <html>
                <body>
                    <h2>🎉 Winu Bot Signal - Test Email</h2>
                    <p>This is a test email to verify SendGrid is working!</p>
                    <p>Verification Code: <strong>123456</strong></p>
                    <p>Best regards,<br>Winu Bot Signal Team</p>
                </body>
                </html>
                """
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers
            ) as response:
                print(f"Status Code: {response.status}")
                print(f"Response: {await response.text()}")
                
                if response.status == 202:
                    print("✅ SendGrid test successful!")
                    return True
                else:
                    print("❌ SendGrid test failed!")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing SendGrid: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_sendgrid())
