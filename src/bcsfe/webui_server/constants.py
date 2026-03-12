"""Immutable constants for the web UI backend."""

from __future__ import annotations

from types import MappingProxyType

BASE_UPGRADE_ICON_FALLBACK_IDS = MappingProxyType(
    {
        0: 60,
        1: 61,
        2: 62,
        3: 63,
        4: 64,
        5: 65,
        6: 66,
        7: 67,
        8: 68,
        9: 69,
    }
)

PRESET_ALIASES = MappingProxyType(
    {
        "human_max": "10",
        "full_legit_max": "9",
        "safe_resources": "1",
        "starter_boost": "5",
    }
)

TRANSFER_BACKUP_VERSION = 1
TRANSFER_HISTORY_LIMIT = 60
