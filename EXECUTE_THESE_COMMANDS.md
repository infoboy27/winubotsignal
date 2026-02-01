# 🚀 Execute These Commands to Fix Traefik Routing

## **Step-by-Step Commands to Run:**

### **1. Stop Direct Dashboard Process**
```bash
pkill -f "dashboard/app.py"
```

### **2. Stop Existing Docker Container**
```bash
docker stop winu-bot-signal-bot-dashboard
docker rm winu-bot-signal-bot-dashboard
```

### **3. Build Dashboard Image**
```bash
docker build -t winu-bot-dashboard ./bot
```

### **4. Start Bot Dashboard with Traefik**
```bash
docker-compose up -d bot-dashboard
```

### **5. Check Container Status**
```bash
docker ps | grep bot-dashboard
```

### **6. Check Container Logs**
```bash
docker logs winu-bot-signal-bot-dashboard
```

### **7. Check Traefik Logs**
```bash
docker logs winu-bot-signal-traefik | tail -20
```

## **🎯 Expected Results:**

After running these commands:
- ✅ Bot dashboard container should be running
- ✅ `https://bot.winu.app` should work
- ✅ You should see the dual trading dashboard

## **🔍 Troubleshooting:**

### **If Container Fails to Start:**
```bash
docker logs winu-bot-signal-bot-dashboard
```

### **If Still 404:**
```bash
# Check if Traefik is routing correctly
docker logs winu-bot-signal-traefik | grep bot-dashboard

# Check DNS resolution
nslookup bot.winu.app
```

### **If Build Fails:**
```bash
# Check Docker build logs
docker build -t winu-bot-dashboard ./bot --no-cache
```

## **📋 Quick One-Liner (Alternative):**

If you want to run everything at once:
```bash
pkill -f "dashboard/app.py" && docker stop winu-bot-signal-bot-dashboard && docker rm winu-bot-signal-bot-dashboard && docker build -t winu-bot-dashboard ./bot && docker-compose up -d bot-dashboard
```

## **✅ Verification:**

After running the commands, test:
```bash
curl -I https://bot.winu.app
```

Should return HTTP 200 or 302 (not 404).

## **🎉 Success Indicators:**

You'll know it's working when:
- ✅ `docker ps` shows bot-dashboard container running
- ✅ `https://bot.winu.app` loads the login page
- ✅ Login shows dual balance cards (Spot/Futures)
- ✅ Separate position tables for each market type

**Run these commands in order and your dashboard should be accessible via Traefik!** 🚀

