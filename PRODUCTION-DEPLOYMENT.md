# Winu Bot Signal - Production Deployment Guide

This guide covers the complete production deployment of the Winu Bot Signal trading system with monitoring, alerting, and automatic SSL certificate management.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Cloudflare account with API access
- Domain configured with Cloudflare DNS
- Server with at least 4GB RAM and 2 CPU cores

### 1. Deploy to Production

```bash
# Make the deployment script executable
chmod +x deploy-production.sh

# Run the production deployment
./deploy-production.sh
```

### 2. Access Your Services

After deployment, your services will be available at:

- **Dashboard**: https://dashboard.winu.app
- **API**: https://api.winu.app
- **Grafana Monitoring**: https://grafana.winu.app (admin/admin)
- **Traefik Dashboard**: https://traefik.winu.app
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

## 📋 Architecture Overview

The production stack includes:

### Core Services
- **API**: FastAPI backend with trading signal generation
- **Web Dashboard**: Next.js frontend for monitoring and control
- **Worker**: Celery workers for background tasks
- **Celery Beat**: Scheduled task scheduler

### Infrastructure
- **PostgreSQL**: TimescaleDB for time-series data storage
- **Redis**: Message broker and caching
- **Traefik**: Reverse proxy with automatic SSL certificates

### Monitoring & Alerting
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notifications
- **Exporters**: PostgreSQL, Redis, and Node metrics

## 🔧 Configuration

### Environment Variables

All configuration is managed through the `production.env` file:

```bash
# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=winudb
POSTGRES_USER=winu
POSTGRES_PASSWORD=winu250420

# API Keys and Secrets
CMC_API_KEY=your_coinmarketcap_key
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DISCORD_WEBHOOK_URL=your_discord_webhook

# Domain Configuration
DOMAIN=winu.app
CLOUDFLARE_EMAIL=your_cloudflare_email
CLOUDFLARE_API_KEY=your_cloudflare_api_key
```

### SSL Certificates

SSL certificates are automatically managed by Traefik using Cloudflare DNS challenge. No manual certificate management required.

## 📊 Monitoring

### Grafana Dashboards

The system includes pre-configured dashboards for:

- **Service Status**: Real-time health of all services
- **System Metrics**: CPU, memory, and disk usage
- **Database Performance**: PostgreSQL connection and query metrics
- **Redis Performance**: Connection and memory usage
- **API Metrics**: Request rates and response times

### Alerting

Alerts are configured for:

- **Service Downtime**: Critical alerts for service failures
- **High Resource Usage**: CPU and memory warnings
- **Database Issues**: Connection failures and performance problems
- **Redis Issues**: Connection failures and memory usage

Alerts are sent to:
- Telegram (configured chat ID)
- Discord (configured webhook)
- Webhook endpoint in the API

## 🛠️ Management Commands

### Deployment Script Usage

```bash
# Full deployment
./deploy-production.sh

# View logs
./deploy-production.sh logs

# Health check
./deploy-production.sh health

# Stop services
./deploy-production.sh stop

# Restart services
./deploy-production.sh restart
```

### Docker Compose Commands

```bash
# Start all services
docker-compose -f docker-compose.traefik.yml --env-file production.env up -d

# Stop all services
docker-compose -f docker-compose.traefik.yml --env-file production.env down

# View logs
docker-compose -f docker-compose.traefik.yml --env-file production.env logs -f

# Restart specific service
docker-compose -f docker-compose.traefik.yml --env-file production.env restart api
```

### System Service

The deployment creates a systemd service for automatic startup:

```bash
# Enable auto-start
sudo systemctl enable winu-bot-signal

# Start services
sudo systemctl start winu-bot-signal

# Stop services
sudo systemctl stop winu-bot-signal

# Check status
sudo systemctl status winu-bot-signal
```

## 🔍 Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   - Ensure Cloudflare API key has DNS edit permissions
   - Check domain DNS settings in Cloudflare
   - Verify email address matches Cloudflare account

2. **Service Health Check Failures**
   - Check service logs: `docker-compose logs [service-name]`
   - Verify environment variables in `production.env`
   - Ensure all required API keys are configured

3. **Database Connection Issues**
   - Verify PostgreSQL is running: `docker-compose ps postgres`
   - Check database credentials in environment file
   - Ensure database initialization completed

4. **Monitoring Issues**
   - Verify Prometheus targets: http://localhost:9090/targets
   - Check Grafana datasource configuration
   - Ensure exporters are running and accessible

### Log Locations

- **Application Logs**: `docker-compose logs [service-name]`
- **System Logs**: `/var/log/syslog`
- **Service Logs**: `journalctl -u winu-bot-signal`

### Health Check Endpoints

- **API Health**: http://localhost:8000/health
- **Prometheus Health**: http://localhost:9090/-/healthy
- **Grafana Health**: http://localhost:3001/api/health

## 🔒 Security Considerations

### Production Security

1. **Environment Variables**: Never commit sensitive data to version control
2. **API Keys**: Rotate keys regularly and use least-privilege access
3. **Network Security**: Use firewall rules to restrict access
4. **SSL/TLS**: All external traffic is encrypted via Traefik
5. **Database Security**: Use strong passwords and limit network access

### Backup Strategy

1. **Database Backups**: Regular PostgreSQL dumps
2. **Configuration Backups**: Version control for all config files
3. **Volume Backups**: Regular backup of Docker volumes

## 📈 Scaling

### Horizontal Scaling

- **API**: Scale by running multiple API containers
- **Workers**: Increase Celery worker concurrency or add more workers
- **Database**: Consider read replicas for high read loads

### Vertical Scaling

- **Memory**: Increase container memory limits
- **CPU**: Adjust CPU limits for compute-intensive tasks
- **Storage**: Monitor disk usage and expand as needed

## 🔄 Updates and Maintenance

### Rolling Updates

```bash
# Pull latest images
docker-compose -f docker-compose.traefik.yml --env-file production.env pull

# Rebuild and restart
docker-compose -f docker-compose.traefik.yml --env-file production.env up -d --build
```

### Database Migrations

```bash
# Run migrations (if needed)
docker-compose -f docker-compose.traefik.yml --env-file production.env exec api python -m alembic upgrade head
```

## 📞 Support

For issues and support:

1. Check the logs first: `./deploy-production.sh logs`
2. Run health checks: `./deploy-production.sh health`
3. Review this documentation
4. Check service status: `docker-compose ps`

## 🎯 Performance Optimization

### Recommended Settings

- **Memory**: 4GB+ RAM for production workloads
- **CPU**: 2+ cores for optimal performance
- **Storage**: SSD recommended for database performance
- **Network**: Stable internet connection for API calls

### Monitoring Recommendations

- Set up external monitoring (UptimeRobot, Pingdom)
- Configure log aggregation (ELK stack, Fluentd)
- Implement backup monitoring and alerting
- Regular performance reviews and optimization

---

**Note**: This deployment is configured for production use with automatic SSL certificates, comprehensive monitoring, and alerting. Ensure all API keys and secrets are properly configured before deployment.






