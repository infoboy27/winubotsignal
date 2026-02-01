#!/usr/bin/env python3
"""
Test script to send welcome email to jonathanmaria@gmail.com
"""

import asyncio
import aiohttp
import os
import sys

# SendGrid API configuration
import os
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
SENDER_EMAIL = "noreply@winu.app"
TEST_EMAIL = "jonathanmaria@gmail.com"
TEST_USERNAME = "Jonathan"


async def send_welcome_email_test():
    """Send a test welcome email."""
    
    # Create beautiful HTML body with Telegram and Discord links
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Winu Bot Signal</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f5f5f5; padding: 20px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <!-- Header with gradient -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 32px; font-weight: 700;">🚀 Winu Bot Signal</h1>
                                <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">AI-Powered Trading Signals</p>
                            </td>
                        </tr>
                        
                        <!-- Main Content -->
                        <tr>
                            <td style="padding: 40px 30px; background-color: #ffffff;">
                                <h2 style="color: #1a1a1a; margin: 0 0 20px 0; font-size: 28px; font-weight: 600;">Welcome to Winu, {TEST_USERNAME}! 🎉</h2>
                                
                                <p style="color: #4a5568; line-height: 1.8; font-size: 16px; margin: 0 0 20px 0;">
                                    Congratulations! Your email has been successfully verified, and you're now part of the Winu Bot Signal community. 
                                    Get ready to experience professional-grade trading signals powered by advanced AI.
                                </p>
                                
                                <!-- Features Box -->
                                <div style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); border-left: 4px solid #667eea; padding: 20px; margin: 25px 0; border-radius: 8px;">
                                    <h3 style="color: #2d3748; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">✨ What's Next?</h3>
                                    <ul style="color: #4a5568; margin: 0; padding-left: 20px; line-height: 1.8;">
                                        <li style="margin-bottom: 10px;">📊 Access real-time AI trading signals</li>
                                        <li style="margin-bottom: 10px;">📈 Track your trading performance</li>
                                        <li style="margin-bottom: 10px;">🎯 Get instant alerts on your dashboard</li>
                                        <li style="margin-bottom: 10px;">💬 Join our exclusive community</li>
                                    </ul>
                                </div>
                                
                                <!-- CTA Button for Dashboard -->
                                <div style="text-align: center; margin: 30px 0;">
                                    <a href="https://winu.app/dashboard" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);">
                                        🎯 Go to Dashboard
                                    </a>
                                </div>
                                
                                <!-- Community Section -->
                                <div style="background: #ffffff; border: 2px solid #e2e8f0; padding: 25px; margin: 25px 0; border-radius: 10px;">
                                    <h3 style="color: #2d3748; margin: 0 0 15px 0; font-size: 20px; font-weight: 600; text-align: center;">🌟 Join Our Community</h3>
                                    
                                    <p style="color: #4a5568; line-height: 1.6; font-size: 15px; margin: 0 0 20px 0; text-align: center;">
                                        Connect with thousands of successful traders and get exclusive insights!
                                    </p>
                                    
                                    <!-- Telegram Button -->
                                    <div style="text-align: center; margin-bottom: 15px;">
                                        <a href="https://t.me/+gbq0Qc3z6whiZDAx" style="display: inline-block; background: linear-gradient(135deg, #0088cc 0%, #0066aa 100%); color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; box-shadow: 0 3px 10px rgba(0, 136, 204, 0.3);">
                                            📱 Join Telegram Channel
                                        </a>
                                    </div>
                                    
                                    <p style="color: #718096; font-size: 14px; text-align: center; margin: 15px 0;">
                                        Get instant notifications, share strategies, and connect with pro traders
                                    </p>
                                </div>
                                
                                <!-- Support Section -->
                                <div style="background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%); border-left: 4px solid #f56565; padding: 20px; margin: 25px 0; border-radius: 8px;">
                                    <h3 style="color: #742a2a; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">💬 Need Help?</h3>
                                    <p style="color: #742a2a; margin: 0 0 15px 0; line-height: 1.6; font-size: 15px;">
                                        Our support team is here to help you 24/7. If you have any questions or need assistance, reach out to us:
                                    </p>
                                    <div style="text-align: center;">
                                        <a href="https://discord.gg/5dZcxqsM" style="display: inline-block; background: linear-gradient(135deg, #7289da 0%, #5865f2 100%); color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; box-shadow: 0 3px 10px rgba(114, 137, 218, 0.3);">
                                            🎮 Contact us on Discord
                                        </a>
                                    </div>
                                </div>
                                
                                <!-- Tips Section -->
                                <div style="background: linear-gradient(135deg, #f0fff4 0%, #c6f6d5 100%); padding: 20px; margin: 25px 0; border-radius: 8px; border-left: 4px solid #48bb78;">
                                    <h3 style="color: #22543d; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">💡 Pro Tips</h3>
                                    <ul style="color: #22543d; margin: 0; padding-left: 20px; line-height: 1.8; font-size: 15px;">
                                        <li style="margin-bottom: 8px;">Start with demo trading to familiarize yourself with the platform</li>
                                        <li style="margin-bottom: 8px;">Set up your notification preferences in Settings</li>
                                        <li style="margin-bottom: 8px;">Review our risk management guidelines</li>
                                        <li>Join our Telegram channel for exclusive market insights</li>
                                    </ul>
                                </div>
                                
                                <p style="color: #4a5568; line-height: 1.6; font-size: 15px; margin: 25px 0 0 0;">
                                    Thank you for choosing Winu Bot Signal. We're excited to be part of your trading journey!
                                </p>
                                
                                <p style="color: #4a5568; line-height: 1.6; font-size: 15px; margin: 10px 0 0 0;">
                                    Happy Trading! 🚀<br>
                                    <strong style="color: #2d3748;">The Winu Bot Signal Team</strong>
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f7fafc; padding: 30px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="color: #718096; font-size: 14px; margin: 0 0 10px 0;">
                                    <strong>Winu Bot Signal</strong> - AI-Powered Trading Intelligence
                                </p>
                                <p style="color: #a0aec0; font-size: 13px; margin: 0 0 15px 0;">
                                    © 2025 Winu.app. All rights reserved.
                                </p>
                                <div style="margin: 15px 0;">
                                    <a href="https://winu.app" style="color: #667eea; text-decoration: none; margin: 0 10px; font-size: 13px;">Website</a>
                                    <a href="https://t.me/+gbq0Qc3z6whiZDAx" style="color: #667eea; text-decoration: none; margin: 0 10px; font-size: 13px;">Telegram</a>
                                    <a href="https://discord.gg/5dZcxqsM" style="color: #667eea; text-decoration: none; margin: 0 10px; font-size: 13px;">Discord</a>
                                </div>
                                <p style="color: #cbd5e0; font-size: 12px; margin: 15px 0 0 0; line-height: 1.5;">
                                    This is an automated message. Please do not reply to this email.<br>
                                    For support, contact us via Discord or Telegram.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # SendGrid API payload
    payload = {
        "personalizations": [
            {
                "to": [{"email": TEST_EMAIL}],
                "subject": "🎉 Welcome to Winu Bot Signal - Let's Start Trading!"
            }
        ],
        "from": {"email": SENDER_EMAIL, "name": "Winu Bot Signal"},
        "content": [
            {
                "type": "text/html",
                "value": html_body
            }
        ],
        "tracking_settings": {
            "click_tracking": {
                "enable": False,
                "enable_text": False
            },
            "open_tracking": {
                "enable": True
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        print("=" * 80)
        print("🚀 SENDING WELCOME EMAIL TEST")
        print("=" * 80)
        print(f"📧 To: {TEST_EMAIL}")
        print(f"👤 Username: {TEST_USERNAME}")
        print(f"📬 Sender: {SENDER_EMAIL}")
        print(f"🔗 Telegram: https://t.me/+gbq0Qc3z6whiZDAx")
        print(f"🎮 Discord: https://discord.gg/5dZcxqsM")
        print("=" * 80)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers
            ) as response:
                print(f"\n⏳ Sending email...")
                print(f"📊 Status Code: {response.status}")
                
                if response.status == 202:
                    print("\n" + "=" * 80)
                    print("✅ SUCCESS! WELCOME EMAIL SENT!")
                    print("=" * 80)
                    print(f"📧 Email sent to: {TEST_EMAIL}")
                    print(f"📬 Check your inbox!")
                    print("\n📝 Email Contents:")
                    print("   • Beautiful Winu.app branding with gradient header")
                    print("   • Telegram channel link for trading signals")
                    print("   • Discord support link")
                    print("   • Pro tips for getting started")
                    print("   • Dashboard access button")
                    print("=" * 80)
                    return True
                else:
                    response_text = await response.text()
                    print(f"\n❌ FAILED TO SEND EMAIL")
                    print(f"Status: {response.status}")
                    print(f"Response: {response_text}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🎯 WINU BOT SIGNAL - WELCOME EMAIL TEST")
    print("=" * 80)
    print("This will send a beautiful welcome email to jonathanmaria@gmail.com")
    print("with Telegram and Discord links included.")
    print("=" * 80 + "\n")
    
    result = asyncio.run(send_welcome_email_test())
    
    if result:
        print("\n🎉 Test completed successfully!")
        print("📧 Please check jonathanmaria@gmail.com for the welcome email.")
    else:
        print("\n❌ Test failed. Please check the error messages above.")
        sys.exit(1)

