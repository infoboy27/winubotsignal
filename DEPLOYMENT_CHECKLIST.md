# 🚀 DEPLOYMENT CHECKLIST

## Pre-Deployment Checklist for Winu Bot Signal

Use this checklist before deploying to production.

---

## ☑️ CRITICAL SECURITY TASKS

### 1. Credential Rotation (MUST DO FIRST!)

- [ ] **Rotate Binance API Keys**
  - Visit: https://www.binance.com/en/my/settings/api-management
  - Delete old keys
  - Create new API key with minimal required permissions
  - Update `production.env`

- [ ] **Rotate Telegram Bot Token**
  - Contact: @BotFather on Telegram
  - Use `/revoke` command
  - Create new bot token
  - Update `production.env`

- [ ] **Regenerate Discord Webhook**
  - Go to Discord Server Settings → Integrations → Webhooks
  - Delete old webhook
  - Create new webhook URL
  - Update `production.env`

- [ ] **Rotate Stripe Keys**
  - Visit: https://dashboard.stripe.com/apikeys
  - Rotate secret key and webhook secret
  - Update `production.env`

- [ ] **Rotate SendGrid API Key**
  - Visit: https://app.sendgrid.com/settings/api_keys
  - Delete old key
  - Create new API key
  - Update `production.env`

- [ ] **Generate New Secrets**
  ```bash
  # JWT Secret
  openssl rand -hex 32
  
  # NEXTAUTH Secret
  openssl rand -base64 32
  
  # Database Password
  openssl rand -base64 24
  ```

- [ ] **Update Database Password**
  ```sql
  -- In PostgreSQL
  ALTER USER winu WITH PASSWORD 'new_secure_password_here';
  ```

### 2. Git Security

- [ ] **Remove sensitive files from Git history**
  ```bash
  # Install git-filter-repo
  pip install git-filter-repo
  
  # Remove env files from history
  git filter-repo --invert-paths --path production.env --path development.env --force
  ```

- [ ] **Verify .gitignore is working**
  ```bash
  git check-ignore production.env  # Should output: production.env
  git check-ignore development.env  # Should output: development.env
  ```

- [ ] **Commit updated code** (without credentials)
  ```bash
  git add .
  git commit -m "Security hardening and dependency updates"
  git push origin main
  ```

---

## ☑️ ENVIRONMENT SETUP

### 3. Configure Environment

- [ ] **Copy template and fill with NEW credentials**
  ```bash
  cp env.example production.env
  nano production.env
  ```

- [ ] **Verify all required variables are set**
  ```bash
  grep -E "your_|change_this|generate_" production.env
  # Should return no matches
  ```

- [ ] **Set proper admin credentials**
  - Use strong password (32+ characters)
  - Store credentials in password manager

---

## ☑️ DEPENDENCY INSTALLATION

### 4. Update All Dependencies

- [ ] **Backend API**
  ```bash
  cd apps/api
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

- [ ] **Worker**
  ```bash
  cd apps/worker
  pip install -r requirements.txt
  ```

- [ ] **Frontend**
  ```bash
  cd apps/web
  npm install
  npm run build  # Test build
  ```

---

## ☑️ DATABASE SETUP

### 5. Run Migrations

- [ ] **Run email verification migration**
  ```bash
  cd apps/api
  python migration.py
  ```

- [ ] **Run subscription migration**
  ```bash
  psql -U winu -d winudb -f ../migrations/add_subscription_fields.sql
  ```

- [ ] **Verify tables created**
  ```bash
  psql -U winu -d winudb -c "\dt"
  # Should show: users, email_verifications, subscription_events, etc.
  ```

---

## ☑️ DOCKER DEPLOYMENT

### 6. Build and Deploy Containers

- [ ] **Build all images**
  ```bash
  docker-compose build --no-cache
  ```

- [ ] **Start services**
  ```bash
  docker-compose up -d
  ```

- [ ] **Check service health**
  ```bash
  docker-compose ps
  docker-compose logs -f api
  ```

- [ ] **Verify services are running**
  - [ ] PostgreSQL: `docker-compose exec postgres pg_isready`
  - [ ] Redis: `docker-compose exec redis redis-cli ping`
  - [ ] API: `curl http://localhost:8001/health`
  - [ ] Web: `curl http://localhost:3005`

---

## ☑️ TESTING

### 7. Functional Testing

