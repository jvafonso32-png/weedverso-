import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib import error, request

from desktop_code_backup_status import now_iso, write_status
from env_loader import load_env_file
from weedverso_paths import persistent_data_root


load_env_file()

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
LOCK_FILE = persistent_data_root() / "desktop_code_backup.lock"
CLOUD_URL = str(os.getenv("WEEDVERSO_CLOUD_URL") or os.getenv("WEEDVERSO_PUBLIC_URL") or "").strip().rstrip("/")
SYNC_TOKEN = str(os.getenv("WEEDVERSO_SYNC_TOKEN") or "").strip()


class BackupError(RuntimeError):
    pass


def lock_exists():
    return LOCK_FILE.exists()


def acquire_lock():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    os.write(handle, str(os.getpid()).encode("utf-8"))
    return handle


def release_lock(handle):
    if handle is not None:
        os.close(handle)
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def find_git_exe():
    candidates = [
        os.getenv("GIT_EXE", "").strip(),
        shutil.which("git"),
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    raise BackupError("Git nao encontrado no desktop para salvar o codigo.")


def run_git(git_exe, args, check=True):
    completed = subprocess.run(
        [git_exe, "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise BackupError(detail or f"Falha ao executar git {' '.join(args)}")
    return completed


def git_output(git_exe, args, default=""):
    completed = run_git(git_exe, args, check=False)
    if completed.returncode != 0:
        return default
    return (completed.stdout or "").strip()


def ensure_git_identity(git_exe):
    name = git_output(git_exe, ["config", "user.name"])
    email = git_output(git_exe, ["config", "user.email"])
    if not name:
        run_git(git_exe, ["config", "user.name", "Weedverso Desktop"])
    if not email:
        run_git(git_exe, ["config", "user.email", "weedverso-desktop@local"])


def current_branch(git_exe):
    branch = git_output(git_exe, ["rev-parse", "--abbrev-ref", "HEAD"])
    if not branch or branch == "HEAD":
        raise BackupError("Nao consegui identificar a branch atual do repositório.")
    return branch


def current_commit(git_exe):
    return git_output(git_exe, ["rev-parse", "--short", "HEAD"])


def origin_url(git_exe):
    remote = git_output(git_exe, ["remote", "get-url", "origin"])
    if not remote:
        raise BackupError("O repositório ainda nao tem remote origin configurado.")
    return remote


def changed_entries(git_exe):
    raw = git_output(git_exe, ["status", "--short"])
    return [line for line in raw.splitlines() if line.strip()]


def staged_entries(git_exe):
    raw = git_output(git_exe, ["diff", "--cached", "--name-only"])
    return [line for line in raw.splitlines() if line.strip()]


def report_remote_status(payload):
    if not CLOUD_URL or not SYNC_TOKEN:
        return False, ""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{CLOUD_URL}/api/desktop-code-backup-status",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Weedverso-Sync-Token": SYNC_TOKEN,
        },
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            response.read()
        return True, ""
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        return False, f"HTTP {exc.code} {detail}".strip()
    except Exception as exc:
        return False, str(exc)


def publish_status(payload):
    local_payload = write_status(payload)
    delivered, delivery_error = report_remote_status(local_payload)
    if delivery_error:
        local_payload = write_status({"reportDelivered": False, "reportError": delivery_error})
    elif delivered:
        local_payload = write_status({"reportDelivered": True, "reportError": ""})
    return local_payload


def success_message(changed_files):
    if changed_files > 0:
        noun = "arquivo" if changed_files == 1 else "arquivos"
        return f"Codigo salvo no GitHub com {changed_files} {noun} atualizados."
    return "Codigo ja estava salvo no GitHub."


def run_backup(trigger, uri):
    lock_handle = acquire_lock()
    if lock_handle is None:
        payload = publish_status(
            {
                "status": "running",
                "message": "Ja existe um backup do codigo rodando no desktop.",
                "lastError": "",
                "trigger": trigger,
                "source": "desktop-protocol",
                "lastRunAt": now_iso(),
            }
        )
        return payload

    started_at = now_iso()
    try:
        payload = publish_status(
            {
                "status": "running",
                "message": "Preparando backup do codigo para o GitHub...",
                "startedAt": started_at,
                "finishedAt": "",
                "lastRunAt": started_at,
                "trigger": trigger,
                "source": "desktop-protocol",
                "launchUri": uri or "",
                "branch": "",
                "commit": "",
                "remote": "",
                "changedFiles": 0,
                "pushed": False,
                "lastError": "",
            }
        )

        git_exe = find_git_exe()
        ensure_git_identity(git_exe)
        branch = current_branch(git_exe)
        remote = origin_url(git_exe)
        pending = changed_entries(git_exe)
        changed_files = 0

        if pending:
            publish_status(
                {
                    "status": "running",
                    "message": f"Versionando {len(pending)} alteracoes do codigo...",
                    "startedAt": started_at,
                    "lastRunAt": started_at,
                    "trigger": trigger,
                    "source": "desktop-protocol",
                    "branch": branch,
                    "remote": remote,
                    "lastError": "",
                }
            )
            run_git(git_exe, ["add", "-A"])
            staged = staged_entries(git_exe)
            changed_files = len(staged)
            if staged:
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                run_git(git_exe, ["commit", "-m", f"chore: desktop backup {stamp}"])

        publish_status(
            {
                "status": "running",
                "message": "Enviando codigo para o GitHub...",
                "startedAt": started_at,
                "lastRunAt": started_at,
                "trigger": trigger,
                "source": "desktop-protocol",
                "branch": branch,
                "remote": remote,
                "changedFiles": changed_files,
                "lastError": "",
            }
        )
        run_git(git_exe, ["push", "origin", branch])

        final_payload = publish_status(
            {
                "status": "ok",
                "message": success_message(changed_files),
                "startedAt": started_at,
                "finishedAt": now_iso(),
                "lastRunAt": now_iso(),
                "trigger": trigger,
                "source": "desktop-protocol",
                "branch": branch,
                "commit": current_commit(git_exe),
                "remote": remote,
                "changedFiles": changed_files,
                "pushed": True,
                "lastError": "",
            }
        )
        return final_payload
    except Exception as exc:
        final_payload = publish_status(
            {
                "status": "error",
                "message": "Falha ao salvar o codigo no GitHub.",
                "startedAt": started_at,
                "finishedAt": now_iso(),
                "lastRunAt": now_iso(),
                "trigger": trigger,
                "source": "desktop-protocol",
                "pushed": False,
                "lastError": str(exc),
            }
        )
        raise
    finally:
        release_lock(lock_handle)


def main():
    parser = argparse.ArgumentParser(description="Salva o codigo local do Weedverso no GitHub.")
    parser.add_argument("command", nargs="?", default="run", choices=("run", "status"))
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--uri", default="")
    args = parser.parse_args()

    if args.command == "status":
        print(json.dumps(write_status({}), ensure_ascii=False, indent=2))
        return

    payload = run_backup(args.trigger, args.uri)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
