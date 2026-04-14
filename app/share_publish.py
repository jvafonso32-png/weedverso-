import hashlib
import json
import os
import socket
import threading
from datetime import datetime
from urllib import error, parse, request

from env_loader import load_env_file
from telegram_chats import latest_chat_id
from weedverso_paths import persistent_data_root


load_env_file()

DATA_DIR = persistent_data_root()
PUBLISH_FILE = DATA_DIR / "publish_runtime.json"
LOCK = threading.RLock()
TRUTHY = {"1", "true", "on", "yes", "sim"}
ANY_HOSTS = {"0.0.0.0", "::", ""}


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _default_runtime():
    return {
        "version": 0,
        "updatedAt": "",
        "reason": "",
        "stateHash": "",
        "lastLinks": {},
        "notifications": {"telegram": "idle", "discord": "idle"},
    }


def _normalize_runtime(raw_runtime):
    runtime = _default_runtime()
    runtime.update(raw_runtime or {})
    runtime["version"] = max(0, int(runtime.get("version") or 0))
    runtime["updatedAt"] = str(runtime.get("updatedAt") or "")
    runtime["reason"] = str(runtime.get("reason") or "")
    runtime["stateHash"] = str(runtime.get("stateHash") or "")
    runtime["lastLinks"] = dict(runtime.get("lastLinks") or {})
    notifications = dict(runtime.get("notifications") or {})
    runtime["notifications"] = {
        "telegram": str(notifications.get("telegram") or "idle"),
        "discord": str(notifications.get("discord") or "idle"),
    }
    return runtime


def ensure_publish_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PUBLISH_FILE.exists():
        PUBLISH_FILE.write_text(json.dumps(_default_runtime(), ensure_ascii=False, indent=2), encoding="utf-8")


def read_publish_runtime():
    ensure_publish_store()
    with LOCK:
        try:
            raw_runtime = json.loads(PUBLISH_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw_runtime = {}
    return _normalize_runtime(raw_runtime)


def write_publish_runtime(runtime):
    ensure_publish_store()
    normalized = _normalize_runtime(runtime)
    with LOCK:
        PUBLISH_FILE.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def _clean_base_url(url):
    return str(url or "").strip().rstrip("/")


def _configured_host():
    host = str(os.getenv("WEEDVERSO_SHARE_HOST") or "").strip()
    if host:
        return host
    host = str(os.getenv("WEEDVERSO_HOST") or "").strip()
    if host and host not in ANY_HOSTS and host.lower() != "localhost":
        return host
    return ""


def detect_local_host():
    configured = _configured_host()
    if configured:
        return configured
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return "127.0.0.1"


def local_base_url():
    port = int(os.getenv("WEEDVERSO_PORT", "8765"))
    explicit_host = str(os.getenv("WEEDVERSO_SHARE_HOST") or "").strip()
    if explicit_host:
        explicit_host = explicit_host.rstrip("/")
        if explicit_host.startswith("http://") or explicit_host.startswith("https://"):
            return explicit_host
        return f"http://{explicit_host}:{port}"
    if public_base_url():
        return ""
    return f"http://{detect_local_host()}:{port}"


def public_base_url():
    return _clean_base_url(os.getenv("WEEDVERSO_PUBLIC_URL", ""))


def _versioned_link(base_url, version):
    base_url = _clean_base_url(base_url)
    if not base_url:
        return ""
    return f"{base_url}/login?v={version}"


def build_share_links(version):
    links = {
        "local": _versioned_link(local_base_url(), version),
        "public": _versioned_link(public_base_url(), version),
    }
    links["preferred"] = links["public"] or links["local"]
    return links


def current_share_info():
    runtime = read_publish_runtime()
    links = build_share_links(runtime["version"])
    return {
        "version": runtime["version"],
        "updatedAt": runtime["updatedAt"],
        "reason": runtime["reason"],
        "links": links,
        "notifications": dict(runtime["notifications"]),
    }


def _state_hash(state):
    payload = json.dumps(state or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _notify_telegram(message):
    token = str(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        return "unconfigured"
    chat_id = str(os.getenv("WEEDVERSO_NOTIFY_CHAT_ID") or "").strip() or str(latest_chat_id() or "").strip()
    if not chat_id:
        return "no_chat"
    data = parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        return "sent" if body.get("ok") else "failed"
    except Exception:
        return "failed"


def _notify_discord(message):
    webhook = str(os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
    if not webhook:
        return "unconfigured"
    payload = json.dumps({"content": message}, ensure_ascii=False).encode("utf-8")
    req = request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=20) as response:
            return "sent" if 200 <= response.status < 300 else "failed"
    except error.HTTPError as exc:
        return "sent" if 200 <= exc.code < 300 else "failed"
    except Exception:
        return "failed"


def _publish_message(version, reason, links):
    label_map = {
        "manual": "salvamento manual",
        "close": "fechamento da sessao",
        "autosave": "salvamento automatico",
        "sync": "sincronizacao",
    }
    reason_label = label_map.get(str(reason or "").strip().lower(), str(reason or "salvamento"))
    lines = [
        "weedverso | dados sincronizados",
        f"Versao do link: v{version}",
        f"Motivo: {reason_label}",
        f"Atualizado em: {_now_iso()}",
    ]
    if links.get("local"):
        lines.append(f"Link local: {links['local']}")
    if links.get("public"):
        lines.append(f"Link publico: {links['public']}")
    if links.get("local") and not links.get("public"):
        lines.append("Esse link local funciona com o Weedverso aberto neste PC e na mesma rede.")
    return "\n".join(lines)


def publish_state(state, reason="manual", force=False):
    runtime = read_publish_runtime()
    snapshot_hash = _state_hash(state)
    changed = snapshot_hash != runtime["stateHash"]
    should_publish = bool(force or changed or runtime["version"] <= 0)
    version = runtime["version"]
    notifications = dict(runtime["notifications"])

    if should_publish:
        version += 1
        links = build_share_links(version)
        message = _publish_message(version, reason, links)
        notifications = {
            "telegram": _notify_telegram(message),
            "discord": _notify_discord(message),
        }
        runtime = write_publish_runtime(
            {
                "version": version,
                "updatedAt": _now_iso(),
                "reason": str(reason or ""),
                "stateHash": snapshot_hash,
                "lastLinks": links,
                "notifications": notifications,
            }
        )
    else:
        links = build_share_links(version)
        runtime["lastLinks"] = links

    return {
        "published": should_publish,
        "changed": changed,
        "version": runtime["version"],
        "updatedAt": runtime["updatedAt"],
        "reason": runtime["reason"],
        "links": dict(runtime.get("lastLinks") or build_share_links(runtime["version"])),
        "notifications": dict(runtime["notifications"]),
    }
