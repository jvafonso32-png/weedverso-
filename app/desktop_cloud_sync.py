import argparse
import hashlib
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib import error, request

from env_loader import load_env_file
from shared_state import normalize_state, read_state, write_state
from weedverso_paths import persistent_data_root


load_env_file()

DATA_DIR = persistent_data_root()
STATE_FILE = DATA_DIR / "shared_state.json"
STATUS_FILE = DATA_DIR / "cloud_sync_status.json"
SHARE_INFO_FILE = DATA_DIR / "cloud_share_info.json"
CLOUD_URL = str(os.getenv("WEEDVERSO_CLOUD_URL") or os.getenv("WEEDVERSO_PUBLIC_URL") or "").strip().rstrip("/")
SYNC_TOKEN = str(os.getenv("WEEDVERSO_SYNC_TOKEN") or "").strip()
SYNC_INTERVAL_SECONDS = max(1, float(os.getenv("WEEDVERSO_DESKTOP_SYNC_INTERVAL_SECONDS", "1") or "1"))
SYNC_TIMEOUT_SECONDS = max(5, int(os.getenv("WEEDVERSO_DESKTOP_SYNC_TIMEOUT_SECONDS", "20") or "20"))
FAST_PUSH_LOCK = threading.Lock()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def state_hash(payload):
    return hashlib.sha256(
        json.dumps(normalize_state(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def ensure_config():
    if not CLOUD_URL:
        raise RuntimeError("Defina WEEDVERSO_CLOUD_URL no .env para conectar o desktop a nuvem.")
    if not SYNC_TOKEN:
        raise RuntimeError("Defina WEEDVERSO_SYNC_TOKEN no .env para espelhar dados com seguranca.")


def sync_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Weedverso-Sync-Token": SYNC_TOKEN,
    }


def request_json(path, method="GET", payload=None):
    ensure_config()
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(f"{CLOUD_URL}{path}", data=body, headers=sync_headers(), method=method)
    try:
        with request.urlopen(req, timeout=SYNC_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8").strip()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Falha {method} {path}: HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha {method} {path}: {exc.reason}") from exc
    if not raw:
        return {}
    return json.loads(raw)


def write_json_if_changed(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def read_status():
    if not STATUS_FILE.exists():
        return {}
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_status(patch):
    status = read_status()
    status.update(patch or {})
    status["cloudUrl"] = CLOUD_URL
    status["statusFile"] = str(STATUS_FILE)
    write_json_if_changed(STATUS_FILE, status)
    return status


def local_state_mtime():
    try:
        return float(STATE_FILE.stat().st_mtime)
    except FileNotFoundError:
        return 0.0


def sync_share_info(share_info):
    share_info = share_info or {}
    changed = write_json_if_changed(SHARE_INFO_FILE, share_info)
    return changed, int(share_info.get("version") or 0)


def sync_once(reason="sync"):
    remote_state = normalize_state(request_json("/api/state"))
    remote_hash = state_hash(remote_state)
    remote_share_info = request_json("/api/share-info")
    local_state = normalize_state(read_state())
    local_hash = state_hash(local_state)
    status = read_status()
    last_local_mtime = float(status.get("lastLocalStateMtime") or 0)
    current_local_mtime = local_state_mtime()

    if local_hash == remote_hash:
        share_changed, share_version = sync_share_info(remote_share_info)
        status = write_status(
            {
                "mode": "sync",
                "direction": "noop",
                "lastAttemptAt": now_iso(),
                "lastSuccessfulSyncAt": now_iso(),
                "lastError": "",
                "remoteStateHash": remote_hash,
                "localStateHash": local_hash,
                "lastLocalStateMtime": current_local_mtime,
                "shareVersion": share_version,
                "localStateFile": str(STATE_FILE.resolve()),
                "shareInfoFile": str(SHARE_INFO_FILE.resolve()),
            }
        )
        return {
            "direction": "noop",
            "stateChanged": False,
            "shareChanged": share_changed,
            "status": status,
            "shareInfo": remote_share_info,
        }

    if current_local_mtime > last_local_mtime + 1e-6:
        pushed = push_local(reason=reason)
        pushed["direction"] = "push"
        return pushed

    write_state(remote_state)
    share_changed, share_version = sync_share_info(remote_share_info)
    status = write_status(
        {
            "mode": "sync",
            "direction": "pull",
            "lastAttemptAt": now_iso(),
            "lastSuccessfulSyncAt": now_iso(),
            "lastError": "",
            "remoteStateHash": remote_hash,
            "localStateHash": remote_hash,
            "lastLocalStateMtime": local_state_mtime(),
            "shareVersion": share_version,
            "localStateFile": str(STATE_FILE.resolve()),
            "shareInfoFile": str(SHARE_INFO_FILE.resolve()),
        }
    )
    return {
        "direction": "pull",
        "stateChanged": True,
        "shareChanged": share_changed,
        "status": status,
        "shareInfo": remote_share_info,
    }


def pull_once():
    remote_state = normalize_state(request_json("/api/state"))
    share_info = request_json("/api/share-info")
    remote_hash = state_hash(remote_state)
    try:
        local_hash = state_hash(read_state())
    except Exception:
        local_hash = ""
    state_changed = remote_hash != local_hash
    if state_changed:
        write_state(remote_state)
    share_changed = write_json_if_changed(SHARE_INFO_FILE, share_info)
    status = write_status(
        {
            "mode": "pull",
            "lastAttemptAt": now_iso(),
            "lastSuccessfulSyncAt": now_iso(),
            "lastError": "",
            "remoteStateHash": remote_hash,
            "shareVersion": int(share_info.get("version") or 0),
            "localStateFile": str((DATA_DIR / "shared_state.json").resolve()),
            "shareInfoFile": str(SHARE_INFO_FILE.resolve()),
        }
    )
    return {
        "stateChanged": state_changed,
        "shareChanged": share_changed,
        "status": status,
        "shareInfo": share_info,
    }


def push_local(reason="desktop-bootstrap"):
    local_state = normalize_state(read_state())
    request_json("/api/state", method="PUT", payload=local_state)
    publish = request_json(
        "/api/publish",
        method="POST",
        payload={"state": local_state, "reason": reason, "force": False},
    )
    share_info = request_json("/api/share-info")
    share_changed, share_version = sync_share_info(share_info)
    status = write_status(
        {
            "mode": "push",
            "direction": "push",
            "lastAttemptAt": now_iso(),
            "lastPushAt": now_iso(),
            "lastSuccessfulSyncAt": now_iso(),
            "lastError": "",
            "remoteStateHash": state_hash(local_state),
            "localStateHash": state_hash(local_state),
            "lastLocalStateMtime": local_state_mtime(),
            "lastPublishVersion": int(((publish or {}).get("publish") or {}).get("version") or 0),
            "shareVersion": share_version,
            "localStateFile": str(STATE_FILE.resolve()),
            "shareInfoFile": str(SHARE_INFO_FILE.resolve()),
        }
    )
    return {
        "publish": publish,
        "pull": None,
        "direction": "push",
        "stateChanged": True,
        "shareChanged": share_changed,
        "status": status,
        "shareInfo": share_info,
    }


def trigger_background_push(reason="external-update"):
    if not CLOUD_URL or not SYNC_TOKEN:
        return False

    def worker():
        if not FAST_PUSH_LOCK.acquire(blocking=False):
            return
        try:
            push_local(reason=reason)
        except Exception as exc:
            write_status(
                {
                    "lastAttemptAt": now_iso(),
                    "lastError": str(exc),
                }
            )
            print(f"[{now_iso()}] Push rapido falhou: {exc}")
        finally:
            FAST_PUSH_LOCK.release()

    threading.Thread(target=worker, daemon=True, name=f"weedverso-fast-sync-{reason}").start()
    return True


def print_json(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_forever():
    print(f"Espelhamento desktop<->nuvem ativo em {CLOUD_URL}")
    while True:
        try:
            result = sync_once(reason="sync")
            if result["stateChanged"] or result["shareChanged"]:
                print(
                    f"[{now_iso()}] Sync ok | direcao={result.get('direction') or 'noop'} | "
                    f"estado={result['stateChanged']} | share={result['shareChanged']} | "
                    f"versao={int((result['shareInfo'] or {}).get('version') or 0)}"
                )
        except Exception as exc:
            write_status(
                {
                    "lastAttemptAt": now_iso(),
                    "lastError": str(exc),
                }
            )
            print(f"[{now_iso()}] Sync falhou: {exc}")
        time.sleep(SYNC_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(description="Espelha o Weedverso da nuvem para o desktop e faz bootstrap seguro.")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=("run", "pull-once", "push-local", "status"),
        help="run inicia o espelhamento; pull-once baixa uma vez; push-local envia o estado local para a nuvem.",
    )
    args = parser.parse_args()
    ensure_config()

    if args.command == "pull-once":
        print_json(pull_once())
        return
    if args.command == "push-local":
        print_json(push_local())
        return
    if args.command == "status":
        print_json(read_status())
        return
    run_forever()


if __name__ == "__main__":
    main()
