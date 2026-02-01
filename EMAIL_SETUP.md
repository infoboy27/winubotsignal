# 📧 Email Service Setup Guide

## Current Setup
The email verification system is already implemented and ready to use! You can choose between different email services:

## 🥇 Option 1: SendGrid (Recommended)

### Setup Steps:
1. **Sign up for SendGrid**: Go to [sendgrid.com](https://sendgrid.com)
2. **Get API Key**: 
   - Go to Settings → API Keys
   - Create a new API key with "Mail Send" permissions
   - Copy the API key

3. **Add to Environment Variables**:
   ```bash
   # Add to your production.env file
   SENDGRID_API_KEY=your_sendgrid_api_key_here
   EMAIL_SENDER=noreply@winu.app
   ```

4. **Verify Sender Email**: 
   - In SendGrid dashboard, go to Settings → Sender Authentication
   - Verify your domain or single sender email

### Benefits:
- ✅ 100 emails/day free tier
- ✅ High deliverability
- ✅ Professional email templates
- ✅ Analytics and tracking

---

## 🥈 Option 2: Gmail SMTP (Current)

### Setup Steps:
1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"

3. **Add to Environment Variables**:
   ```bash
   # Add to your production.env file
   EMAIL_SENDER=your-gmail@gmail.com
   EMAIL_PASSWORD=your_app_password_here
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_SMTP_PORT=587
   ```

### Benefits:
- ✅ Free
- ✅ Easy setup
- ❌ Limited to 500 emails/day
- ❌ Not ideal for production

---

## 🥉 Option 3: Mailgun

### Setup Steps:
1. **Sign up for Mailgun**: Go to [mailgun.com](https://mailgun.com)
2. **Get API Key**: From dashboard
3. **Add to Environment Variables**:
   ```bash
   MAILGUN_API_KEY=your_mailgun_api_key_here
   MAILGUN_DOMAIN=your_mailgun_domain_here
   EMAIL_SENDER=noreply@winu.app
   ```

---

## 🚀 Quick Start (Recommended: SendGrid)

1. **Sign up for SendGrid** (free tier: 100 emails/day)
2. **Get your API key** from SendGrid dashboard
3. **Add to your environment**:
   ```bash
   echo "SENDGRID_API_KEY=your_api_key_here" >> production.env
   echo "EMAIL_SENDER=noreply@winu.app" >> production.env
   ```
4. **Restart the API service**:
   ```bash
   docker-compose -f docker-compose.yaml restart api
   ```

## 📧 Email Template Features

The verification emails include:
- ✅ Beautiful HTML design
- ✅ Winu branding
- ✅ 6-digit verification code
- ✅ 15-minute expiration
- ✅ Mobile-friendly design

## 🔧 Testing

To test email sending:
1. Register a new user at https://winu.app/register
2. Check the email inbox
3. Use the verification code to complete registration

## 📊 Monitoring

Check email logs in the API container:
```bash
docker-compose -f docker-compose.yaml logs api | grep "email"
```

---

**Ready to go!** 🎉 Just add your SendGrid API key and you're all set!
