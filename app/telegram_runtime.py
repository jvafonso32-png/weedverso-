import json
import os
import threading
from datetime import datetime

from weedverso_paths import persistent_data_root


DATA_DIR = persistent_data_root()
RUNTIME_FILE = DATA_DIR / "telegram_runtime.json"
TEST_STATE_DIR = DATA_DIR / "telegram_test_state"
LOCK = threading.RLock()
TRUTHY = {"1", "true", "on", "yes", "sim"}
FALSY = {"0", "false", "off", "no", "nao", "não"}


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _normalize_runtime(raw_runtime):
    raw_runtime = raw_runtime or {}
    return {
        "testMode": bool(raw_runtime.get("testMode")),
        "updatedAt": str(raw_runtime.get("updatedAt") or ""),
    }


def _env_override():
    value = os.getenv("WEEDVERSO_TELEGRAM_TEST_MODE", "").strip().lower()
    if value in TRUTHY:
        return {"testMode": True, "updatedAt": _now_iso()}
    if value in FALSY:
        return {"testMode": False, "updatedAt": _now_iso()}
    return None


def ensure_runtime_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEST_STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not RUNTIME_FILE.exists():
        normalized = _normalize_runtime({"testMode": False, "updatedAt": ""})
        RUNTIME_FILE.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def read_runtime():
    override = _env_override()
    if override is not None:
        return override

    ensure_runtime_store()
    with LOCK:
        try:
            raw_runtime = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw_runtime = {}
    return _normalize_runtime(raw_runtime)


def write_runtime(runtime):
    ensure_runtime_store()
    normalized = _normalize_runtime(runtime)
    with LOCK:
        RUNTIME_FILE.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def set_telegram_test_mode(enabled):
    return write_runtime({"testMode": bool(enabled), "updatedAt": _now_iso()})


def telegram_test_mode_enabled():
    return bool(read_runtime().get("testMode"))


def telegram_test_state_file(chat_id):
    ensure_runtime_store()
    safe_chat_id = "".join(ch for ch in str(chat_id or "anon") if ch.isdigit()) or "anon"
    return TEST_STATE_DIR / f"{safe_chat_id}.json"


def clear_telegram_test_state(chat_id=None):
    ensure_runtime_store()
    if chat_id is None:
        for item in TEST_STATE_DIR.glob("*.json"):
            try:
                item.unlink()
            except FileNotFoundError:
                continue
        return

    target = telegram_test_state_file(chat_id)
    try:
        target.unlink()
    except FileNotFoundError:
        return
