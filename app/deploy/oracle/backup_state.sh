#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/opt/weedverso/app"
BACKUP_DIR="/opt/weedverso/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/weedverso-data-$STAMP.tar.gz" -C "$BASE_DIR" data .env
echo "Backup criado em $BACKUP_DIR/weedverso-data-$STAMP.tar.gz"
