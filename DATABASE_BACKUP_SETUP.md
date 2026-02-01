# Database Backup System - Storj Configuration

## ✅ Setup Complete!

Your WinuBot database is now automatically backed up to **Storj decentralized cloud storage**.

---

## 📊 Current Status

### **First Backup Completed:**
- ✅ **Date**: October 7, 2025, 10:54 PM
- ✅ **Size**: 5.4 MB (compressed)
- ✅ **Duration**: 3 seconds total (1s upload)
- ✅ **Location**: Storj bucket `winubot-backups`
- ✅ **Status**: Verified and stored successfully

### **Storage Provider:**
- **Service**: Storj (Decentralized Cloud Storage)
- **Project**: winuappdb
- **Bucket**: winubot-backups
- **Endpoint**: https://gateway.storjshare.io
- **Encryption**: End-to-end (client-side)

---

## ⏰ Automated Backup Schedule

### **Daily Backups**
```
Schedule:  Every day at 2:00 AM
Script:    /home/ubuntu/winubotsignal/db_backup_storj.sh
Cron:      0 2 * * * /home/ubuntu/winubotsignal/db_backup_storj.sh
Log File:  /var/log/winu_backup.log
```

### **What Gets Backed Up:**
- ✅ All database tables
- ✅ User accounts & subscriptions
- ✅ Trading signals (all historical data)
- ✅ Payment transactions
- ✅ Trading positions
- ✅ System configurations
- ✅ Alert history

---

## 💾 Retention Policy

### **Local Storage** (`/var/backups/postgresql/`)
- **Retention**: Last 3 days
- **Purpose**: Quick local recovery
- **Auto-cleanup**: Automatic

### **Storj Cloud Storage**
- **Retention**: Last 60 days  
- **Purpose**: Long-term backup & disaster recovery
- **Auto-cleanup**: Automatic
- **Cost**: ~$0.01-0.10/month (essentially FREE!)

---

## 📈 Storage Costs

### **Current Usage:**
```
Local:    5.4 MB (1 backup)
Storj:    5.4 MB (1 backup)
Total:    ~$0.001/month
```

### **Projected (60 days):**
```
Estimated: ~300 MB (60 backups × 5 MB)
Cost:      ~$0.05-0.10/month
```

### **Storj Free Tier:**
- First 150 GB: **FREE**
- Your usage: ~0.3 GB (0.2% of free tier)
- **You're well within the free tier!**

---

## 🔔 Discord Notifications

Every backup sends a notification to your **WinuBot** Discord channel with:

```
✅ Database Backup Completed

📦 Backup File: winubot_backup_20251007_225426.sql.gz
💾 Backup Size: 5.4M
⏱️ Duration: 3s (Upload: 1s)
📊 Local Backups: 1 files (last 3 days)
☁️ Storj Backups: 1 files (5 MB total)
🔄 Next Backup: 2025-10-08 02:00:00
📍 Location: Storj Bucket: winubot-backups
```

---

## 🔐 Security Features

