# Guinée Academy - Backup Configuration Guide

## Overview

Automated daily PostgreSQL backups with 30-day retention, integrity verification, and failure alerting.

## Installation

### 1. Make Script Executable

```bash
chmod +x scripts/backup-database.sh
```

### 2. Configure Environment Variables

Create `/etc/guinee_academy/backup.env`:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-secure-password

# Backup Configuration
BACKUP_DIR=/var/backups/guinee_academy
RETENTION_DAYS=30

# Alert Configuration
ALERT_EMAIL=admin@guinee-academy.com
ALERT_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. Create Backup Directory

```bash
sudo mkdir -p /var/backups/guinee_academy
sudo chown postgres:postgres /var/backups/guinee_academy
sudo chmod 750 /var/backups/guinee_academy
```

### 4. Setup Cron Job

Add to crontab (as postgres user or root):

```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 2:00 AM
0 2 * * * /usr/bin/env bash -c 'source /etc/guinee_academy/backup.env && /path/to/guinee-academy/scripts/backup-database.sh >> /var/log/guinee_academy-backup.log 2>&1'
```

**Alternative: Using systemd timer (recommended for production)**

Create `/etc/systemd/system/guinee_academy-backup.service`:

```ini
[Unit]
Description=Guinée Academy Database Backup
After=postgresql.service

[Service]
Type=oneshot
User=postgres
EnvironmentFile=/etc/guinee_academy/backup.env
ExecStart=/path/to/guinee-academy/scripts/backup-database.sh
StandardOutput=append:/var/log/guinee_academy-backup.log
StandardError=append:/var/log/guinee_academy-backup.log
```

Create `/etc/systemd/system/guinee_academy-backup.timer`:

```ini
[Unit]
Description=Guinée Academy Daily Backup Timer
Requires=guinee_academy-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable guinee_academy-backup.timer
sudo systemctl start guinee_academy-backup.timer

# Check timer status
sudo systemctl status guinee_academy-backup.timer
sudo systemctl list-timers --all
```

## Manual Backup

Run backup manually:

```bash
# With environment file
source /etc/guinee_academy/backup.env
./scripts/backup-database.sh

# Or with inline variables
DB_HOST=localhost DB_NAME=postgres DB_USER=postgres DB_PASSWORD=yourpass ./scripts/backup-database.sh
```

## Restore from Backup

### Full Restore

```bash
# 1. Stop application
docker compose down

# 2. Restore database
gunzip -c /var/backups/guinee_academy/guinee_academy_backup_YYYYMMDD_HHMMSS.sql.gz | \
    docker exec -i guinee-academy-supabase-db-1 psql -U postgres -d postgres

# 3. Restart application
docker compose up -d
```

### Restore to Test Database

```bash
# Create test database
docker exec -i guinee-academy-supabase-db-1 psql -U postgres -c "CREATE DATABASE guinee_academy_test;"

# Restore backup
gunzip -c /var/backups/guinee_academy/guinee_academy_backup_YYYYMMDD_HHMMSS.sql.gz | \
    docker exec -i guinee-academy-supabase-db-1 psql -U postgres -d guinee_academy_test

# Verify data
docker exec -i guinee-academy-supabase-db-1 psql -U postgres -d guinee_academy_test -c "\dt"

# Drop test database when done
docker exec -i guinee-academy-supabase-db-1 psql -U postgres -c "DROP DATABASE guinee_academy_test;"
```

## Monitoring

### Check Backup Logs

```bash
# View recent backups
tail -f /var/log/guinee_academy-backup.log

# Check backup success
grep "✅ Backup completed" /var/log/guinee_academy-backup.log

# Check for errors
grep "❌" /var/log/guinee_academy-backup.log
```

### List Backups

```bash
ls -lh /var/backups/guinee_academy/

# Count backups
ls -1 /var/backups/guinee_academy/guinee_academy_backup_*.sql.gz | wc -l

# Show oldest and newest
ls -lt /var/backups/guinee_academy/guinee_academy_backup_*.sql.gz | tail -1
ls -lt /var/backups/guinee_academy/guinee_academy_backup_*.sql.gz | head -1
```

