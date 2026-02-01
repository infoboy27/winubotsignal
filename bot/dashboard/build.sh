#!/bin/bash

# Build script for Winu Bot Dashboard
echo "🚀 Building Winu Bot Dashboard CSS..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build CSS for production
echo "🎨 Building Tailwind CSS..."
npm run build-css-prod

echo "✅ Build complete! CSS file generated at static/styles.css"
echo "📁 File size: $(du -h static/styles.css | cut -f1)"
