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
JOAO_GIST_ID = os.getenv("GITHUB_GIST_ID", "20470ade1d831a08ca6f87955658d8a2").strip()
JULIA_GIST_ID = os.getenv("GITHUB_JULIA_GIST_ID", "746f27fac12d7211f3966965afbf7889").strip()

_LAST_PULL_TIMES = {"joao": 0.0, "julia": 0.0}
_PULL_LOCKS = {"joao": threading.Lock(), "julia": threading.Lock()}
_PUSH_LOCKS = {"joao": threading.Lock(), "julia": threading.Lock()}
_PERIODIC_SYNC_STARTED = False


def _get_user_config(user="joao"):
    user = str(user or "joao").lower().strip()
    if user == "julia":
        return {
            "user": "julia",
            "gist_id": JULIA_GIST_ID,
            "state_file": persistent_data_root() / "julia_state.json",
            "state_filename": "weedverso_state.json"
        }
    return {
        "user": "joao",
        "gist_id": JOAO_GIST_ID,
        "state_file": persistent_data_root() / "shared_state.json",
        "state_filename": "weedverso_state.json"
    }


def state_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def pull_from_gist(user="joao", force=False, max_age_seconds=10.0):
    cfg = _get_user_config(user)
    gist_id = cfg["gist_id"]
    state_file = cfg["state_file"]
    u = cfg["user"]

    if not TOKEN or not gist_id:
        return None, f"Token ou Gist ID nao configurado para {u}"

    now = time.time()
    last_pull = _LAST_PULL_TIMES.get(u, 0.0)
    if not force and (now - last_pull < max_age_seconds):
        try:
            with shared_state.using_state_file(state_file):
                return shared_state.read_state(), "cached"
        except Exception:
            pass

    lock = _PULL_LOCKS.get(u, _PULL_LOCKS["joao"])
    if not lock.acquire(blocking=True, timeout=5.0):
        try:
            with shared_state.using_state_file(state_file):
                return shared_state.read_state(), "busy"
        except Exception:
            return None, "Lock busy"

    try:
        req = urllib.request.Request(
            f"https://api.github.com/gists/{gist_id}",
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

            # Atualiza arquivo de estado local apropriado
            with shared_state.using_state_file(state_file):
                shared_state.write_state(norm)

            _LAST_PULL_TIMES[u] = time.time()
            return norm, "ok"
    except Exception as e:
        return None, str(e)
    finally:
        lock.release()


def push_to_gist(user="joao"):
    cfg = _get_user_config(user)
    gist_id = cfg["gist_id"]
    state_file = cfg["state_file"]
    u = cfg["user"]

    if not TOKEN or not gist_id:
        return False, f"Token ou Gist ID nao configurado para {u}"

    lock = _PUSH_LOCKS.get(u, _PUSH_LOCKS["joao"])
    if not lock.acquire(blocking=True, timeout=10.0):
        return False, "Lock busy"

    try:
        with shared_state.using_state_file(state_file):
            current = shared_state.read_state()

        payload = {
            "files": {
                "weedverso_state.json": {
                    "content": json.dumps(current, indent=2, ensure_ascii=False)
                }
            }
        }
        req = urllib.request.Request(
            f"https://api.github.com/gists/{gist_id}",
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
            _LAST_PULL_TIMES[u] = time.time()
            return True, "ok"
    except Exception as e:
        return False, str(e)
    finally:
        lock.release()


def trigger_push_async(reason="sync", user="joao"):
    def worker():
        try:
            push_to_gist(user=user)
        except Exception as exc:
            print(f"[Gist Push Error ({reason} - {user})]: {exc}")

    threading.Thread(target=worker, daemon=True, name=f"weedverso-gist-push-{user}-{reason}").start()
    return True


def start_periodic_sync(interval_seconds=30):
    global _PERIODIC_SYNC_STARTED
    if _PERIODIC_SYNC_STARTED:
        return
    _PERIODIC_SYNC_STARTED = True

    def sync_loop():
        # Primeira execucao imediata para ambos
        try:
            pull_from_gist(user="joao", force=True)
        except Exception as exc:
            print(f"[Gist Sync Inicial Joao Falhou]: {exc}")

        if JULIA_GIST_ID:
            try:
                pull_from_gist(user="julia", force=True)
            except Exception as exc:
                print(f"[Gist Sync Inicial Julia Falhou]: {exc}")

        while True:
            try:
                time.sleep(interval_seconds)
                pull_from_gist(user="joao", force=False, max_age_seconds=interval_seconds - 5)
                if JULIA_GIST_ID:
                    pull_from_gist(user="julia", force=False, max_age_seconds=interval_seconds - 5)
            except Exception as exc:
                print(f"[Gist Sync Loop Falhou]: {exc}")

    threading.Thread(target=sync_loop, daemon=True, name="weedverso-gist-periodic-sync").start()


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pull"
    target_user = sys.argv[2] if len(sys.argv) > 2 else "joao"
    if cmd == "pull":
        state, msg = pull_from_gist(user=target_user, force=True)
        print(f"PULL ({target_user}): {msg}")
    elif cmd == "push":
        ok, msg = push_to_gist(user=target_user)
        print(f"PUSH ({target_user}): {msg}")
