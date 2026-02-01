#!/bin/bash

echo "🧪 Testing Grafana Server Performance Metrics"
echo "============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if node-exporter is running
echo "1️⃣  Checking node-exporter status..."
if docker ps | grep -q "winu-bot-signal-node-exporter"; then
    echo -e "${GREEN}✅ Node-exporter container is running${NC}"
else
    echo -e "${RED}❌ Node-exporter container is not running${NC}"
    echo "   Starting node-exporter..."
    docker-compose -f docker-compose.traefik.yml up -d node-exporter
    sleep 5
fi
echo ""

# Test 2: Check if node-exporter metrics are available
echo "2️⃣  Testing node-exporter metrics endpoint..."
if curl -s http://localhost:9100/metrics | head -20 > /dev/null; then
    echo -e "${GREEN}✅ Node-exporter metrics endpoint is accessible${NC}"
    echo "   Sample metrics:"
    curl -s http://localhost:9100/metrics | grep -E "^node_(cpu|memory|disk|network)_" | head -5
else
    echo -e "${RED}❌ Cannot access node-exporter metrics${NC}"
fi
echo ""

# Test 3: Check if Prometheus is running
echo "3️⃣  Checking Prometheus status..."
if docker ps | grep -q "winu-bot-signal-prometheus"; then
    echo -e "${GREEN}✅ Prometheus container is running${NC}"
else
    echo -e "${RED}❌ Prometheus container is not running${NC}"
    echo "   Starting Prometheus..."
    docker-compose -f docker-compose.traefik.yml up -d prometheus
    sleep 10
fi
echo ""

# Test 4: Check if Prometheus is scraping node-exporter
echo "4️⃣  Checking if Prometheus is scraping node-exporter..."
PROM_RESPONSE=$(curl -s "http://localhost:9090/api/v1/query?query=up{job='node-exporter'}")
if echo "$PROM_RESPONSE" | grep -q '"value":\[.*,"1"\]'; then
    echo -e "${GREEN}✅ Prometheus is successfully scraping node-exporter${NC}"
else
    echo -e "${YELLOW}⚠️  Prometheus may not be scraping node-exporter yet${NC}"
    echo "   Response: $PROM_RESPONSE"
fi
echo ""

# Test 5: Check CPU metrics
echo "5️⃣  Testing CPU metrics..."
CPU_RESPONSE=$(curl -s "http://localhost:9090/api/v1/query?query=node_cpu_seconds_total")
if echo "$CPU_RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✅ CPU metrics are available in Prometheus${NC}"
    # Calculate current CPU usage
    CPU_IDLE=$(curl -s "http://localhost:9090/api/v1/query?query=avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m]))*100" | grep -oP '"value":\[\d+,"\K[0-9.]+')
    if [ ! -z "$CPU_IDLE" ]; then
        CPU_USAGE=$(echo "100 - $CPU_IDLE" | bc -l | awk '{printf "%.2f", $0}')
        echo "   Current CPU Usage: ${CPU_USAGE}%"
    fi
else
    echo -e "${RED}❌ CPU metrics not available${NC}"
fi
echo ""

# Test 6: Check Memory metrics
echo "6️⃣  Testing Memory metrics..."
MEM_TOTAL=$(curl -s "http://localhost:9090/api/v1/query?query=node_memory_MemTotal_bytes" | grep -oP '"value":\[\d+,"\K[0-9]+')
MEM_AVAIL=$(curl -s "http://localhost:9090/api/v1/query?query=node_memory_MemAvailable_bytes" | grep -oP '"value":\[\d+,"\K[0-9]+')
if [ ! -z "$MEM_TOTAL" ] && [ ! -z "$MEM_AVAIL" ]; then
    echo -e "${GREEN}✅ Memory metrics are available in Prometheus${NC}"
    MEM_USED=$((MEM_TOTAL - MEM_AVAIL))
    MEM_USAGE=$(echo "scale=2; $MEM_USED * 100 / $MEM_TOTAL" | bc)
    MEM_TOTAL_GB=$(echo "scale=2; $MEM_TOTAL / 1024 / 1024 / 1024" | bc)
    MEM_USED_GB=$(echo "scale=2; $MEM_USED / 1024 / 1024 / 1024" | bc)
    echo "   Total Memory: ${MEM_TOTAL_GB} GB"
    echo "   Used Memory: ${MEM_USED_GB} GB (${MEM_USAGE}%)"
else
    echo -e "${RED}❌ Memory metrics not available${NC}"
fi
echo ""

