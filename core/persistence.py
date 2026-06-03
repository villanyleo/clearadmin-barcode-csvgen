"""
Save and restore application state between runs.

State is stored as JSON in the per-user application-data directory, so it
survives app restarts (and app updates / reinstalls of the .exe).
"""
import json
import os
import sys
from pathlib import Path

APP_NAME = "ClearAdmin CSV vonalkod olvaso"
_STATE_FILENAME = "state.json"


def app_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / APP_NAME


def state_file() -> Path:
    return app_data_dir() / _STATE_FILENAME


def load_state() -> dict | None:
    """Return the saved state dict, or None if there is none / it is unreadable."""
    try:
        with open(state_file(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return None


def save_state(data: dict) -> None:
    """Write *data* as JSON. Best-effort: never raises, so it can't block exit."""
    path = state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # atomic replace
    except OSError:
        pass
