#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: sudo bash deploy/aws/setup_sslip_https.sh HOSTNAME_SSLIP"
  echo "Exemplo: sudo bash deploy/aws/setup_sslip_https.sh 52.14.134.193.sslip.io"
  exit 1
fi

HOSTNAME_SSLIP="$1"
CADDY_VERSION="${CADDY_VERSION:-2.11.2}"
CADDY_URL="${CADDY_URL:-https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz}"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo."
  exit 1
fi

dnf install -y tar

if ! id -u caddy >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/caddy --create-home --shell /sbin/nologin caddy
fi

mkdir -p /etc/caddy /var/lib/caddy /var/log/caddy /usr/local/bin

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

curl -fsSL "$CADDY_URL" -o "$tmpdir/caddy.tar.gz"
tar -xzf "$tmpdir/caddy.tar.gz" -C "$tmpdir"
install -m 0755 "$tmpdir/caddy" /usr/local/bin/caddy
setcap cap_net_bind_service=+ep /usr/local/bin/caddy || true

cat >/etc/caddy/Caddyfile <<EOF
${HOSTNAME_SSLIP} {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8765
}
EOF

cat >/etc/systemd/system/caddy.service <<'EOF'
[Unit]
Description=Caddy HTTPS Reverse Proxy
After=network-online.target
Wants=network-online.target

[Service]
User=caddy
Group=caddy
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/local/bin/caddy reload --config /etc/caddy/Caddyfile
Restart=always
RestartSec=5
WorkingDirectory=/var/lib/caddy

[Install]
WantedBy=multi-user.target
EOF

chown -R caddy:caddy /etc/caddy /var/lib/caddy /var/log/caddy

systemctl daemon-reload
systemctl enable caddy
systemctl restart caddy

echo "Caddy configurado para https://${HOSTNAME_SSLIP}"
echo "Garanta 80/tcp e 443/tcp abertos no Security Group."
