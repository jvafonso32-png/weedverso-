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
        "telegramPin": {"chatId": "", "messageId": 0, "updatedAt": "", "link": "", "status": "idle"},
    }


def _normalize_telegram_pin(raw_pin):
    raw_pin = dict(raw_pin or {})
    return {
        "chatId": str(raw_pin.get("chatId") or ""),
        "messageId": max(0, int(raw_pin.get("messageId") or 0)),
        "updatedAt": str(raw_pin.get("updatedAt") or ""),
        "link": str(raw_pin.get("link") or ""),
        "status": str(raw_pin.get("status") or "idle"),
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
    runtime["telegramPin"] = _normalize_telegram_pin(runtime.get("telegramPin"))
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
    return f"{base_url}/login"


def build_share_links(version):
    links = {
        "local": _versioned_link(local_base_url(), version),
        "public": _versioned_link(public_base_url(), version),
    }
    links["preferred"] = links["public"] or links["local"]
    return links


def _telegram_link(links):
    preferred = str((links or {}).get("public") or (links or {}).get("preferred") or "").strip()
    if not preferred:
        preferred = str((links or {}).get("local") or "").strip()
    if "?" in preferred:
        preferred = preferred.split("?", 1)[0].rstrip("/")
    return preferred


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


def _telegram_call(token, method, payload=None):
    payload = {key: value for key, value in dict(payload or {}).items() if value not in {None, ""}}
    data = parse.urlencode(payload).encode("utf-8")
    req = request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data)
    with request.urlopen(req, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Falha na API do Telegram: {body}")
    return body.get("result")


def _notify_telegram(links, previous_pin=None):
    token = str(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        return {"status": "unconfigured", "pin": _normalize_telegram_pin(previous_pin)}
    chat_id = str(os.getenv("WEEDVERSO_NOTIFY_CHAT_ID") or "").strip() or str(latest_chat_id() or "").strip()
    if not chat_id:
        return {"status": "no_chat", "pin": _normalize_telegram_pin(previous_pin)}

    preferred_link = _telegram_link(links)
    if not preferred_link:
        return {"status": "failed", "pin": _normalize_telegram_pin(previous_pin)}

    previous_pin = _normalize_telegram_pin(previous_pin)
    message_id = 0
    try:
        if previous_pin.get("chatId") == chat_id and previous_pin.get("messageId"):
            message_id = int(previous_pin["messageId"])
            _telegram_call(
                token,
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": preferred_link,
                    "disable_web_page_preview": "true",
                },
            )
        else:
            result = _telegram_call(
                token,
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": preferred_link,
                    "disable_web_page_preview": "true",
                    "disable_notification": "true",
                },
            )
            message_id = int((result or {}).get("message_id") or 0)
            if previous_pin.get("chatId") == chat_id and previous_pin.get("messageId") and previous_pin.get("messageId") != message_id:
                try:
                    _telegram_call(
                        token,
                        "deleteMessage",
                        {"chat_id": chat_id, "message_id": int(previous_pin["messageId"])},
                    )
                except Exception:
                    pass

        _telegram_call(
            token,
            "pinChatMessage",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "disable_notification": "true",
            },
        )
        return {
            "status": "sent",
            "pin": {
                "chatId": chat_id,
                "messageId": message_id,
                "updatedAt": _now_iso(),
                "link": preferred_link,
                "status": "sent",
            },
        }
    except Exception:
        try:
            result = _telegram_call(
                token,
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": preferred_link,
                    "disable_web_page_preview": "true",
                    "disable_notification": "true",
                },
            )
            message_id = int((result or {}).get("message_id") or 0)
            _telegram_call(
                token,
                "pinChatMessage",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "disable_notification": "true",
                },
            )
            if previous_pin.get("chatId") == chat_id and previous_pin.get("messageId") and previous_pin.get("messageId") != message_id:
                try:
                    _telegram_call(
                        token,
                        "deleteMessage",
                        {"chat_id": chat_id, "message_id": int(previous_pin["messageId"])},
                    )
                except Exception:
                    pass
            return {
                "status": "sent",
                "pin": {
                    "chatId": chat_id,
                    "messageId": message_id,
                    "updatedAt": _now_iso(),
                    "link": preferred_link,
                    "status": "sent",
                },
            }
        except Exception:
            failed_pin = previous_pin if previous_pin.get("messageId") else _normalize_telegram_pin({})
            failed_pin["status"] = "failed"
            failed_pin["link"] = preferred_link
            failed_pin["updatedAt"] = _now_iso()
            return {"status": "failed", "pin": failed_pin}


def _state_hash(state):
    payload = json.dumps(state or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    current_links = build_share_links(runtime["version"])
    link_changed = current_links != dict(runtime.get("lastLinks") or {})
    should_publish = bool(force or changed or link_changed or runtime["version"] <= 0)
    version = runtime["version"]
    notifications = dict(runtime["notifications"])
    telegram_pin = _normalize_telegram_pin(runtime.get("telegramPin"))

    if should_publish:
        version += 1
        links = build_share_links(version)
        message = _publish_message(version, reason, links)
        telegram_result = _notify_telegram(links, previous_pin=telegram_pin)
        notifications = {
            "telegram": str(telegram_result.get("status") or "failed"),
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
                "telegramPin": telegram_result.get("pin"),
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
