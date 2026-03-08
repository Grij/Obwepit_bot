#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <path_to_backup_file>"
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "Backup file $1 not found."
    exit 1
fi

echo "Restoring database from $1..."
cp "$1" db.sqlite3
echo "Restore complete."
