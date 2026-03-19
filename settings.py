"""Persistent settings stored in %APPDATA%\\ClaudeHappyHours\\settings.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

SETTINGS_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "ClaudeHappyHours"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULTS: dict = {
    "pos_x": None,
    "pos_y": None,
    "autostart": False,
    "sound_enabled": True,
    "popup_on_golden_start": True,
    "popup_before_golden_end": True,
    "marquee_enabled": True,
    "compact_mode": True,
    "show_usage_stats": True,
}


def load() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_position(x: int, y: int) -> None:
    data = load()
    data["pos_x"] = x
    data["pos_y"] = y
    save(data)


def set_key(key: str, value) -> None:
    data = load()
    data[key] = value
    save(data)
