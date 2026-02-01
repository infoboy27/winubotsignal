#!/bin/bash

# Test script for production deployment
# This script validates the deployment configuration and tests connectivity

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Test configuration files
test_config_files() {
    print_status "Testing configuration files..."
    
    if [ ! -f "production.env" ]; then
        print_error "production.env file not found"
        return 1
    fi
    
    if [ ! -f "docker-compose.traefik.yml" ]; then
        print_error "docker-compose.traefik.yml file not found"
        return 1
    fi
    
    # Test docker-compose configuration
    if docker-compose -f docker-compose.traefik.yml --env-file production.env config --quiet; then
        print_success "Docker Compose configuration is valid"
    else
        print_error "Docker Compose configuration is invalid"
        return 1
    fi
    
    print_success "Configuration files are valid"
}

# Test environment variables
test_environment() {
    print_status "Testing environment variables..."
    
    source production.env
    
    # Check required variables
    required_vars=(
        "POSTGRES_DB"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "JWT_SECRET"
        "DOMAIN"
        "CLOUDFLARE_EMAIL"
        "CLOUDFLARE_API_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Required environment variable $var is not set"
            return 1
        fi
    done
    
    print_success "Environment variables are properly configured"
}

# Test Docker and Docker Compose
test_docker() {
    print_status "Testing Docker and Docker Compose..."
    
    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker is not installed"
        return 1
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "Docker Compose is not installed"
        return 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        return 1
    fi
    
    print_success "Docker and Docker Compose are working"
}

# Test network connectivity
test_connectivity() {
    print_status "Testing network connectivity..."
    
    # Test Cloudflare API connectivity
    if curl -s -f "https://api.cloudflare.com/client/v4/user/tokens/verify" \
        -H "Authorization: Bearer $CLOUDFLARE_API_KEY" >/dev/null; then
        print_success "Cloudflare API connectivity is working"
    else
        print_warning "Cloudflare API connectivity test failed (this may be normal if API key is not yet valid)"
    fi
    
    # Test external API connectivity
    if curl -s -f "https://api.coingecko.com/api/v3/ping" >/dev/null; then
        print_success "External API connectivity is working"
    else
        print_warning "External API connectivity test failed"
    fi
}

# Test file permissions
test_permissions() {
    print_status "Testing file permissions..."
    
    if [ -f "deploy-production.sh" ] && [ -x "deploy-production.sh" ]; then
        print_success "Deployment script is executable"
    else
        print_warning "Deployment script is not executable"
    fi
    
    # Check if we can create necessary directories
    if mkdir -p test-dir 2>/dev/null; then
        rmdir test-dir
        print_success "Directory creation permissions are working"
    else
        print_error "Cannot create directories"
        return 1
    fi
}

# Test Docker images availability
test_docker_images() {
    print_status "Testing Docker image availability..."
    
    # Test if we can pull required images
    images=(
        "timescale/timescaledb:latest-pg15"
        "redis:7-alpine"
        "traefik:v2.10"
        "prom/prometheus:latest"
        "grafana/grafana:latest"
        "prometheuscommunity/postgres-exporter:latest"
        "oliver006/redis_exporter:latest"
        "prom/node-exporter:latest"
        "prom/alertmanager:latest"
    )
    
    for image in "${images[@]}"; do
        if docker pull "$image" >/dev/null 2>&1; then
            print_success "Image $image is available"
        else
            print_warning "Could not pull image $image"
        fi
    done
}

# Main test function
main() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "  Winu Bot Signal Deployment Test"
    echo "=========================================="
    echo -e "${NC}"
    
    local tests_passed=0
    local tests_failed=0
    
    # Run all tests
    if test_config_files; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_environment; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_docker; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_connectivity; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_permissions; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_docker_images; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    echo ""
    echo "=========================================="
    echo "Test Results:"
    echo -e "${GREEN}Passed: $tests_passed${NC}"
    echo -e "${RED}Failed: $tests_failed${NC}"
    echo "=========================================="
    
    if [ $tests_failed -eq 0 ]; then
        echo ""
        print_success "All tests passed! Ready for production deployment."
        echo ""
        echo "To deploy to production, run:"
        echo -e "${BLUE}./deploy-production.sh${NC}"
    else
        echo ""
        print_error "Some tests failed. Please fix the issues before deploying."
        exit 1
    fi
}

# Run the tests
main






