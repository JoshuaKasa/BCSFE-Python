"""Bootstrap objects and shared primitives for the web UI backend."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from flask import Flask

from bcsfe import core
from bcsfe.cli.save_management import SaveManagement
from bcsfe.core.game.gamoto import ototo as ototo_data
from bcsfe.core.game.gamoto.gamatoto import Helper as GamatotoHelper
from simple_max_account import resolve_input_path

from ..constants import BASE_UPGRADE_ICON_FALLBACK_IDS
from ..constants import PRESET_ALIASES

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
for candidate_path in (REPO_ROOT, SRC_DIR):
    if str(candidate_path) not in sys.path:
        sys.path.insert(0, str(candidate_path))

WEBUI_DIR = REPO_ROOT / "webui"


def clean_name(text: str) -> str:
    """Normalize display names to human-friendly title case."""
    text = text.replace("_", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text.title() if text.islower() else text


def safe_int(value: object, default: int = 0) -> int:
    """Parse integer value with fallback."""
    try:
        return int(value)
    except Exception:
        return default


def cat_number(cat: core.Cat) -> str:
    """Return formatted unit number with current form suffix."""
    form = max(1, min(cat.current_form + 1, 4))
    return f"{cat.id + 1:03d}-{form}"


def _build_wiki_file_url(filename: str) -> str:
    """Build wiki special file path URL."""
    encoded = quote(filename)
    return f"https://battlecats.miraheze.org/wiki/Special:FilePath/{encoded}"


def gatyaitem_icon_url(item_id: int | None) -> str | None:
    """Return wiki icon URL for a gatyaitem id."""
    if item_id is None:
        return None
    value = safe_int(item_id, -1)
    if value < 0:
        return None
    if value == 61:
        value = 60
    padded = f"{value:02d}" if value < 10 else str(value)
    filename = f"GatyaitemD_{padded}_f.png"
    return _build_wiki_file_url(filename)


def wiki_file_icon_url(filename: str | None) -> str | None:
    """Return wiki URL for one known filename."""
    if not filename:
        return None
    return _build_wiki_file_url(str(filename))


def talent_orb_icon_url() -> str:
    """Return default talent orb icon URL."""
    fallback_url = "/webui/icons/inventory.svg"
    return wiki_file_icon_url("Orbs_Icon.png") or fallback_url


def talent_orb_rank_icon_url(rank: str | None) -> str:
    """Return grade-based icon URL for talent orbs."""
    rank_key = str(rank or "").strip().upper()
    mapping = {
        "S": "Talent_9.png",
        "A": "Talent_8.png",
        "B": "Talent_7.png",
        "C": "Talent_6.png",
        "D": "Talent_5.png",
    }
    return wiki_file_icon_url(mapping.get(rank_key)) or talent_orb_icon_url()


def medal_icon_url(medal_id: int | None) -> str | None:
    """Return wiki medal icon URL for one medal id."""
    if medal_id is None:
        return None
    value = safe_int(medal_id, -1)
    if value < 0:
        return None
    filename = f"Medal_{value:03d}.png"
    return _build_wiki_file_url(filename)


def enemy_icon_url(enemy_id: int | None) -> str | None:
    """Return wiki enemy icon URL for one enemy id."""
    if enemy_id is None:
        return None
    value = safe_int(enemy_id, -1)
    if value < 0:
        return None
    width = 3 if value < 1000 else len(str(value))
    filename = f"E_{str(value).zfill(width)}.png"
    return _build_wiki_file_url(filename)


def cat_sprite_url(cat_id: int, form_index: int) -> str:
    """Return onestoppress sprite URL for cat + form index."""
    unit_number = f"{cat_id + 1:03d}-{max(1, min(form_index + 1, 4))}"
    return f"https://onestoppress.com/images/{unit_number}.png"


@dataclass
class AppState:
    """Runtime mutable state for currently loaded web UI session."""

    save_file: core.SaveFile | None = None
    loaded_path: Path | None = None
    name_cache: dict[int, str] | None = None
    mygamatoto_index: dict[str, str] | None = None
    history: list[dict[str, object]] | None = None
    history_reasons: list[str] | None = None
    history_index: int = -1
    history_limit: int = 20
    safe_mode: bool = True
    transfer_records: list[dict[str, object]] | None = None

    def __post_init__(self) -> None:
        """Initialize mutable containers if not provided."""
        if self.name_cache is None:
            self.name_cache = {}
        if self.mygamatoto_index is None:
            self.mygamatoto_index = {}
        if self.history is None:
            self.history = []
        if self.history_reasons is None:
            self.history_reasons = []
        if self.transfer_records is None:
            self.transfer_records = []


app = Flask(__name__, static_folder=str(WEBUI_DIR), static_url_path="/webui")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
state = AppState()

CACHE_DIR = REPO_ROOT / ".cache" / "mygamatoto"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = CACHE_DIR / "allcats_index.json"
TRANSFER_CODES_PATH = CACHE_DIR / "transfer_codes.json"

core.core_data.init_data()

__all__ = [
    "app",
    "AppState",
    "BASE_UPGRADE_ICON_FALLBACK_IDS",
    "CACHE_DIR",
    "cat_number",
    "cat_sprite_url",
    "clean_name",
    "core",
    "enemy_icon_url",
    "GamatotoHelper",
    "gatyaitem_icon_url",
    "INDEX_PATH",
    "medal_icon_url",
    "ototo_data",
    "PRESET_ALIASES",
    "REPO_ROOT",
    "resolve_input_path",
    "safe_int",
    "SaveManagement",
    "SRC_DIR",
    "state",
    "talent_orb_icon_url",
    "talent_orb_rank_icon_url",
    "TRANSFER_CODES_PATH",
    "WEBUI_DIR",
    "wiki_file_icon_url",
]