### Disk Space

```bash
# Check backup directory size
du -sh /var/backups/guinee_academy/

# Check available space
df -h /var/backups/guinee_academy/
```

## Alerting

### Email Alerts

Requires `mailx` or `sendmail`:

```bash
# Install mailx (Ubuntu/Debian)
sudo apt-get install mailutils

# Test email
echo "Test backup alert" | mail -s "Guinée Academy Backup Test" admin@guinee-academy.com
```

### Slack/Discord Webhook

Configure webhook URL in `/etc/guinee_academy/backup.env`:

```bash
ALERT_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Test webhook:

```bash
curl -X POST "$ALERT_WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d '{"text": "Guinée Academy Backup Test"}'
```

## Backup Retention Policy

| Data Type | Retention Period | Legal Basis |
|-----------|------------------|-------------|
| **Database Backups** | 30 days | Operational continuity |
| **Invoices/Payments** | 10 years | Code de commerce Art. L123-22 |
| **Academic Records** | Permanent | Code de l'éducation Art. D211-10 |
| **Audit Logs** | 5 years | RGPD Article 5(2) |

## Troubleshooting

### Backup Fails - Disk Space

```bash
# Check disk space
df -h /var/backups/guinee_academy/

# Clean old backups manually
find /var/backups/guinee_academy/ -name "guinee_academy_backup_*.sql.gz" -mtime +30 -delete

# Increase retention period if needed
# Edit /etc/guinee_academy/backup.env
RETENTION_DAYS=15  # Reduce from 30 to 15 days
```

### Backup Fails - Permission Denied

```bash
# Fix permissions
sudo chown -R postgres:postgres /var/backups/guinee_academy/
sudo chmod 750 /var/backups/guinee_academy/
```

### Backup Fails - Connection Refused

```bash
# Check PostgreSQL is running
docker ps | grep supabase-db

# Check connection
docker exec -i guinee-academy-supabase-db-1 psql -U postgres -c "SELECT version();"

# Verify credentials in /etc/guinee_academy/backup.env
```

### Restore Fails - Integrity Check

```bash
# Verify backup file integrity
gunzip -t /var/backups/guinee_academy/guinee_academy_backup_YYYYMMDD_HHMMSS.sql.gz

# If corrupted, use previous backup
ls -lt /var/backups/guinee_academy/guinee_academy_backup_*.sql.gz
```

## Security Best Practices

1. **Encrypt Backups** (for off-site storage):
   ```bash
   # Encrypt backup
   gpg --symmetric --cipher-algo AES256 guinee_academy_backup_YYYYMMDD_HHMMSS.sql.gz
   
   # Decrypt backup
   gpg --decrypt guinee_academy_backup_YYYYMMDD_HHMMSS.sql.gz.gpg > backup.sql.gz
   ```

2. **Restrict Permissions**:
   ```bash
   chmod 600 /etc/guinee_academy/backup.env
   chmod 750 /var/backups/guinee_academy/
   chmod 640 /var/backups/guinee_academy/*.sql.gz
   ```

3. **Off-site Backups**:
   ```bash
   # Sync to remote server (rsync)
   rsync -avz --delete /var/backups/guinee_academy/ backup-server:/backups/guinee_academy/
   
   # Or upload to S3
   aws s3 sync /var/backups/guinee_academy/ s3://guinee_academy-backups/
   ```

## Performance Optimization

### Parallel Compression

For large databases (>10GB), use parallel compression:

```bash
# Install pigz (parallel gzip)
sudo apt-get install pigz

# Modify backup script to use pigz instead of gzip
pg_dump ... | pigz -p 4 > backup.sql.gz  # Use 4 CPU cores
```

### Incremental Backups

For very large databases, consider WAL archiving:

```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /var/backups/guinee_academy/wal/%f'
```

## Next Steps

1. ✅ Install and configure backup script
2. ✅ Setup cron job or systemd timer
3. ✅ Configure email/webhook alerts
4. ✅ Test manual backup
5. ✅ Test restore procedure
6. ⏳ Setup off-site backup sync (optional)
7. ⏳ Configure monitoring dashboard (optional)
