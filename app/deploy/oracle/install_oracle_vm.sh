#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/weedverso/app"
SERVICE_NAME="weedverso"
REPO_URL="${1:-}"

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root: sudo bash deploy/oracle/install_oracle_vm.sh <repo-url>"
  exit 1
fi

dnf install -y git python3 unzip

if ! id -u weedverso >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /opt/weedverso --shell /sbin/nologin weedverso
fi

mkdir -p /opt/weedverso

if [[ -n "$REPO_URL" ]]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
else
  echo "Nenhum repo passado. Copie o projeto manualmente para $APP_DIR."
  mkdir -p "$APP_DIR"
fi

chown -R weedverso:weedverso /opt/weedverso

if [[ ! -f "$APP_DIR/.env" && -f "$APP_DIR/deploy/oracle/.env.oracle.example" ]]; then
  cp "$APP_DIR/deploy/oracle/.env.oracle.example" "$APP_DIR/.env"
  chown weedverso:weedverso "$APP_DIR/.env"
fi

cp "$APP_DIR/deploy/oracle/weedverso.service" "/etc/systemd/system/${SERVICE_NAME}.service"

if command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --permanent --add-port=8765/tcp || true
  firewall-cmd --reload || true
fi

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "Instalacao base concluida."
echo "1. Edite $APP_DIR/.env"
echo "2. Rode: systemctl restart ${SERVICE_NAME}"
echo "3. Verifique: systemctl status ${SERVICE_NAME} --no-pager"