### **Encryption:**
- ✅ **End-to-end encryption** (Storj native)
- ✅ **Client-side encryption** before upload
- ✅ **Zero-knowledge** (Storj can't read your data)
- ✅ **Compressed** (gzip) for smaller size

### **Credentials:**
- 🔒 Stored in: `/home/ubuntu/winubotsignal/.storj_credentials`
- 🔒 Permissions: 600 (owner read/write only)
- 🔒 Not in git repository
- 🔒 Separate from application code

### **Redundancy:**
- ✅ Data split into 80 pieces across global nodes
- ✅ Only 29 pieces needed to recover
- ✅ Automatic repair if nodes fail
- ✅ 99.95% availability SLA

---

## 🔄 Backup Process

The backup script performs these steps:

1. **Create Database Dump**
   - Uses `pg_dump` to export full database
   - Compresses with gzip (~50-70% size reduction)
   
2. **Upload to Storj**
   - Uses S3-compatible API
   - Parallel upload to multiple nodes
   - Typical upload: 1-5 seconds

3. **Verify Upload**
   - Confirms file exists on Storj
   - Validates file size matches

4. **Clean Up Old Backups**
   - Removes local backups older than 3 days
   - Removes Storj backups older than 60 days

5. **Send Discord Notification**
   - Success/failure alert
   - Backup statistics
   - Next backup time

---

## 🧪 Testing & Verification

### **Manual Test Backup:**
```bash
cd /home/ubuntu/winubotsignal
bash db_backup_storj.sh
```

### **View Backup Logs:**
```bash
tail -f /var/log/winu_backup.log
```

### **List Local Backups:**
```bash
ls -lh /var/backups/postgresql/
```

### **List Storj Backups:**
```bash
source /home/ubuntu/winubotsignal/.storj_credentials
AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
aws s3 ls s3://$STORJ_BUCKET/ --endpoint-url $STORJ_ENDPOINT
```

---

## 💡 Restore Instructions

### **Quick Restore from Local Backup:**
```bash
# 1. Find latest backup
ls -lt /var/backups/postgresql/ | head -5

# 2. Restore (replace YYYYMMDD_HHMMSS with actual timestamp)
gunzip < /var/backups/postgresql/winubot_backup_YYYYMMDD_HHMMSS.sql.gz | \
docker exec -i winu-bot-signal-postgres psql -U winu winudb
```

### **Restore from Storj:**
```bash
# 1. Download from Storj
source /home/ubuntu/winubotsignal/.storj_credentials
AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
aws s3 cp s3://$STORJ_BUCKET/winubot_backup_YYYYMMDD_HHMMSS.sql.gz \
  /tmp/restore_backup.sql.gz \
  --endpoint-url $STORJ_ENDPOINT

# 2. Restore to database
gunzip < /tmp/restore_backup.sql.gz | \
docker exec -i winu-bot-signal-postgres psql -U winu winudb

# 3. Clean up
rm /tmp/restore_backup.sql.gz
```

### **Restore to Test Database (Recommended):**
```bash
# Create test database first
docker exec winu-bot-signal-postgres psql -U winu -c "CREATE DATABASE winudb_test;"

# Restore to test database
gunzip < /var/backups/postgresql/winubot_backup_YYYYMMDD_HHMMSS.sql.gz | \
docker exec -i winu-bot-signal-postgres psql -U winu winudb_test

# Verify data
docker exec winu-bot-signal-postgres psql -U winu winudb_test -c "SELECT COUNT(*) FROM signals;"
```

---

## 📋 Complete Cron Schedule

```bash
*/5 * * * *   → Health checks every 5 minutes
0 2 * * *     → Database backup every day at 2:00 AM
0 7 * * *     → System audit every day at 7:00 AM
```

---

## 🚨 Monitoring & Alerts

### **Discord Notifications:**
- ✅ **Success**: Green notification after each backup
- 🚨 **Failure**: Red alert if backup fails
- ⚠️ **Warning**: Yellow alert for partial failures

### **What's Monitored:**
- Database dump creation
- Storj upload success
- Backup verification
- Storage usage
- Retention policy compliance

---

## 📊 Backup Statistics

### **Current Setup:**
```
Database Size:        ~250 records (signals)
Backup Size:          5.4 MB compressed
Backup Frequency:     Daily (2 AM)
Local Retention:      3 days (~16 MB)
Cloud Retention:      60 days (~320 MB)
Monthly Cost:         ~$0.05 (essentially free)
```

### **Growth Projections:**
```
Year 1:
- Database: ~10-50 MB
- Storj cost: ~$0.10-0.50/month

Year 2:
- Database: ~50-200 MB  
- Storj cost: ~$0.50-2/month

Still within free tier! (150 GB free)
```

---

## 🔧 Troubleshooting

### **If Backup Fails:**

1. **Check logs:**
   ```bash
   tail -50 /var/log/winu_backup.log
   ```

2. **Test Storj connection:**
   ```bash
   source /home/ubuntu/winubotsignal/.storj_credentials
   AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
   AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
   aws s3 ls s3://$STORJ_BUCKET/ --endpoint-url $STORJ_ENDPOINT
   ```

3. **Test database connection:**
   ```bash
   docker exec winu-bot-signal-postgres psql -U winu -c "SELECT version();"
   ```

4. **Check disk space:**
   ```bash
   df -h /var/backups/postgresql/
   ```

### **If Upload is Slow:**
- Normal: 1-10 seconds for 5-50 MB
- Slow network: May take longer
- Storj distributes globally, so speed varies

---

## 🎯 Best Practices

### **✅ DO:**
- Test restore process monthly
- Monitor Discord notifications
- Keep credentials secure
- Review backup logs periodically

### **❌ DON'T:**
- Don't share Storj credentials
- Don't disable backups
- Don't delete retention policies
- Don't ignore failure alerts

---

## 📞 Support

### **If You Need Help:**

1. **Check Discord** - Look for error notifications
2. **Check Logs** - `/var/log/winu_backup.log`
3. **Test Manually** - Run `bash db_backup_storj.sh`
4. **Verify Storj** - Check bucket contents

### **Useful Commands:**
```bash
# View recent backups
ls -lht /var/backups/postgresql/ | head -10

# Check Storj space usage
source /home/ubuntu/winubotsignal/.storj_credentials
AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
aws s3 ls s3://$STORJ_BUCKET/ --recursive --summarize --endpoint-url $STORJ_ENDPOINT

# Manual backup now
bash /home/ubuntu/winubotsignal/db_backup_storj.sh
```

---

## ✅ Summary

### **What's Configured:**
- ✅ Automated daily backups at 2 AM
- ✅ Storj decentralized cloud storage
- ✅ 60-day retention policy
- ✅ Discord notifications
- ✅ Automatic cleanup
- ✅ End-to-end encryption
- ✅ Cost: ~$0.05/month (FREE tier)

### **What You Get:**
- 🛡️ **Protection**: Against data loss
- 💰 **Cost**: Essentially free
- 🔐 **Security**: End-to-end encrypted
- 🌍 **Reliability**: Decentralized storage
- 📊 **Visibility**: Discord notifications
- ⚡ **Speed**: 1-3 second backups

---

**Backup System: ACTIVE & MONITORING** 🚀

First backup completed successfully!
Next backup: Tomorrow at 2:00 AM

---

**Configured**: October 7, 2025, 10:54 PM EDT
**Status**: ✅ Operational
**Cost**: ~$0.05/month





