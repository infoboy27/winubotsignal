# Winu Bot Signal - Grafana Monitoring Integration

## 🎯 Overview

This integration adds comprehensive monitoring capabilities to your existing Grafana setup, providing real-time metrics, alerts, and visualizations for the Winu Bot Signal system.

## 🚀 Features

### 📊 **Custom Metrics**
- **API Health**: Real-time API status monitoring
- **Data Metrics**: Total candles, active assets, data freshness
- **Signal Metrics**: Recent signals, daily signal count
- **Worker Status**: Error and warning detection
- **Performance**: API response times, request rates

### 📈 **Grafana Dashboards**
- **System Overview**: Key metrics at a glance
- **Performance Monitoring**: Response times and throughput
- **Data Quality**: Data freshness and completeness
- **Alert Status**: Real-time alert monitoring

### 🚨 **Alert Rules**
- **API Down**: Critical alert when API is unavailable
- **Data Stale**: Warning when data is older than 6 hours
- **Worker Errors**: Detection of worker process errors
- **No Signals**: Alert when no signals generated
- **High Response Time**: Performance degradation alerts

## 🔧 Setup Instructions

### **1. Deploy the Monitoring System**
```bash
# Run the setup script
./setup_grafana_monitoring.sh
```

### **2. Access Your Dashboards**
- **Grafana**: https://grafana.winu.app
- **Prometheus**: https://prometheus.winu.app
- **Metrics Endpoint**: http://localhost:8002/metrics

### **3. Default Credentials**
- **Grafana**: admin/admin
- **Prometheus**: No authentication required

## 📊 Available Dashboards

### **Winu Bot Signal - System Monitor**
- **System Health**: API status, worker health
- **Data Metrics**: Total candles, active assets
- **Signal Metrics**: Recent signals, daily count
- **Performance**: Response times, request rates
- **Data Freshness**: Hours since last update

### **System Metrics** (Existing)
- **CPU Usage**: System resource utilization
- **Memory Usage**: RAM consumption
- **Disk Usage**: Storage metrics
- **Network**: Network I/O statistics

### **Database Metrics** (Existing)
- **PostgreSQL**: Database performance
- **Redis**: Cache and queue metrics
- **Connection Pools**: Database connections

## 🚨 Alert Configuration

### **Critical Alerts**
- **API Down**: `winu_api_health == 0`
- **Data Ingestion Failed**: No requests in 1 hour
- **Worker Errors**: `winu_worker_errors == 1`

### **Warning Alerts**
- **Data Stale**: Data older than 6 hours
- **No Signals**: No signals generated after 12:00
- **High Response Time**: API response > 5 seconds

### **Alert Channels**
- **Discord**: Already configured
- **Email**: Can be added to AlertManager
- **Slack**: Can be configured in AlertManager

## 📈 Metrics Details

### **Custom Metrics**
```
# API Health
winu_api_health                    # 1=healthy, 0=unhealthy

# Data Metrics
winu_total_candles                # Total OHLCV candles
winu_active_assets               # Active trading assets
winu_total_assets                # Total trading assets
winu_data_freshness_hours        # Hours since last update

# Signal Metrics
winu_recent_signals               # Number of recent signals
winu_signals_today               # Signals generated today

# Worker Status
winu_worker_errors                # Worker error status
winu_worker_warnings             # Worker warning status

# Performance
winu_api_response_time_seconds   # API response time histogram
winu_data_ingestion_requests_total    # Data ingestion counter
winu_signal_generation_requests_total # Signal generation counter
winu_api_requests_total          # API requests counter

# Info
winu_system_info                 # System information
winu_latest_signal               # Latest signal details
```

## 🔧 Configuration

### **Metrics Exporter**
- **Port**: 8002
- **Interval**: 30 seconds
- **API Base**: https://winu.app/api

### **Prometheus Scraping**
- **Job**: winu-bot-metrics
- **Target**: metrics-exporter:8002
- **Interval**: 30 seconds

### **Grafana Dashboard**
- **Auto-refresh**: 30 seconds
- **Time Range**: Last 1 hour
- **Theme**: Dark mode

## 🛠️ Troubleshooting

### **Check Metrics Exporter**
```bash
# Check if running
docker ps | grep metrics-exporter

# View logs
docker logs winu-bot-signal-metrics-exporter

# Test metrics endpoint
curl http://localhost:8002/metrics
```

### **Check Prometheus**
```bash
# Check targets
curl http://localhost:9090/api/v1/targets

# Check if scraping
curl http://localhost:9090/api/v1/query?query=winu_api_health
```

### **Check Grafana**
```bash
# Check if running
docker ps | grep grafana

# View logs
docker logs winu-bot-signal-grafana
```

## 📱 Integration with Existing Monitoring

### **Discord Alerts**
The existing Discord alert system continues to work alongside Grafana:
- **System Alerts**: API health, data freshness
- **Performance Alerts**: Response time, errors
- **Business Alerts**: New signals, data updates

### **Background Monitor**
The background monitor continues to run and provides:
- **Real-time Status**: Command line monitoring
- **Discord Notifications**: Immediate alerts
- **Auto-fix**: Automatic issue resolution

### **API Endpoints**
All existing API endpoints remain functional:
- **Status API**: https://winu.app/api/monitor/status
- **Health API**: https://winu.app/api/monitor/health
- **Admin API**: https://winu.app/api/admin/*

## 🎯 Benefits

### **Visual Monitoring**
- **Real-time Dashboards**: Live system status
- **Historical Data**: Trend analysis
- **Performance Metrics**: Response time tracking
- **Alert Visualization**: Alert status overview

### **Professional Monitoring**
- **Enterprise-grade**: Prometheus + Grafana stack
- **Scalable**: Handles high-volume metrics
- **Extensible**: Easy to add new metrics
- **Reliable**: Industry-standard tools

### **Enhanced Alerting**
- **Multiple Channels**: Discord, Email, Slack
- **Smart Thresholds**: Context-aware alerts
- **Alert History**: Track alert patterns
- **Escalation**: Multi-level alerting

## 🔄 Maintenance

### **Regular Tasks**
- **Monitor Dashboard**: Check daily for issues
- **Review Alerts**: Ensure alert thresholds are appropriate
- **Update Metrics**: Add new metrics as needed
- **Backup Configuration**: Save dashboard configurations

### **Scaling**
- **Add Metrics**: Extend metrics_exporter.py
- **New Dashboards**: Create additional Grafana dashboards
- **Alert Rules**: Add new Prometheus alert rules
- **Data Retention**: Configure Prometheus retention

## 📞 Support

For issues with the monitoring system:
1. **Check Logs**: `docker logs winu-bot-signal-metrics-exporter`
2. **Verify Metrics**: `curl http://localhost:8002/metrics`
3. **Test API**: `curl https://winu.app/api/monitor/status`
4. **Restart Services**: `docker-compose restart metrics-exporter prometheus`

The monitoring system is now fully integrated with your existing Grafana setup! 🚀





