#!/bin/bash

echo "🤖 Setting up Winu Bot Signal Grafana Monitoring"
echo "================================================="

# Make scripts executable
chmod +x apps/monitoring/metrics_exporter.py

# Create necessary directories
mkdir -p deployments/grafana/provisioning/dashboards
mkdir -p deployments/grafana/dashboards
mkdir -p deployments/prometheus/alert-rules

# Copy alert rules
cp deployments/prometheus/winu-bot-rules.yml deployments/prometheus/alert-rules/

# Build and start the metrics exporter
echo "🔧 Building metrics exporter..."
docker-compose -f docker-compose.traefik.yml build metrics-exporter

echo "🚀 Starting metrics exporter..."
docker-compose -f docker-compose.traefik.yml up -d metrics-exporter

# Restart Prometheus to pick up new configuration
echo "🔄 Restarting Prometheus..."
docker-compose -f docker-compose.traefik.yml restart prometheus

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check if metrics exporter is running
echo "📊 Checking metrics exporter status..."
if curl -s http://localhost:8002/metrics > /dev/null; then
    echo "✅ Metrics exporter is running"
else
    echo "❌ Metrics exporter is not responding"
fi

# Check Prometheus targets
echo "📈 Checking Prometheus targets..."
if curl -s http://localhost:9090/api/v1/targets | grep -q "winu-bot-metrics"; then
    echo "✅ Prometheus is scraping metrics"
else
    echo "⚠️  Prometheus may not be scraping metrics yet"
fi

echo ""
echo "✅ Grafana monitoring setup complete!"
echo ""
echo "🌐 Access your monitoring:"
echo "  - Grafana: https://grafana.winu.app"
echo "  - Prometheus: https://prometheus.winu.app"
echo "  - Metrics: http://localhost:8002/metrics"
echo ""
echo "📊 Available dashboards:"
echo "  - Winu Bot Signal - System Monitor"
echo "  - System metrics (CPU, Memory, Disk)"
echo "  - Database metrics (PostgreSQL, Redis)"
echo ""
echo "🚨 Alert rules configured:"
echo "  - API Health monitoring"
echo "  - Data freshness alerts"
echo "  - Worker error detection"
echo "  - Signal generation monitoring"
echo "  - Response time monitoring"
echo ""
echo "🔧 To view metrics:"
echo "  - Check Prometheus targets: http://localhost:9090/targets"
echo "  - View metrics: http://localhost:8002/metrics"
echo "  - Grafana dashboards: https://grafana.winu.app"





