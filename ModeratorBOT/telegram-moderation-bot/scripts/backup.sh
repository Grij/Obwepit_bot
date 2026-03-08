#!/bin/bash
set -e

BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sqlite3"

if [ -f "db.sqlite3" ]; then
    sqlite3 db.sqlite3 ".backup '$BACKUP_FILE'"
    echo "Backup created at $BACKUP_FILE"
else
    echo "db.sqlite3 not found. Nothing to backup."
fi
