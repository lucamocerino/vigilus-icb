#!/bin/sh
# Backup PostgreSQL — eseguire via crontab ogni 6 ore
# 0 */6 * * * /app/infra/backup.sh

BACKUP_DIR="${BACKUP_DIR:-/backups}"
DB_HOST="${DB_HOST:-db}"
DB_NAME="${DB_NAME:-sentinella}"
DB_USER="${DB_USER:-postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="sentinella_${TIMESTAMP}.sql.gz"

echo "[backup] Avvio backup $DB_NAME → $FILENAME"

PGPASSWORD="${DB_PASSWORD}" pg_dump \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --no-acl \
  | gzip > "$BACKUP_DIR/$FILENAME"

if [ $? -eq 0 ]; then
  SIZE=$(du -sh "$BACKUP_DIR/$FILENAME" | cut -f1)
  echo "[backup] Completato: $FILENAME ($SIZE)"
else
  echo "[backup] ERRORE durante il backup"
  exit 1
fi

# Pulizia backup vecchi
find "$BACKUP_DIR" -name "sentinella_*.sql.gz" -mtime +$RETENTION_DAYS -delete
REMAINING=$(ls "$BACKUP_DIR"/sentinella_*.sql.gz 2>/dev/null | wc -l)
echo "[backup] Backup attivi: $REMAINING (retention: ${RETENTION_DAYS}gg)"
