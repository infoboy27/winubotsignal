#!/usr/bin/env python3
"""
Send verification email manually using SendGrid
"""

import asyncio
import aiohttp
import json

async def send_verification_email():
    """Send verification email to jmariacastro@gmail.com using SendGrid."""
    
    import os
    api_key = os.getenv('SENDGRID_API_KEY', '')
    email = "jmariacastro@gmail.com"
    username = "infoboy2708"
    code = "836998"  # The code from the database
    
    # Email payload
    payload = {
        "personalizations": [
            {
                "to": [{"email": email}],
                "subject": "Winu Bot Signal - Email Verification"
            }
        ],
        "from": {"email": "noreply@winu.app", "name": "Winu Bot Signal"},
        "content": [
            {
                "type": "text/html",
                "value": f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Winu Bot Signal - Email Verification</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                        .verification-code {{ background: #667eea; color: white; font-size: 24px; font-weight: bold; padding: 15px; text-align: center; border-radius: 5px; margin: 20px 0; }}
                        .button {{ background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🚀 Winu Bot Signal</h1>
                            <p>Welcome to the future of AI trading!</p>
                        </div>
                        <div class="content">
                            <h2>Email Verification Required</h2>
                            <p>Hello <strong>{username}</strong>,</p>
                            <p>Thank you for registering with Winu Bot Signal! To complete your registration and access our AI-powered trading signals, please verify your email address.</p>
                            
                            <div class="verification-code">
                                Your verification code: <strong>{code}</strong>
                            </div>
                            
                            <p>Please enter this code in the verification form to activate your account.</p>
                            
                            <p><strong>What's next?</strong></p>
                            <ul>
                                <li>✅ Verify your email with the code above</li>
                                <li>🎯 Choose your plan (Free Trial, Professional, or VIP Elite)</li>
                                <li>📈 Access real-time AI trading signals</li>
                                <li>💬 Join our exclusive Telegram group</li>
                            </ul>
                            
                            <p>This verification code will expire in 15 minutes.</p>
                            
                            <p>If you didn't create an account with Winu Bot Signal, please ignore this email.</p>
                            
                            <p>Best regards,<br><strong>Winu Bot Signal Team</strong></p>
                        </div>
                        <div class="footer">
                            <p>© 2025 Winu Bot Signal. All rights reserved.</p>
                            <p>This is an automated message, please do not reply.</p>
                        </div>
                    </div>
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
                print(f"📧 Sending verification email to {email}")
                print(f"Status Code: {response.status}")
                
                if response.status == 202:
                    print("✅ Verification email sent successfully!")
                    print(f"📧 Email: {email}")
                    print(f"🔑 Verification Code: {code}")
                    print(f"👤 Username: {username}")
                    return True
                else:
                    response_text = await response.text()
                    print(f"❌ Failed to send email: {response_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(send_verification_email())