# Test 7: Check Disk metrics
echo "7️⃣  Testing Disk metrics..."
DISK_SIZE=$(curl -s "http://localhost:9090/api/v1/query?query=node_filesystem_size_bytes{mountpoint=\"/\",fstype!=\"rootfs\"}" | grep -oP '"value":\[\d+,"\K[0-9]+' | head -1)
DISK_AVAIL=$(curl -s "http://localhost:9090/api/v1/query?query=node_filesystem_avail_bytes{mountpoint=\"/\",fstype!=\"rootfs\"}" | grep -oP '"value":\[\d+,"\K[0-9]+' | head -1)
if [ ! -z "$DISK_SIZE" ] && [ ! -z "$DISK_AVAIL" ]; then
    echo -e "${GREEN}✅ Disk metrics are available in Prometheus${NC}"
    DISK_USED=$((DISK_SIZE - DISK_AVAIL))
    DISK_USAGE=$(echo "scale=2; $DISK_USED * 100 / $DISK_SIZE" | bc)
    DISK_SIZE_GB=$(echo "scale=2; $DISK_SIZE / 1024 / 1024 / 1024" | bc)
    DISK_USED_GB=$(echo "scale=2; $DISK_USED / 1024 / 1024 / 1024" | bc)
    echo "   Total Disk: ${DISK_SIZE_GB} GB"
    echo "   Used Disk: ${DISK_USED_GB} GB (${DISK_USAGE}%)"
else
    echo -e "${RED}❌ Disk metrics not available${NC}"
fi
echo ""

# Test 8: Check Network metrics
echo "8️⃣  Testing Network metrics..."
NET_RESPONSE=$(curl -s "http://localhost:9090/api/v1/query?query=node_network_receive_bytes_total")
if echo "$NET_RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✅ Network metrics are available in Prometheus${NC}"
    # Get list of network devices
    NET_DEVICES=$(curl -s "http://localhost:9090/api/v1/query?query=node_network_receive_bytes_total" | grep -oP '"device":"\K[^"]+' | grep -v "lo" | head -3)
    if [ ! -z "$NET_DEVICES" ]; then
        echo "   Network devices monitored: $(echo $NET_DEVICES | tr '\n' ', ' | sed 's/,$//')"
    fi
else
    echo -e "${RED}❌ Network metrics not available${NC}"
fi
echo ""

# Test 9: Check if Grafana is running
echo "9️⃣  Checking Grafana status..."
if docker ps | grep -q "winu-bot-signal-grafana"; then
    echo -e "${GREEN}✅ Grafana container is running${NC}"
else
    echo -e "${RED}❌ Grafana container is not running${NC}"
    echo "   Starting Grafana..."
    docker-compose -f docker-compose.traefik.yml up -d grafana
    sleep 10
fi
echo ""

# Test 10: Check if new dashboard exists
echo "🔟 Checking if dashboard file exists..."
if [ -f "/home/ubuntu/winubotsignal/deployments/grafana/dashboards/winu-bot-dashboard-with-server-metrics.json" ]; then
    echo -e "${GREEN}✅ New dashboard file exists${NC}"
else
    echo -e "${RED}❌ Dashboard file not found${NC}"
fi
echo ""

# Test 11: Verify Grafana API access
echo "1️⃣1️⃣  Testing Grafana API..."
GRAFANA_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health)
if [ "$GRAFANA_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ Grafana API is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Grafana API returned status code: $GRAFANA_RESPONSE${NC}"
fi
echo ""

# Test 12: System Load Average
echo "1️⃣2️⃣  Testing System Load metrics..."
LOAD_1=$(curl -s "http://localhost:9090/api/v1/query?query=node_load1" | grep -oP '"value":\[\d+,"\K[0-9.]+')
LOAD_5=$(curl -s "http://localhost:9090/api/v1/query?query=node_load5" | grep -oP '"value":\[\d+,"\K[0-9.]+')
LOAD_15=$(curl -s "http://localhost:9090/api/v1/query?query=node_load15" | grep -oP '"value":\[\d+,"\K[0-9.]+')
if [ ! -z "$LOAD_1" ]; then
    echo -e "${GREEN}✅ System load metrics are available${NC}"
    echo "   Load Average: $LOAD_1 (1m), $LOAD_5 (5m), $LOAD_15 (15m)"
else
    echo -e "${RED}❌ System load metrics not available${NC}"
fi
echo ""

echo "============================================="
echo "🎉 Testing Complete!"
echo ""
echo "📊 Access your dashboards:"
echo "   - Grafana: http://localhost:3000 or https://grafana.winu.app"
echo "   - Prometheus: http://localhost:9090 or https://prometheus.winu.app"
echo "   - Node Exporter: http://localhost:9100/metrics"
echo ""
echo "🔑 Default Grafana credentials:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "📈 Available dashboards:"
echo "   - Winu Bot Signal - System Monitor (original)"
echo "   - Winu Bot Signal - Complete System Monitor (with server metrics)"
echo ""
echo "💡 Next steps:"
echo "   1. Log in to Grafana at http://localhost:3000"
echo "   2. Navigate to Dashboards"
echo "   3. Open 'Winu Bot Signal - Complete System Monitor'"
echo "   4. You should see server performance metrics (CPU, Memory, Disk, Network)"
echo ""





