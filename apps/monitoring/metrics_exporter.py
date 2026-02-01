#!/usr/bin/env python3
"""
Winu Bot Signal Metrics Exporter
Exports custom metrics to Prometheus for Grafana visualization
"""

import time
import requests
import json
import sys
import os
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Info
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WinuBotMetricsExporter:
    def __init__(self, api_base="http://winu-bot-signal-api:8001", port=8002):
        self.api_base = api_base
        self.port = port
        
        # Prometheus metrics
        self.api_health = Gauge('winu_api_health', 'API health status (1=healthy, 0=unhealthy)')
        self.total_candles = Gauge('winu_total_candles', 'Total number of OHLCV candles')
        self.active_assets = Gauge('winu_active_assets', 'Number of active trading assets')
        self.total_assets = Gauge('winu_total_assets', 'Total number of trading assets')
        self.recent_signals = Gauge('winu_recent_signals', 'Number of recent signals')
        self.signals_today = Gauge('winu_signals_today', 'Number of signals generated today')
        self.worker_errors = Gauge('winu_worker_errors', 'Number of worker errors')
        self.worker_warnings = Gauge('winu_worker_warnings', 'Number of worker warnings')
        self.data_freshness = Gauge('winu_data_freshness_hours', 'Hours since last data update')
        
        # Counters
        self.data_ingestion_requests = Counter('winu_data_ingestion_requests_total', 'Total data ingestion requests')
        self.signal_generation_requests = Counter('winu_signal_generation_requests_total', 'Total signal generation requests')
        self.api_requests = Counter('winu_api_requests_total', 'Total API requests', ['endpoint', 'status'])
        
        # Histograms
        self.api_response_time = Histogram('winu_api_response_time_seconds', 'API response time', ['endpoint'])
        
        # Info
        self.system_info = Info('winu_system_info', 'System information')
        self.latest_signal = Info('winu_latest_signal', 'Latest trading signal information')
        
    def fetch_system_status(self):
        """Fetch system status from API"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.api_base}/monitor/status", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.api_requests.labels(endpoint='monitor/status', status='success').inc()
                self.api_response_time.labels(endpoint='monitor/status').observe(response_time)
                return response.json()
            else:
                self.api_requests.labels(endpoint='monitor/status', status='error').inc()
                logger.error(f"API returned status {response.status_code}")
                return None
                
        except Exception as e:
            self.api_requests.labels(endpoint='monitor/status', status='error').inc()
            logger.error(f"Failed to fetch system status: {e}")
            return None
    
    def update_metrics(self, status_data):
        """Update Prometheus metrics with system status"""
        if not status_data:
            return
            
        try:
            # API Health
            api_healthy = status_data.get('health', {}).get('services', {}).get('api', {}).get('status') == 'healthy'
            self.api_health.set(1 if api_healthy else 0)
            
            # Data Ingestion Metrics
            data_ingestion = status_data.get('data_ingestion', {})
            if data_ingestion.get('status') == 'success':
                self.total_candles.set(data_ingestion.get('total_candles', 0))
                self.active_assets.set(data_ingestion.get('active_assets', 0))
                self.total_assets.set(data_ingestion.get('total_assets', 0))
                
                # Calculate data freshness
                last_update = data_ingestion.get('last_data_update')
                if last_update:
                    try:
                        last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        hours_old = (datetime.now() - last_update_time).total_seconds() / 3600
                        self.data_freshness.set(hours_old)
                    except Exception as e:
                        logger.warning(f"Failed to parse last update time: {e}")
                        self.data_freshness.set(999)  # Very old
                else:
                    self.data_freshness.set(999)  # No data
            
            # Signal Generation Metrics
            signal_generation = status_data.get('signal_generation', {})
            if signal_generation.get('status') == 'success':
                self.recent_signals.set(signal_generation.get('recent_signals', 0))
                self.signals_today.set(signal_generation.get('signals_today', 0))
                
                # Latest signal info
                latest = signal_generation.get('latest_signal')
                if latest:
                    self.latest_signal.info({
                        'symbol': latest.get('symbol', 'N/A'),
                        'direction': latest.get('direction', 'N/A'),
                        'created_at': latest.get('created_at', 'N/A')
                    })
            
            # Worker Logs Metrics
            worker_logs = status_data.get('worker_logs', {})
            if worker_logs.get('status') == 'success':
                self.worker_errors.set(1 if worker_logs.get('has_errors') else 0)
                self.worker_warnings.set(1 if worker_logs.get('has_warnings') else 0)
            
            # System Info
            self.system_info.info({
                'timestamp': status_data.get('timestamp', 'N/A'),
                'version': '1.0.0',
                'environment': 'production'
            })
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    def trigger_data_ingestion(self):
        """Trigger data ingestion and update metrics"""
        try:
            response = requests.post(f"{self.api_base}/admin/ingest-data", timeout=30)
            if response.status_code == 200:
                self.data_ingestion_requests.inc()
                logger.info("Data ingestion triggered successfully")
                return True
            else:
                logger.error(f"Failed to trigger data ingestion: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error triggering data ingestion: {e}")
            return False
    
    def trigger_signal_generation(self):
        """Trigger signal generation and update metrics"""
        try:
            response = requests.post(f"{self.api_base}/admin/generate-signals", timeout=30)
            if response.status_code == 200:
                self.signal_generation_requests.inc()
                logger.info("Signal generation triggered successfully")
                return True
            else:
                logger.error(f"Failed to trigger signal generation: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error triggering signal generation: {e}")
            return False
    
    def run_metrics_loop(self, interval=30):
        """Run the metrics collection loop"""
        logger.info(f"Starting metrics exporter on port {self.port}")
        logger.info(f"Collecting metrics every {interval} seconds")
        
        # Start Prometheus metrics server
        start_http_server(self.port)
        
        while True:
            try:
                # Fetch system status
                status_data = self.fetch_system_status()
                
                # Update metrics
                self.update_metrics(status_data)
                
                # Auto-trigger actions based on metrics
                if status_data:
                    data_ingestion = status_data.get('data_ingestion', {})
                    if data_ingestion.get('status') == 'success':
                        last_update = data_ingestion.get('last_data_update')
                        if last_update:
                            try:
                                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                                hours_old = (datetime.now() - last_update_time).total_seconds() / 3600
                                if hours_old > 2:  # Data is older than 2 hours
                                    logger.info(f"Data is {hours_old:.1f} hours old, triggering refresh...")
                                    self.trigger_data_ingestion()
                            except Exception as e:
                                logger.warning(f"Failed to check data freshness: {e}")
                
                logger.info("Metrics updated successfully")
                
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
            
            time.sleep(interval)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Winu Bot Signal Metrics Exporter')
    parser.add_argument('--port', type=int, default=8002, help='Port for metrics server')
    parser.add_argument('--interval', type=int, default=30, help='Metrics collection interval in seconds')
    parser.add_argument('--api-base', default='http://winu-bot-signal-api:8001', help='API base URL')
    
    args = parser.parse_args()
    
    exporter = WinuBotMetricsExporter(api_base=args.api_base, port=args.port)
    exporter.run_metrics_loop(interval=args.interval)

if __name__ == "__main__":
    main()





