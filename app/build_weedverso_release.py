import argparse
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
RUNTIME_FILES = [
    ".env.example",
    ".gitignore",
    "api_server.py",
    "build_weedverso_release.py",
    "desktop_code_backup.py",
    "desktop_code_backup_status.py",
    "desktop_cloud_sync.py",
    "index.html",
    "login.html",
    "env_loader.py",
    "share_publish.py",
    "shared_state.py",
    "telegram_bot.py",
    "telegram_chats.py",
    "telegram_runtime.py",
    "weedverso_paths.py",
    "weedverso_app.py",
    "weedverso.cmd",
    "start_weedverso.ps1",
    "handle_weedverso_protocol.ps1",
    "launch_weedverso_hidden.vbs",
    "launch_weedverso_protocol.vbs",
    "register_weedverso_protocol.ps1",
    "deploy/aws/setup_sslip_https.sh",
    "deploy/oracle/.env.oracle.example",
    "deploy/oracle/backup_state.sh",
    "deploy/oracle/deploy_oracle_remote.cmd",
    "deploy/oracle/deploy_oracle_remote.ps1",
    "deploy/oracle/install_oracle_vm.sh",
    "deploy/oracle/README_ORACLE.md",
    "deploy/oracle/weedverso.service",
]
DATA_FILES = [
    "data/shared_state.json",
    "data/telegram_chats.json",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Gera pacote enxuto do app Weedverso.")
    parser.add_argument("--include-data", action="store_true", help="Inclui shared_state e chats atuais.")
    return parser.parse_args()


def runtime_paths(include_data):
    items = list(RUNTIME_FILES)
    if include_data:
        items.extend(DATA_FILES)
    return items


def ensure_exists(relative_path):
    path = ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Arquivo obrigatorio nao encontrado: {relative_path}")
    return path


def build_archive(include_data):
    DIST.mkdir(parents=True, exist_ok=True)
    file_name = "weedverso-app-with-data.zip" if include_data else "weedverso-app.zip"
    target = DIST / file_name
    if target.exists():
        target.unlink()

    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in runtime_paths(include_data):
            source = ensure_exists(relative)
            archive.write(source, arcname=relative.replace("\\", "/"))

    return target


def main():
    args = parse_args()
    target = build_archive(args.include_data)
    size_kb = round(target.stat().st_size / 1024, 1)
    print(f"Pacote Weedverso gerado: {target}")
    print(f"Tamanho: {size_kb} KB")


if __name__ == "__main__":
    main()
