import json
from datetime import datetime

from weedverso_paths import persistent_data_root


STATUS_FILE = persistent_data_root() / "desktop_code_backup_status.json"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def default_status():
    return {
        "status": "idle",
        "message": "Backup do codigo aguardando desktop",
        "startedAt": "",
        "finishedAt": "",
        "lastRunAt": "",
        "trigger": "",
        "source": "",
        "branch": "",
        "commit": "",
        "remote": "",
        "changedFiles": 0,
        "pushed": False,
        "lastError": "",
        "statusFile": str(STATUS_FILE),
    }


def read_status():
    if not STATUS_FILE.exists():
        return default_status()
    try:
        payload = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default_status()
    if not isinstance(payload, dict):
        return default_status()
    merged = default_status()
    merged.update(payload)
    merged["statusFile"] = str(STATUS_FILE)
    return merged


def write_status(patch=None):
    payload = read_status()
    payload.update(patch or {})
    payload["statusFile"] = str(STATUS_FILE)
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
