#!/bin/bash
##############################################################################
# WinuBot Database Backup to Storj
# Automatically backs up PostgreSQL database to Storj decentralized storage
##############################################################################

set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/postgresql"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="winubot_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
LOG_FILE="/var/log/winu_backup.log"

# Discord webhook for notifications
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1425290353992532028/YjgFYIiir_cHf04Es12Ah2VxgTIcCRqj2wz7JsKcc6CqhWdAJABDdw_KVbxtDrEaxIOu"

# Load Storj credentials
source /home/ubuntu/winubotsignal/.storj_credentials

# Database configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="winudb"
DB_USER="winu"
DB_PASSWORD="winu250420"

# Retention settings
LOCAL_RETENTION_DAYS=3
STORJ_RETENTION_DAYS=60

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Send Discord notification
send_discord_alert() {
    local title="$1"
    local message="$2"
    local severity="$3"  # SUCCESS, WARNING, ERROR
    local fields="$4"
    
    local color
    case "$severity" in
        SUCCESS) color=65280 ;;  # Green
        WARNING) color=16776960 ;;  # Yellow
        ERROR) color=16711680 ;;  # Red
        *) color=3447003 ;;  # Blue
    esac
    
    local icon
    case "$severity" in
        SUCCESS) icon="✅" ;;
        WARNING) icon="⚠️" ;;
        ERROR) icon="🚨" ;;
        *) icon="ℹ️" ;;
    esac
    
    local payload=$(cat <<EOF
{
  "username": "WinuBot Backup",
  "embeds": [{
    "title": "${icon} ${title}",
    "description": "${message}",
    "color": ${color},
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "footer": {
      "text": "Database Backup System"
    }
    ${fields}
  }]
}
EOF
    )
    
    curl -s -H "Content-Type: application/json" -d "$payload" "$DISCORD_WEBHOOK_URL" > /dev/null 2>&1
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log "==========================================="
log "Starting database backup process"
log "==========================================="

# Start time
START_TIME=$(date +%s)

# Step 1: Create PostgreSQL dump
log "Step 1/5: Creating database dump..."
if docker exec winu-bot-signal-postgres pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_PATH"; then
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    log "✅ Database dump created successfully: $BACKUP_SIZE"
else
    log "❌ Failed to create database dump"
    send_discord_alert \
        "Database Backup Failed" \
        "Failed to create PostgreSQL dump\n**Time**: $(date '+%Y-%m-%d %H:%M:%S')" \
        "ERROR" \
        ""
    exit 1
fi

# Step 2: Upload to Storj
log "Step 2/5: Uploading to Storj..."
UPLOAD_START=$(date +%s)

if AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
   AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
   aws s3 cp "$BACKUP_PATH" "s3://${STORJ_BUCKET}/${BACKUP_FILE}" \
   --endpoint-url "$STORJ_ENDPOINT" > /dev/null 2>&1; then
    
    UPLOAD_END=$(date +%s)
    UPLOAD_DURATION=$((UPLOAD_END - UPLOAD_START))
    log "✅ Successfully uploaded to Storj in ${UPLOAD_DURATION}s"
else
    log "❌ Failed to upload to Storj"
    send_discord_alert \
        "Storj Upload Failed" \
        "Database backup created but failed to upload to Storj\n**File**: $BACKUP_FILE\n**Size**: $BACKUP_SIZE" \
        "ERROR" \
        ""
    exit 1
fi

# Step 3: Verify upload
log "Step 3/5: Verifying backup..."
if AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
   AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
   aws s3 ls "s3://${STORJ_BUCKET}/${BACKUP_FILE}" \
   --endpoint-url "$STORJ_ENDPOINT" > /dev/null 2>&1; then
    log "✅ Backup verified on Storj"
else
    log "⚠️ Warning: Could not verify backup on Storj"
fi

