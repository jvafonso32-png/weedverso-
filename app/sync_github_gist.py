import os
import json
import hashlib
import threading
import time
from pathlib import Path
import urllib.request
import urllib.error

from env_loader import load_env_file
from weedverso_paths import persistent_data_root
import shared_state

load_env_file()

TOKEN = os.getenv("GITHUB_SYNC_TOKEN", "").strip()
GIST_ID = os.getenv("GITHUB_GIST_ID", "20470ade1d831a08ca6f87955658d8a2").strip()

_LAST_PULL_TIME = 0.0
_PULL_LOCK = threading.Lock()
_PUSH_LOCK = threading.Lock()
_PERIODIC_SYNC_STARTED = False


def state_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def pull_from_gist(force=False, max_age_seconds=10.0):
    global _LAST_PULL_TIME
    if not TOKEN or not GIST_ID:
        return None, "Token ou Gist ID nao configurado"

    now = time.time()
    if not force and (now - _LAST_PULL_TIME < max_age_seconds):
        try:
            return shared_state.read_state(), "cached"
        except Exception:
            pass

    if not _PULL_LOCK.acquire(blocking=True, timeout=5.0):
        try:
            return shared_state.read_state(), "busy"
        except Exception:
            return None, "Lock busy"

    try:
        req = urllib.request.Request(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={
                "Authorization": f"token {TOKEN}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "WeedversoSync"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            file_info = data.get("files", {}).get("weedverso_state.json")
            if not file_info or not file_info.get("content"):
                return None, "Arquivo weedverso_state.json nao encontrado no Gist"

            parsed = json.loads(file_info["content"])
            norm = shared_state.normalize_state(parsed)

            # Atualiza shared_state local
            shared_state.write_state(norm)
            _LAST_PULL_TIME = time.time()
            return norm, "ok"
    except Exception as e:
        return None, str(e)
    finally:
        _PULL_LOCK.release()


def push_to_gist():
    global _LAST_PULL_TIME
    if not TOKEN or not GIST_ID:
        return False, "Token ou Gist ID nao configurado"

    if not _PUSH_LOCK.acquire(blocking=True, timeout=10.0):
        return False, "Lock busy"

    try:
        current = shared_state.read_state()
        payload = {
            "files": {
                "weedverso_state.json": {
                    "content": json.dumps(current, indent=2, ensure_ascii=False)
                }
            }
        }
        req = urllib.request.Request(
            f"https://api.github.com/gists/{GIST_ID}",
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={
                "Authorization": f"token {TOKEN}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "WeedversoSync"
            },
            method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            _LAST_PULL_TIME = time.time()
            return True, "ok"
    except Exception as e:
        return False, str(e)
    finally:
        _PUSH_LOCK.release()


def trigger_push_async(reason="sync"):
    def worker():
        try:
            push_to_gist()
        except Exception as exc:
            print(f"[Gist Push Error ({reason})]: {exc}")

    threading.Thread(target=worker, daemon=True, name=f"weedverso-gist-push-{reason}").start()
    return True


def start_periodic_sync(interval_seconds=30):
    global _PERIODIC_SYNC_STARTED
    if _PERIODIC_SYNC_STARTED:
        return
    _PERIODIC_SYNC_STARTED = True

    def sync_loop():
        # Primeira execucao imediata
        try:
            pull_from_gist(force=True)
        except Exception as exc:
            print(f"[Gist Sync Inicial Falhou]: {exc}")

        while True:
            try:
                time.sleep(interval_seconds)
                pull_from_gist(force=False, max_age_seconds=interval_seconds - 5)
            except Exception as exc:
                print(f"[Gist Sync Loop Falhou]: {exc}")

    threading.Thread(target=sync_loop, daemon=True, name="weedverso-gist-periodic-sync").start()


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pull"
    if cmd == "pull":
        state, msg = pull_from_gist(force=True)
        print(f"PULL: {msg}")
    elif cmd == "push":
        ok, msg = push_to_gist()
        print(f"PUSH: {msg}")
