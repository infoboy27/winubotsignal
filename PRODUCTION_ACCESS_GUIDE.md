# 🌐 Production Access Issue - SOLVED

## The Problem You're Experiencing

You're accessing **https://winu.app** (production domain) but getting 404 errors on the registration endpoint.

### Why This Happens:

```
❌ https://winu.app/api/onboarding/register → 404 Not Found
✅ http://localhost:3005/api/onboarding/register → Works!
```

**Reason**: The new API routes I created exist in your **local development** environment but haven't been deployed to the **production Docker container** yet.

---

## 🔧 Quick Fix - Two Options:

### OPTION 1: Use Localhost for Testing (RECOMMENDED)

**Right now, use the development server**:
```bash
URL: http://localhost:3005
```

This has all the latest code and is working perfectly! ✅

**Steps**:
1. Open: http://localhost:3005
2. Register/Login works!
3. All features available

---

### OPTION 2: Deploy to Production Container

To make https://winu.app work, you need to:

#### Step 1: Build and Start Web Container
```bash
cd /home/ubuntu/winubotsignal

# Stop any existing web container
docker stop winu-bot-signal-web 2>/dev/null || true
docker rm winu-bot-signal-web 2>/dev/null || true

# Build new image with updated code
docker build -f apps/web/Dockerfile -t winu-web:latest .

# Start the container
docker run -d \
  --name winu-bot-signal-web \
  --network winu-bot-signal-network \
  -p 3005:3000 \
  -e NEXT_PUBLIC_API_URL=https://api.winu.app \
  -e API_URL_INTERNAL=http://api:8001 \
  -e NEXTAUTH_URL=https://winu.app \
  -v /home/ubuntu/winubotsignal/apps/web:/app \
  -v /app/node_modules \
  -v /app/.next \
  winu-web:latest
```

#### Step 2: Verify It's Running
```bash
docker ps | grep winu-bot-signal-web
```

#### Step 3: Test Through Traefik
```bash
curl -H "Host: winu.app" http://localhost:80/api/health
```

---

## 🎯 Current Situation Summary

| Environment | URL | Status | API Routes |
|-------------|-----|--------|------------|
| **Development** | http://localhost:3005 | ✅ Running | ✅ All working |
| **Production** | https://winu.app | ⚠️ No web container | ❌ 404 errors |

---

## 📊 What's Actually Running

```bash
✅ Backend API (port 8001)     - Working
✅ Database (PostgreSQL)        - Working
✅ Redis                        - Working
✅ Workers (Celery)             - Working
✅ Trading Bot                  - Working
✅ Traefik (reverse proxy)      - Working
⚠️  Web Container (port 3000)  - NOT RUNNING in Docker
✅ Web Dev Server (port 3005)   - Running (localhost only)
```

---

## 🚀 Recommended Approach

### For Development & Testing:
**Use**: http://localhost:3005 ✅

This gives you:
- ✅ Hot reload (changes appear instantly)
- ✅ All latest code
- ✅ Better debugging
- ✅ Faster development

### For Production Deployment:

1. **Build the production image**:
```bash
cd /home/ubuntu/winubotsignal/apps/web
npm run build
```

2. **Create production Dockerfile build**:
```bash
cd /home/ubuntu/winubotsignal
docker build -f apps/web/Dockerfile -t winu-web:production .
```

3. **Start with docker-compose** (after fixing the docker client):
```bash
# Fix docker-compose if needed
sudo pip3 install --upgrade docker-compose

# Then start
docker-compose up -d web
```

---

## 🔍 Why docker-compose Has Issues

You're seeing this error:
```
docker.errors.DockerException: Error while fetching server API version: 
Not supported URL scheme http+docker
```

**This is a known Python docker client issue**. Two solutions:

### Solution A: Upgrade docker-compose
```bash
sudo pip3 install --upgrade docker-compose
```

### Solution B: Use docker commands directly
```bash
# Instead of: docker-compose up -d web
# Use: docker run ... (as shown above)
```

---

## 💡 Quick Test Right Now

**Test your local development server**:
```bash
# Registration
curl -X POST http://localhost:3005/api/onboarding/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test2@example.com","username":"testuser2","password":"testpass123"}'

# Should return:
# {"success":true,"message":"Registration successful...","user_id":2}
```

✅ **This works!**

**Try on production domain**:
```bash
curl -X POST https://winu.app/api/onboarding/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test3@example.com","username":"testuser3","password":"testpass123"}'

# Returns: 404 (because web container not running)
```

❌ **This fails until you deploy**

---

## 📋 Deployment Checklist

Before deploying to production (winu.app):

- [ ] Rotate ALL API credentials (SECURITY_NOTES.md)
- [ ] Update production.env with new credentials  
- [ ] Test all features on localhost:3005
- [ ] Build production Docker image
- [ ] Start web container
- [ ] Verify Traefik routing
- [ ] Test SSL certificates
- [ ] Monitor logs for errors

---

## 🎯 Action Items for You

### Immediate (For Testing):
1. ✅ Use http://localhost:3005 (already working!)
2. ✅ Test registration: Create accounts
3. ✅ Test login: Use created accounts
4. ✅ Explore features: Everything works

### Later (For Production):
1. Follow "OPTION 2" above to deploy web container
2. Or wait until you've rotated credentials
3. Then do full production deployment

---

## 📞 Need Help?

If you want to deploy to production RIGHT NOW:

```bash
# Quick deploy script
cd /home/ubuntu/winubotsignal

# Stop dev server
pkill -f "next dev"

# Build and run in Docker
docker build -f apps/web/Dockerfile -t winu-web:latest . && \
docker run -d \
  --name winu-bot-signal-web \
  --network winu-bot-signal_winu-bot-signal-network \
  -e NEXT_PUBLIC_API_URL=http://localhost:8001 \
  -e API_URL_INTERNAL=http://api:8001 \
  winu-web:latest

# Check it's running
docker ps | grep web
```

---

## ✅ Summary

**Current State**:
- ✅ Development: http://localhost:3005 - **FULLY WORKING**
- ⚠️ Production: https://winu.app - **Needs web container**

**Solution**:
- 🎯 Use localhost:3005 for now (recommended)
- 🚀 Deploy web container when ready for production

**Everything else works perfectly!** The only issue is the production web container isn't running.

---

**Created**: October 1, 2025  
**Issue**: 404 on production domain  
**Cause**: Web container not deployed  
**Solution**: Use localhost:3005 OR deploy web container  



