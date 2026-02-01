# Bot Dashboard Login Credentials

## Test Account

**URL**: https://bot.winu.app/login

**Username**: `admin`  
**Password**: `admin123`

## What You'll See After Login

Once logged in, you'll see the real trading metrics:

- **Total PnL**: $0.24 (from active DOT/USDT position)
- **Win Rate**: Currently 0% (position not yet closed)
- **Total Trades**: 1 active position
- **Balance**: $95.58 USDT (real Binance balance)
- **Bot Status**: Running (5+ hours uptime)

## API Endpoints (Require Authentication)

- `GET /api/status` - Bot status and trading metrics
- `GET /api/balance` - Account balance information
- `POST /api/start` - Start the trading bot
- `POST /api/stop` - Stop the trading bot
- `POST /api/emergency-stop` - Emergency stop

## Session Management

- Sessions last 24 hours
- Cookies are HttpOnly and Secure
- Logout available at `/logout`

## Troubleshooting

If you get 400 Bad Request errors:
1. Make sure you're using the correct credentials
2. Check that the user exists in the database
3. Verify password hashing is working (Argon2)

## Creating Additional Users

To create more users, use the database directly or create a user management script.
