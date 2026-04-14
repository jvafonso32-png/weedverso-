import os
import sys
from pathlib import Path


def resource_root():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def executable_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def app_home():
    if not getattr(sys, "frozen", False):
        return resource_root()
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or executable_root())
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "Weedverso"


def persistent_data_root():
    if getattr(sys, "frozen", False):
        return app_home() / "data"
    return resource_root() / "data"


def resource_path(relative_path):
    return resource_root() / relative_path


def env_candidates():
    seen = set()
    candidates = [
        Path.cwd() / ".env",
        executable_root() / ".env",
        app_home() / ".env",
        resource_root() / ".env",
    ]
    ordered = []
    for item in candidates:
        key = str(item.resolve()) if item.exists() else str(item)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered
