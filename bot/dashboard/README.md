# Winu Bot Dashboard

A modern, responsive dashboard for monitoring the Winu trading bot with real-time metrics and controls.

## Features

- **Real-time Trading Metrics**: Live PnL, win rate, total trades, and balance
- **Position Management**: View and close active trading positions
- **Bot Controls**: Start, stop, and emergency stop the trading bot
- **Responsive Design**: Works on desktop and mobile devices
- **Production-Ready CSS**: Optimized Tailwind CSS build

## CSS Build Process

This dashboard uses a production-ready Tailwind CSS setup instead of the CDN version.

### Building CSS

```bash
# Development (with watch mode)
npm run build-css

# Production (minified)
npm run build-css-prod

# Or use the build script
./build.sh
```

### File Structure

```
dashboard/
├── app.py              # FastAPI application
├── static/
│   └── styles.css      # Generated Tailwind CSS
├── input.css           # Tailwind source file
├── tailwind.config.js  # Tailwind configuration
├── package.json        # Node.js dependencies
├── build.sh           # Build script
└── README.md          # This file
```

## Docker Integration

The Dockerfile automatically builds the CSS during container creation:

1. Installs Node.js
2. Runs `npm install` to get Tailwind CSS
3. Builds the production CSS with `npm run build-css-prod`

## Benefits of Local CSS vs CDN

✅ **Performance**: Optimized for your specific classes only  
✅ **Reliability**: No external dependencies  
✅ **Customization**: Full control over Tailwind configuration  
✅ **Security**: No external script injection  
✅ **Offline**: Works without internet connection  
✅ **Caching**: Better browser caching control  

## Development

To modify styles:

1. Edit `input.css` to add custom styles
2. Update `tailwind.config.js` for configuration changes
3. Run `./build.sh` to rebuild
4. Restart the dashboard container

## Production Deployment

The CSS is automatically built during Docker image creation, so no additional steps are needed for deployment.
