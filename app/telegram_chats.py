import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHATS_FILE = DATA_DIR / "telegram_chats.json"


def ensure_chat_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CHATS_FILE.exists():
        CHATS_FILE.write_text("[]", encoding="utf-8")


def read_chats():
    ensure_chat_store()
    try:
        return json.loads(CHATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_chats(items):
    ensure_chat_store()
    CHATS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def register_chat(chat):
    if not chat or "id" not in chat:
        return
    items = read_chats()
    chat_id = str(chat.get("id"))
    payload = {
        "id": chat_id,
        "type": chat.get("type", ""),
        "username": chat.get("username", ""),
        "first_name": chat.get("first_name", ""),
        "last_name": chat.get("last_name", ""),
    }
    existing = [item for item in items if str(item.get("id")) != chat_id]
    existing.insert(0, payload)
    save_chats(existing[:20])


def latest_chat_id():
    items = read_chats()
    if not items:
        return None
    return str(items[0].get("id") or "")
