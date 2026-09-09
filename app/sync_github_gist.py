import os
import json
import hashlib
from pathlib import Path
import urllib.request
import urllib.error

from env_loader import load_env_file
from weedverso_paths import persistent_data_root
import shared_state

load_env_file()

TOKEN = os.getenv("GITHUB_SYNC_TOKEN", "").strip()
GIST_ID = os.getenv("GITHUB_GIST_ID", "20470ade1d831a08ca6f87955658d8a2").strip()

def state_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

def pull_from_gist():
    if not TOKEN or not GIST_ID:
        return None, "Token ou Gist ID nao configurado"
    
    req = urllib.request.Request(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "WeedversoSync"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            file_info = data.get("files", {}).get("weedverso_state.json")
            if not file_info or not file_info.get("content"):
                return None, "Arquivo weedverso_state.json nao encontrado no Gist"
            
            parsed = json.loads(file_info["content"])
            norm = shared_state.normalize_state(parsed)
            
            # Atualiza shared_state local
            shared_state.write_state(norm)
            return norm, "ok"
    except Exception as e:
        return None, str(e)

def push_to_gist():
    if not TOKEN or not GIST_ID:
        return False, "Token ou Gist ID nao configurado"
    
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
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "WeedversoSync"
        },
        method="PATCH"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "ok"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pull"
    if cmd == "pull":
        state, msg = pull_from_gist()
        print(f"PULL: {msg}")
    elif cmd == "push":
        ok, msg = push_to_gist()
        print(f"PUSH: {msg}")
