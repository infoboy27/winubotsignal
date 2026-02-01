# Monitor Domain Configuration - monitor.winu.app

## ✅ Configuration Complete

Traefik has been successfully configured to route **monitor.winu.app** to your Grafana monitoring dashboard.

## 📊 Access URLs

Your Grafana monitoring dashboard is now accessible via:

1. **Local Access**: http://localhost:3001
2. **External Domain 1**: https://grafana.winu.app
3. **External Domain 2**: https://monitor.winu.app ⭐ NEW

## 🔧 Technical Configuration

### Traefik Router Rule Applied:
```
Host(`grafana.winu.app`) || Host(`monitor.winu.app`)
```

### Docker Compose Labels:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.grafana.rule=Host(`grafana.${DOMAIN:-winu.app}`) || Host(`monitor.${DOMAIN:-winu.app}`)"
  - "traefik.http.routers.grafana.entrypoints=websecure"
  - "traefik.http.routers.grafana.tls.certresolver=cloudflare"
  - "traefik.http.services.grafana.loadbalancer.server.port=3000"
```

### Files Updated:
- ✅ `/home/ubuntu/winubotsignal/docker-compose.yaml`
- ✅ `/home/ubuntu/winubotsignal/docker-compose.traefik.yml`

## 📝 DNS Configuration Required

To make **monitor.winu.app** accessible externally, you need to add a DNS record in Cloudflare:

### Option 1: A Record (Recommended)
```
Type:  A
Name:  monitor
Value: [Your Server IP - same as grafana.winu.app]
Proxy: ✅ Enabled (Orange Cloud)
TTL:   Auto
```

### Option 2: CNAME Record
```
Type:  CNAME
Name:  monitor
Value: grafana.winu.app
Proxy: ✅ Enabled (Orange Cloud)
TTL:   Auto
```

## 🔐 SSL/TLS Certificates

Traefik will automatically obtain and manage SSL certificates for **monitor.winu.app** via:
- Certificate Resolver: Cloudflare
- ACME DNS Challenge
- Auto-renewal enabled

## 🎯 How to Add DNS Record in Cloudflare

1. **Log in to Cloudflare Dashboard**
   - Go to: https://dash.cloudflare.com/

2. **Select your domain** (winu.app)

3. **Navigate to DNS Settings**
   - Click on "DNS" in the left sidebar

4. **Add Record**
   - Click "Add record" button
   - Type: A (or CNAME)
   - Name: `monitor`
   - IPv4 address: [Your server IP] (same as grafana subdomain)
   - Proxy status: ✅ Proxied (orange cloud)
   - TTL: Auto
   - Click "Save"

5. **Wait for DNS Propagation**
   - Usually takes 1-5 minutes
   - Can take up to 24 hours in rare cases

## ✅ Verification

Once DNS is configured, you can verify the setup:

### Test HTTP Response:
```bash
curl -I https://monitor.winu.app
```

### Test DNS Resolution:
```bash
nslookup monitor.winu.app
```

### Check Certificate:
```bash
curl -vI https://monitor.winu.app 2>&1 | grep -E "(SSL|certificate|issuer)"
```

## 🔍 Troubleshooting

### If monitor.winu.app doesn't work:

1. **Check DNS propagation**:
   ```bash
   nslookup monitor.winu.app
   ```

2. **Check Traefik logs**:
   ```bash
   docker logs winu-bot-signal-traefik --tail 50
   ```

3. **Check Grafana container**:
   ```bash
   docker ps | grep grafana
   ```

4. **Verify Traefik routing**:
   ```bash
   docker inspect winu-bot-signal-grafana | grep -A 5 "Labels"
   ```

5. **Check Traefik dashboard** (if enabled):
   - URL: https://traefik.winu.app
   - Look for the grafana router

### Common Issues:

**DNS not resolving:**
- Wait a few minutes for propagation
- Clear DNS cache: `sudo systemd-resolve --flush-caches`
- Check Cloudflare DNS settings

**SSL certificate issues:**
- Traefik will auto-request certificate on first access
- May take 30-60 seconds on first visit
- Check Traefik logs for certificate errors

**403 or 404 errors:**
- Restart Grafana: `docker restart winu-bot-signal-grafana`
- Restart Traefik: `docker restart winu-bot-signal-traefik`

## 🎉 Benefits

### Why monitor.winu.app?

1. **Easier to Remember**: "monitor" is more intuitive than "grafana"
2. **Professional**: Better for sharing with team members
3. **Flexibility**: Can change backend without changing URL
4. **Branding**: Aligns with your monitoring purpose

## 📊 Dashboard Features

Once accessed via monitor.winu.app, you'll have:

- ✅ Server Performance Metrics (CPU, Memory, Disk, Network)
- ✅ Application Metrics (API health, signals, workers)
- ✅ Real-time Monitoring (30s refresh)
- ✅ Historical Data Analysis
- ✅ Custom Dashboards
- ✅ Alert Configuration

## 🔒 Security

- HTTPS enforced via Traefik
- SSL certificates from Let's Encrypt via Cloudflare
- Cloudflare proxy provides DDoS protection
- Admin authentication required (admin/admin)

**⚠️ Security Recommendation**: Change the default Grafana admin password!

```bash
# Access Grafana container
docker exec -it winu-bot-signal-grafana grafana-cli admin reset-admin-password <new-password>
```

## 📚 Related Documentation

- [Grafana Monitoring Setup](GRAFANA_MONITORING.md)
- [Server Performance Metrics](SERVER_PERFORMANCE_METRICS_COMPLETE.md)
- [Traefik Configuration](docker-compose.yaml)

---

**Configuration Date**: October 9, 2025  
**Status**: ✅ Complete - DNS configuration required  
**Domains**: grafana.winu.app, monitor.winu.app  
**Local Port**: 3001





