# PostgreSQL Backups

> Last updated: 2026-06-27

## Backup Strategy

| Setting | Value |
| --- | --- |
| Frequency | Daily at 03:00 UTC |
| Retention (daily) | 7 days |
| Retention (weekly) | 4 weeks |
| Encryption | AES-256 |
| Storage | Hetzner Object Storage (off-server) |
| Checksum | SHA-256 |
| Test restore | Monthly |

## Backup Script

```bash
#!/usr/bin/env bash
# /opt/terrabits/scripts/backup-postgres.sh
set -euo pipefail

TIMESTAMP=$(date -u +%Y%m%d_%H%M%SZ)
BACKUP_DIR="/opt/terrabits/backups/postgres"
S3_ENDPOINT="${S3_ENDPOINT:-}"
S3_BUCKET="${S3_BUCKET:-}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-}"
S3_SECRET_KEY="${S3_SECRET_KEY:-}"
DB_CONTAINER="pulse-of-earth-db-1"
DB_NAME="pulse"
DB_USER="pulse"

mkdir -p "$BACKUP_DIR"

# Dump
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

# Encrypt
openssl enc -aes-256-cbc -salt -in "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz" \
  -out "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz.enc" \
  -pass pass:"${BACKUP_ENCRYPTION_KEY:-}"

# Checksum
sha256sum "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz.enc" > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sha256"

# Upload to Object Storage
if [ -n "$S3_ENDPOINT" ]; then
  aws s3 cp "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz.enc" \
    "s3://${S3_BUCKET}/backups/postgres/" \
    --endpoint-url="$S3_ENDPOINT" --quiet
fi

# Cleanup old backups (keep 7 days)
find "$BACKUP_DIR" -name "*.sql.gz*" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.sha256" -mtime +7 -delete

echo "Backup completed: ${DB_NAME}_${TIMESTAMP}.sql.gz.enc"
```

## Restore Script

```bash
#!/usr/bin/env bash
# /opt/terrabits/scripts/restore-postgres.sh
set -euo pipefail

BACKUP_FILE="${1:?Usage: $0 <backup-file>}"
DB_CONTAINER="pulse-of-earth-db-1"
DB_NAME="pulse"
DB_USER="pulse"

# Decrypt
DECRYPTED="${BACKUP_FILE%.enc}"
openssl enc -aes-256-cbc -d -in "$BACKUP_FILE" -out "$DECRYPTED" \
  -pass pass:"${BACKUP_ENCRYPTION_KEY:-}"

# Decompress
SQL_FILE="${DECRYPTED%.gz}"
gunzip -f "$DECRYPTED"

# Restore
docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME" < "$SQL_FILE"

echo "Restore completed from: $BACKUP_FILE"
```

## Verify Script

```bash
#!/usr/bin/env bash
# /opt/terrabits/scripts/verify-backup.sh
set -euo pipefail

BACKUP_DIR="/opt/terrabits/backups/postgres"
LATEST=$(ls -t "$BACKUP_DIR"/*.sha256 2>/dev/null | head -n1)

if [ -z "$LATEST" ]; then
  echo "ERROR: No backup found"
  exit 1
fi

# Verify checksum
cd "$BACKUP_DIR"
sha256sum -c "$LATEST"

# Check backup age
BACKUP_AGE=$(( ($(date +%s) - $(stat -c %Y "${LATEST%.sha256}")) / 3600 ))
if [ "$BACKUP_AGE" -gt 25 ]; then
  echo "WARNING: Latest backup is ${BACKUP_AGE}h old"
  exit 1
fi

echo "Backup verified: ${LATEST}"
```

## Required Secrets

| Secret | Purpose |
| --- | --- |
| S3_ENDPOINT | Hetzner Object Storage URL |
| S3_BUCKET | Bucket name |
| S3_ACCESS_KEY | Access key |
| S3_SECRET_KEY | Secret key |
| BACKUP_ENCRYPTION_KEY | Encryption passphrase |

## Owner Actions Required

1. Create Hetzner Object Storage bucket
2. Provide S3 credentials
3. Provide encryption key
4. Approve backup schedule
