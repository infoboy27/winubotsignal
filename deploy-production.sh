#!/bin/bash

# Production Deployment Script for Winu Bot Signal
# This script deploys the complete production stack with health checks and monitoring

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="winu-bot-signal"
COMPOSE_FILE="docker-compose.traefik.yml"
ENV_FILE="production.env"
DOMAIN="winu.app"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Production environment file $ENV_FILE not found."
        exit 1
    fi
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file $COMPOSE_FILE not found."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p data/postgres
    mkdir -p data/redis
    mkdir -p data/grafana
    mkdir -p data/prometheus
    mkdir -p data/traefik
    
    print_success "Directories created"
}

# Function to set proper permissions
set_permissions() {
    print_status "Setting proper permissions..."
    
    # Set permissions for Traefik data directory
    chmod 600 data/traefik/acme.json 2>/dev/null || true
    
    # Set permissions for logs directory
    chmod 755 logs
    
    print_success "Permissions set"
}

# Function to stop existing containers
stop_existing() {
    print_status "Stopping existing containers..."
    
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --remove-orphans || true
    
    print_success "Existing containers stopped"
}

# Function to pull latest images
pull_images() {
    print_status "Pulling latest Docker images..."
    
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    
    print_success "Images pulled successfully"
}

# Function to build custom images
build_images() {
    print_status "Building custom images..."
    
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache
    
    print_success "Images built successfully"
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Start infrastructure services first
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d postgres redis
    
    # Wait for infrastructure to be ready
    print_status "Waiting for infrastructure services to be ready..."
    sleep 30
    
    # Start monitoring services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d prometheus grafana postgres-exporter redis-exporter node-exporter
    
    # Start Traefik
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d traefik
    
    # Start application services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d api worker celery-beat
    
    # Start web service last
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d web
    
    print_success "All services started"
}

# Function to wait for service health
wait_for_health() {
    print_status "Waiting for services to be healthy..."
    
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Health check attempt $attempt/$max_attempts"
        
        # Check if all services are running
        local running_services=$(docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps --services --filter "status=running" | wc -l)
        local total_services=$(docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" config --services | wc -l)
        
        if [ "$running_services" -eq "$total_services" ]; then
            print_success "All services are running"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Services failed to start within timeout"
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
            exit 1
        fi
        
        sleep 10
        attempt=$((attempt + 1))
    done
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check API health
    local api_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
    if [ "$api_health" = "200" ]; then
        print_success "API health check passed"
    else
        print_warning "API health check failed (HTTP $api_health)"
    fi
    
    # Check database connection
    if docker exec winu-bot-signal-postgres pg_isready -U winu >/dev/null 2>&1; then
        print_success "Database health check passed"
    else
        print_warning "Database health check failed"
    fi
    
    # Check Redis connection
    if docker exec winu-bot-signal-redis redis-cli ping >/dev/null 2>&1; then
        print_success "Redis health check passed"
    else
        print_warning "Redis health check failed"
    fi
    
    # Check Prometheus
    local prometheus_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090/-/healthy || echo "000")
    if [ "$prometheus_health" = "200" ]; then
        print_success "Prometheus health check passed"
    else
        print_warning "Prometheus health check failed (HTTP $prometheus_health)"
    fi
    
    # Check Grafana
    local grafana_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/health || echo "000")
    if [ "$grafana_health" = "200" ]; then
        print_success "Grafana health check passed"
    else
        print_warning "Grafana health check failed (HTTP $grafana_health)"
    fi
}

# Function to display service URLs
display_urls() {
    print_status "Service URLs:"
    echo ""
    echo -e "${GREEN}Dashboard:${NC} https://dashboard.$DOMAIN"
    echo -e "${GREEN}API:${NC} https://api.$DOMAIN"
    echo -e "${GREEN}Grafana:${NC} https://grafana.$DOMAIN (admin/admin)"
    echo -e "${GREEN}Traefik Dashboard:${NC} https://traefik.$DOMAIN"
    echo -e "${GREEN}Prometheus:${NC} http://localhost:9090"
    echo ""
    echo -e "${YELLOW}Note:${NC} SSL certificates will be automatically generated by Traefik using Cloudflare DNS challenge."
    echo -e "${YELLOW}Note:${NC} It may take a few minutes for SSL certificates to be issued."
}

# Function to show logs
show_logs() {
    print_status "Showing recent logs..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50
}

# Function to setup monitoring alerts
setup_monitoring() {
    print_status "Setting up monitoring alerts..."
    
    # Create alert rules directory if it doesn't exist
    mkdir -p deployments/alert-rules
    
    # Create basic alert rules
    cat > deployments/alert-rules/winu-alerts.yml << EOF
groups:
  - name: winu-bot-signal
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ \$labels.instance }} is down"
          description: "Service {{ \$labels.instance }} has been down for more than 1 minute."
      
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ \$labels.instance }}"
          description: "CPU usage is above 80% for more than 5 minutes."
      
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ \$labels.instance }}"
          description: "Memory usage is above 85% for more than 5 minutes."
      
      - alert: DatabaseConnectionFailure
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Cannot connect to PostgreSQL database."
      
      - alert: RedisConnectionFailure
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis connection failure"
          description: "Cannot connect to Redis."
EOF
    
    print_success "Monitoring alerts configured"
}

# Function to create systemd service for auto-start
create_systemd_service() {
    print_status "Creating systemd service for auto-start..."
    
    local current_dir=$(pwd)
    local user=$(whoami)
    
    sudo tee /etc/systemd/system/winu-bot-signal.service > /dev/null << EOF
[Unit]
Description=Winu Bot Signal Production Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$current_dir
ExecStart=/usr/bin/docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
ExecStop=/usr/bin/docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down
TimeoutStartSec=0
User=$user

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable winu-bot-signal.service
    
    print_success "Systemd service created and enabled"
}

# Main deployment function
main() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "  Winu Bot Signal Production Deployment"
    echo "=========================================="
    echo -e "${NC}"
    
    check_prerequisites
    create_directories
    set_permissions
    stop_existing
    pull_images
    build_images
    start_services
    wait_for_health
    run_health_checks
    setup_monitoring
    create_systemd_service
    
    echo ""
    print_success "Production deployment completed successfully!"
    echo ""
    display_urls
    echo ""
    print_status "To view logs, run: docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE logs -f"
    print_status "To stop services, run: docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down"
    print_status "To restart services, run: sudo systemctl restart winu-bot-signal"
}

# Handle command line arguments
case "${1:-}" in
    "logs")
        show_logs
        ;;
    "health")
        run_health_checks
        ;;
    "stop")
        stop_existing
        ;;
    "restart")
        stop_existing
        start_services
        wait_for_health
        run_health_checks
        ;;
    *)
        main
        ;;
esac






