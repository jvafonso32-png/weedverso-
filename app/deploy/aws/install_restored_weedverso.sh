#!/usr/bin/env bash
set -euo pipefail

APP_ARCHIVE="${1:-}"
ENV_FILE="${2:-}"
PUBLIC_HOST="${3:-}"

if [[ -z "$APP_ARCHIVE" || -z "$ENV_FILE" || -z "$PUBLIC_HOST" ]]; then
  echo "Uso: sudo bash install_restored_weedverso.sh APP_ARCHIVE ENV_FILE PUBLIC_HOST"
  exit 1
fi

APP_ROOT="/opt/weedverso"
APP_DIR="$APP_ROOT/app"
RUN_USER="weedverso"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo."
  exit 1
fi

dnf install -y python3 tar

if ! command -v curl >/dev/null 2>&1; then
  echo "curl nao encontrado na instancia."
  exit 1
fi

if ! id -u "$RUN_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_ROOT" --shell /sbin/nologin "$RUN_USER"
fi

mkdir -p "$APP_DIR"
find "$APP_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -xzf "$APP_ARCHIVE" -C "$APP_DIR"
install -m 0600 "$ENV_FILE" "$APP_DIR/.env"

install -m 0644 "$APP_DIR/deploy/oracle/weedverso.service" /etc/systemd/system/weedverso.service
chown -R "$RUN_USER:$RUN_USER" "$APP_ROOT"

systemctl daemon-reload
systemctl enable weedverso
systemctl restart weedverso

for attempt in {1..30}; do
  if curl -fsS "http://127.0.0.1:8765/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS "http://127.0.0.1:8765/health" >/dev/null 2>&1; then
  echo "Weedverso nao respondeu na porta local 8765."
  journalctl -u weedverso -n 80 --no-pager || true
  exit 1
fi

sudo bash "$APP_DIR/deploy/aws/setup_sslip_https.sh" "$PUBLIC_HOST"

sudo -u "$RUN_USER" bash -lc "cd '$APP_DIR' && python3 - <<'PY'
from shared_state import read_state
from share_publish import publish_state

publish = publish_state(read_state(), reason='sync', force=True)
print(publish)
PY"

echo "Weedverso restaurado em https://$PUBLIC_HOST"