# Step 4: Clean up old local backups
log "Step 4/5: Cleaning up old local backups (keeping last ${LOCAL_RETENTION_DAYS} days)..."
find "$BACKUP_DIR" -name "winubot_backup_*.sql.gz" -type f -mtime +$LOCAL_RETENTION_DAYS -delete
LOCAL_BACKUP_COUNT=$(find "$BACKUP_DIR" -name "winubot_backup_*.sql.gz" -type f | wc -l)
log "✅ Local backups: $LOCAL_BACKUP_COUNT files"

# Step 5: Clean up old Storj backups
log "Step 5/5: Cleaning up old Storj backups (keeping last ${STORJ_RETENTION_DAYS} days)..."
CUTOFF_DATE=$(date -d "${STORJ_RETENTION_DAYS} days ago" +%Y%m%d)

AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
aws s3 ls "s3://${STORJ_BUCKET}/" --endpoint-url "$STORJ_ENDPOINT" | \
while read -r line; do
    BACKUP_DATE=$(echo "$line" | grep -oP 'winubot_backup_\K[0-9]{8}' || true)
    if [ -n "$BACKUP_DATE" ] && [ "$BACKUP_DATE" -lt "$CUTOFF_DATE" ]; then
        BACKUP_NAME=$(echo "$line" | awk '{print $4}')
        log "Deleting old backup: $BACKUP_NAME"
        AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
        AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
        aws s3 rm "s3://${STORJ_BUCKET}/${BACKUP_NAME}" --endpoint-url "$STORJ_ENDPOINT" > /dev/null 2>&1
    fi
done

# Get Storj backup count
STORJ_BACKUP_COUNT=$(AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
aws s3 ls "s3://${STORJ_BUCKET}/" --endpoint-url "$STORJ_ENDPOINT" | grep "winubot_backup_" | wc -l)

# Calculate total Storj usage
STORJ_USAGE=$(AWS_ACCESS_KEY_ID="$STORJ_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$STORJ_SECRET_KEY" \
aws s3 ls "s3://${STORJ_BUCKET}/" --endpoint-url "$STORJ_ENDPOINT" --recursive --summarize | grep "Total Size" | awk '{print $3}' || echo "0")

if [ "$STORJ_USAGE" -gt 0 ]; then
    STORJ_USAGE_MB=$((STORJ_USAGE / 1024 / 1024))
else
    STORJ_USAGE_MB=0
fi

log "✅ Storj backups: $STORJ_BACKUP_COUNT files (${STORJ_USAGE_MB} MB)"

# End time and duration
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

log "==========================================="
log "Backup completed successfully in ${TOTAL_DURATION}s"
log "==========================================="

# Calculate next backup time
NEXT_BACKUP=$(date -d "tomorrow 02:00" '+%Y-%m-%d %H:%M:%S')

# Send success notification to Discord
send_discord_alert \
    "Database Backup Completed" \
    "✅ **Backup successful!**\n\nDatabase backed up to Storj decentralized storage." \
    "SUCCESS" \
    ",
    \"fields\": [
      {\"name\": \"📦 Backup File\", \"value\": \"\`${BACKUP_FILE}\`\", \"inline\": false},
      {\"name\": \"💾 Backup Size\", \"value\": \"${BACKUP_SIZE}\", \"inline\": true},
      {\"name\": \"⏱️ Duration\", \"value\": \"${TOTAL_DURATION}s (Upload: ${UPLOAD_DURATION}s)\", \"inline\": true},
      {\"name\": \"📊 Local Backups\", \"value\": \"${LOCAL_BACKUP_COUNT} files (last ${LOCAL_RETENTION_DAYS} days)\", \"inline\": true},
      {\"name\": \"☁️ Storj Backups\", \"value\": \"${STORJ_BACKUP_COUNT} files (${STORJ_USAGE_MB} MB total)\", \"inline\": true},
      {\"name\": \"🔄 Next Backup\", \"value\": \"${NEXT_BACKUP}\", \"inline\": true},
      {\"name\": \"📍 Location\", \"value\": \"Storj Bucket: \`${STORJ_BUCKET}\`\", \"inline\": false}
    ]"

log "📧 Discord notification sent"

exit 0





