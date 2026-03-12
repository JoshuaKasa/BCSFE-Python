from __future__ import annotations

import importlib

from bcsfe import core

import simple_max_account as simple_max_account_module

from .bootstrap import PRESET_ALIASES
from .bootstrap import state


def ensure_loaded() -> core.SaveFile:
    """Return the loaded save file, or fail if none is loaded."""
    if state.save_file is None:
        raise RuntimeError("No save loaded.")
    return state.save_file


def resolve_preset_key(raw: str) -> str:
    """Normalize a preset key and map known aliases."""
    key = str(raw or "").strip().lower()
    return PRESET_ALIASES.get(key, key)


def get_ops_and_presets() -> tuple[
    dict[str, tuple[str, object]],
    dict[str, list[str]],
]:
    """Reload preset/operation tables so UI reflects latest local edits."""
    try:
        module = importlib.reload(simple_max_account_module)
    except Exception:
        module = simple_max_account_module
    return module.OPERATIONS, module.PRESETS


def parse_game_version(
    raw: object,
    fallback: core.GameVersion,
) -> core.GameVersion:
    """Parse a game version from string/int text, else use fallback."""
    text = str(raw or "").strip()
    if not text:
        return fallback
    try:
        if text.isdigit():
            return core.GameVersion(int(text))
        return core.GameVersion.from_string(text)
    except Exception:
        return fallback


def clone_save(sf: core.SaveFile) -> core.SaveFile:
    """Clone a save-file object through dictionary serialization."""
    return core.SaveFile.from_dict(sf.to_dict(), warn=False)
