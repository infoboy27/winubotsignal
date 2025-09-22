#!/bin/bash

# Million Trader Setup Script
# This script sets up the development environment

set -e

echo "🚀 Setting up Million Trader..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys and configuration"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs data/postgres data/redis data/grafana data/prometheus

# Set permissions
echo "🔐 Setting permissions..."
chmod +x scripts/*.sh

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check API health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API service is healthy"
else
    echo "❌ API service is not responding"
fi

# Check Web dashboard
if curl -f http://localhost:3003 > /dev/null 2>&1; then
    echo "✅ Web dashboard is accessible"
else
    echo "❌ Web dashboard is not responding"
fi

# Check database
if docker-compose exec -T postgres pg_isready -U million > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not ready"
fi

echo ""
echo "🎉 Million Trader setup complete!"
echo ""
echo "📊 Access points:"
echo "  • Web Dashboard: http://localhost:3003"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Grafana Monitoring: http://localhost:3001 (admin/admin)"
echo "  • Prometheus: http://localhost:9090"
echo ""
echo "📝 Next steps:"
echo "  1. Edit .env file with your API keys"
echo "  2. Configure Telegram bot token and chat ID"
echo "  3. Configure Discord webhook URL"
echo "  4. Restart services: docker-compose restart"
echo ""
echo "🔧 Useful commands:"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop services: docker-compose down"
echo "  • Restart services: docker-compose restart"
echo "  • View API logs: docker-compose logs -f api"
echo "  • View Worker logs: docker-compose logs -f worker"
echo ""
echo "⚠️  IMPORTANT: This is not financial advice. Trade responsibly!"

