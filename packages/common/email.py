"""Email verification system."""

import smtplib
import secrets
import string
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .config import get_settings
from .database import User, EmailVerification
from .logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmailService:
    """Email service for sending verification emails."""
    
    def __init__(self):
        # Use SendGrid SMTP instead of Gmail
        self.smtp_server = "smtp.sendgrid.net"
        self.smtp_port = 587  # Use TLS port
        self.sender_email = "noreply@winu.app"
        import os
        self.sender_password = os.getenv('SENDGRID_API_KEY', '')
        
        # Try to get SendGrid API key from environment or settings
        import os
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY') or getattr(settings.email, 'sendgrid_api_key', None)
        self.use_sendgrid = True  # Always use SendGrid SMTP now
        logger.info(f"Email service initialized: use_sendgrid={self.use_sendgrid}, smtp_server={self.smtp_server}")
    
    def generate_verification_code(self, length: int = 6) -> str:
        """Generate a random verification code."""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    async def send_verification_email(self, email: str, code: str, username: str) -> bool:
        """Send verification email to user."""
        # Try SendGrid API first, fallback to SMTP
        if self.sendgrid_api_key:
            return await self._send_via_sendgrid(email, code, username)
        else:
            return await self._send_via_smtp(email, code, username)
    
    async def _send_via_sendgrid(self, email: str, code: str, username: str) -> bool:
        """Send email via SendGrid API."""
        try:
            # Create HTML body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Winu Bot Signal</h1>
                    <p style="color: white; margin: 10px 0 0 0;">AI Crypto Trading Signals</p>
                </div>
                
                <div style="padding: 30px; background: #f8f9fa;">
                    <h2 style="color: #333; margin-top: 0;">Welcome {username}!</h2>
                    <p style="color: #666; line-height: 1.6;">
                        Thank you for registering with Winu Bot Signal. To complete your registration, 
                        please verify your email address using the code below:
                    </p>
                    
                    <div style="background: #fff; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                        <h3 style="color: #667eea; margin: 0; font-size: 32px; letter-spacing: 3px;">{code}</h3>
                        <p style="color: #666; margin: 10px 0 0 0; font-size: 14px;">Verification Code</p>
                    </div>
                    
                    <p style="color: #666; line-height: 1.6;">
                        This code will expire in 15 minutes. If you didn't request this verification, 
                        please ignore this email.
                    </p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p style="color: #999; font-size: 12px; margin: 0;">
                            © 2025 Winu Bot Signal. All rights reserved.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # SendGrid API payload
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": email}],
                        "subject": "Winu Bot Signal - Email Verification"
                    }
                ],
                "from": {"email": self.sender_email, "name": "Winu Bot Signal"},
                "content": [
                    {
                        "type": "text/html",
                        "value": html_body
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 202:
                        logger.info(f"Verification email sent via SendGrid to {email}")
                        return True
                    else:
                        logger.error(f"SendGrid API error: {response.status}")
                        return False
            
        except Exception as e:
            logger.error(f"Failed to send verification email via SendGrid to {email}: {e}")
            return False
    
    async def _send_via_smtp(self, email: str, code: str, username: str) -> bool:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = email
            msg['Subject'] = "Winu Bot Signal - Email Verification"
            
            # Create HTML body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Winu Bot Signal</h1>
                    <p style="color: white; margin: 10px 0 0 0;">AI Crypto Trading Signals</p>
                </div>
                
                <div style="padding: 30px; background: #f8f9fa;">
                    <h2 style="color: #333; margin-top: 0;">Welcome {username}!</h2>
                    <p style="color: #666; line-height: 1.6;">
                        Thank you for registering with Winu Bot Signal. To complete your registration, 
                        please verify your email address using the code below:
                    </p>
                    
                    <div style="background: #fff; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                        <h3 style="color: #667eea; margin: 0; font-size: 32px; letter-spacing: 3px;">{code}</h3>
                        <p style="color: #666; margin: 10px 0 0 0; font-size: 14px;">Verification Code</p>
                    </div>
                    
                    <p style="color: #666; line-height: 1.6;">
                        This code will expire in 15 minutes. If you didn't request this verification, 
                        please ignore this email.
                    </p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p style="color: #999; font-size: 12px; margin: 0;">
                            © 2025 Winu Bot Signal. All rights reserved.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Verification email sent via SMTP to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email via SMTP to {email}: {e}")
            return False
    
    async def send_welcome_email(self, email: str, username: str) -> bool:
        """Send welcome email to user after successful verification."""
        # Try SendGrid API first, fallback to SMTP
        if self.sendgrid_api_key:
            return await self._send_welcome_via_sendgrid(email, username)
        else:
            return await self._send_welcome_via_smtp(email, username)
    
    async def _send_welcome_via_sendgrid(self, email: str, username: str) -> bool:
        """Send welcome email via SendGrid API."""
        try:
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
                                        <h2 style="color: #1a1a1a; margin: 0 0 20px 0; font-size: 28px; font-weight: 600;">Welcome to Winu, {username}! 🎉</h2>
                                        
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
                        "to": [{"email": email}],
                        "subject": "🎉 Welcome to Winu Bot Signal - Let's Start Trading!"
                    }
                ],
                "from": {"email": self.sender_email, "name": "Winu Bot Signal"},
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
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 202:
                        logger.info(f"Welcome email sent via SendGrid to {email}")
                        return True
                    else:
                        logger.error(f"SendGrid API error: {response.status}")
                        return False
            
        except Exception as e:
            logger.error(f"Failed to send welcome email via SendGrid to {email}: {e}")
            return False
    
    async def _send_welcome_via_smtp(self, email: str, username: str) -> bool:
        """Send welcome email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = email
            msg['Subject'] = "🎉 Welcome to Winu Bot Signal - Let's Start Trading!"
            
            # Create beautiful HTML body (same as SendGrid version)
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
                                        <h2 style="color: #1a1a1a; margin: 0 0 20px 0; font-size: 28px; font-weight: 600;">Welcome to Winu, {username}! 🎉</h2>
                                        
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
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Welcome email sent via SMTP to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email via SMTP to {email}: {e}")
            return False


async def create_email_verification(db: AsyncSession, user_id: int, email: str) -> str:
    """Create email verification record and send email."""
    email_service = EmailService()
    code = email_service.generate_verification_code()
    
    # Create verification record
    verification = EmailVerification(
        user_id=user_id,
        email=email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        is_used=False
    )
    
    db.add(verification)
    await db.commit()
    await db.refresh(verification)
    
    # Send email
    user = await db.get(User, user_id)
    await email_service.send_verification_email(email, code, user.username)
    
    return code


async def verify_email_code(db: AsyncSession, email: str, code: str) -> bool:
    """Verify email code and mark user as verified."""
    # Find verification record
    result = await db.execute(
        select(EmailVerification)
        .where(
            and_(
                EmailVerification.email == email,
                EmailVerification.code == code,
                EmailVerification.is_used == False,
                EmailVerification.expires_at > datetime.utcnow()
            )
        )
    )
    
    verification = result.scalar_one_or_none()
    if not verification:
        return False
    
    # Mark verification as used
    verification.is_used = True
    verification.verified_at = datetime.utcnow()
    
    # Mark user as verified
    user = await db.get(User, verification.user_id)
    user.email_verified = True
    
    db.add(verification)
    db.add(user)
    await db.commit()
    
    logger.info(f"Email verified for user {user.username}")
    return True


async def has_used_free_trial(db: AsyncSession, email: str) -> bool:
    """Check if user has already used free trial."""
    result = await db.execute(
        select(User)
        .where(
            and_(
                User.email == email,
                User.subscription_status == "inactive",
                User.plan_id == "free_trial"
            )
        )
    )
    
    user = result.scalar_one_or_none()
    return user is not None


async def send_welcome_email_to_user(db: AsyncSession, user_id: int, email: str) -> bool:
    """Send welcome email to user after successful email verification."""
    email_service = EmailService()
    user = await db.get(User, user_id)
    return await email_service.send_welcome_email(email, user.username)