- [ ] **Test authentication**
  - [ ] Try logging in with admin credentials
  - [ ] Verify JWT token is generated
  - [ ] Test logout functionality

- [ ] **Test API endpoints**
  ```bash
  # Health check
  curl http://localhost:8001/health
  
  # With authentication
  curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8001/signals/recent
  ```

- [ ] **Test rate limiting**
  ```bash
  # Should get 429 after 60 requests in 1 minute
  for i in {1..65}; do curl http://localhost:8001/health; done
  ```

- [ ] **Test WebSocket connection**
  ```bash
  # Use wscat or similar tool
  wscat -c ws://localhost:8001/ws/alerts
  ```

- [ ] **Test Stripe webhook**
  ```bash
  # Use Stripe CLI
  stripe listen --forward-to localhost:8001/billing/webhook
  ```

---

## ☑️ MONITORING & LOGGING

### 8. Setup Monitoring

- [ ] **Access Grafana**
  - URL: http://localhost:3001
  - Login: admin / (your new password)
  - Import dashboards from `deployments/grafana/dashboards/`

- [ ] **Access Prometheus**
  - URL: http://localhost:9090
  - Verify targets are up
  - Check for scrape errors

- [ ] **Review logs**
  ```bash
  docker-compose logs --tail=100 api
  docker-compose logs --tail=100 worker
  docker-compose logs --tail=100 web
  ```

---

## ☑️ PRODUCTION DEPLOYMENT

### 9. Production Checklist

- [ ] **Configure domain DNS**
  - [ ] A record: winu.app → Your server IP
  - [ ] A record: api.winu.app → Your server IP
  - [ ] A record: dashboard.winu.app → Your server IP

- [ ] **SSL/TLS Certificates**
  - [ ] Traefik will auto-generate via Let's Encrypt
  - [ ] Verify ACME email is set in production.env
  - [ ] Wait for certificates to be issued (~5 minutes)

- [ ] **Firewall rules**
  ```bash
  # Open required ports
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw allow 3005/tcp  # If accessing directly
  sudo ufw enable
  ```

- [ ] **Backup strategy**
  ```bash
  # Database backups
  pg_dump -U winu winudb > backup_$(date +%Y%m%d).sql
  
  # Schedule daily backups
  crontab -e
  # Add: 0 2 * * * pg_dump -U winu winudb > /backups/winudb_$(date +\%Y\%m\%d).sql
  ```

---

## ☑️ POST-DEPLOYMENT

### 10. Final Verification

- [ ] **Verify HTTPS is working**
  ```bash
  curl https://winu.app
  curl https://api.winu.app/health
  ```

- [ ] **Test from external network**
  - Try accessing from your phone (not on same network)
  - Verify login works
  - Check signal generation

- [ ] **Monitor for 24 hours**
  - Check error logs every 2-4 hours
  - Monitor resource usage
  - Verify trading signals are generating

- [ ] **Security scan** (optional but recommended)
  ```bash
  # Using nikto
  nikto -h https://api.winu.app
  
  # Or use online tools like:
  # - https://observatory.mozilla.org/
  # - https://securityheaders.com/
  ```

---

## ☑️ MAINTENANCE

### 11. Ongoing Tasks

- [ ] **Weekly tasks**
  - Review error logs
  - Check disk usage
  - Verify backups are working

- [ ] **Monthly tasks**
  - Update dependencies
  - Review security advisories
  - Rotate non-critical API keys

- [ ] **Quarterly tasks**
  - Full security audit
  - Performance optimization review
  - User access review

---

## 📞 EMERGENCY CONTACTS

### If Something Goes Wrong:

1. **Check logs immediately**
   ```bash
   docker-compose logs --tail=500 --follow
   ```

2. **Rollback if needed**
   ```bash
   git checkout previous-stable-tag
   docker-compose down
   docker-compose up -d --build
   ```

3. **Monitor service health**
   ```bash
   watch -n 5 'docker-compose ps'
   ```

---

## ✅ COMPLETION

- [ ] All critical security tasks completed
- [ ] All credentials rotated
- [ ] Services running and healthy
- [ ] Monitoring configured
- [ ] Backups scheduled
- [ ] Team notified of deployment

**Deployment Date**: _____________  
**Deployed By**: _____________  
**Next Review Date**: _____________

---

**Last Updated**: October 1, 2025



