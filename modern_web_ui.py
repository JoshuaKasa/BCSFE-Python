from __future__ import annotations

import importlib
import json
import re
import sys
import tkinter as tk
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import requests
from tkinter import filedialog
from flask import Flask, jsonify, request, send_from_directory


REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bcsfe import core  # noqa: E402
from bcsfe.cli.save_management import SaveManagement  # noqa: E402
from bcsfe.core.game.gamoto.gamatoto import Helper as GamatotoHelper  # noqa: E402
from bcsfe.core.game.gamoto import ototo as ototo_data  # noqa: E402
import simple_max_account as simple_max_account_module  # noqa: E402
from simple_max_account import resolve_input_path  # noqa: E402


def clean_name(text: str) -> str:
    text = text.replace("_", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text.title() if text.islower() else text


def cat_number(cat: core.Cat) -> str:
    form = max(1, min(cat.current_form + 1, 4))
    return f"{cat.id + 1:03d}-{form}"


def gatyaitem_icon_url(item_id: int | None) -> str | None:
    if item_id is None:
        return None
    value = safe_int(item_id, -1)
    if value < 0:
        return None
    # Some UI item IDs do not have a dedicated public icon file.
    if value == 61:
        value = 60
    # Wiki filenames use zero-padding for single-digit IDs.
    padded = f"{value:02d}" if value < 10 else str(value)
    filename = f"GatyaitemD_{padded}_f.png"
    return f"https://battlecats.miraheze.org/wiki/Special:FilePath/{quote(filename)}"


def medal_icon_url(medal_id: int | None) -> str | None:
    if medal_id is None:
        return None
    value = safe_int(medal_id, -1)
    if value < 0:
        return None
    filename = f"Medal_{value:03d}.png"
    return f"https://battlecats.miraheze.org/wiki/Special:FilePath/{quote(filename)}"


def enemy_icon_url(enemy_id: int | None) -> str | None:
    if enemy_id is None:
        return None
    value = safe_int(enemy_id, -1)
    if value < 0:
        return None
    width = 3 if value < 1000 else len(str(value))
    filename = f"E_{str(value).zfill(width)}.png"
    return f"https://battlecats.miraheze.org/wiki/Special:FilePath/{quote(filename)}"


def cat_sprite_url(cat_id: int, form_index: int) -> str:
    unit_number = f"{cat_id + 1:03d}-{max(1, min(form_index + 1, 4))}"
    return f"https://onestoppress.com/images/{unit_number}.png"


# Fallback icon IDs used when base upgrade item definitions are missing in data files.
BASE_UPGRADE_ICON_FALLBACK_IDS: dict[int, int] = {
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


@dataclass
class AppState:
    save_file: core.SaveFile | None = None
    loaded_path: Path | None = None
    name_cache: dict[int, str] | None = None
    mygamatoto_index: dict[str, str] | None = None
    history: list[dict[str, Any]] | None = None
    history_reasons: list[str] | None = None
    history_index: int = -1
    history_limit: int = 20
    safe_mode: bool = True
    transfer_records: list[dict[str, Any]] | None = None

    def __post_init__(self):
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


app = Flask(__name__, static_folder="webui", static_url_path="/webui")
state = AppState()

CACHE_DIR = REPO_ROOT / ".cache" / "mygamatoto"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = CACHE_DIR / "allcats_index.json"
TRANSFER_CODES_PATH = CACHE_DIR / "transfer_codes.json"
TRANSFER_HISTORY_LIMIT = 60
TRANSFER_BACKUP_VERSION = 1

PRESET_ALIASES: dict[str, str] = {
    "human_max": "10",
    "full_legit_max": "9",
    "safe_resources": "1",
    "starter_boost": "5",
}

# Required for localized save-loading paths and messages used by SaveManagement.
core.core_data.init_data()


def ensure_loaded() -> core.SaveFile:
    if state.save_file is None:
        raise RuntimeError("No save loaded.")
    return state.save_file


def resolve_preset_key(raw: str) -> str:
    key = str(raw or "").strip().lower()
    return PRESET_ALIASES.get(key, key)


def get_ops_and_presets() -> tuple[dict[str, tuple[str, Any]], dict[str, list[str]]]:
    """Reload preset/operation tables so UI reflects latest local edits."""
    try:
        module = importlib.reload(simple_max_account_module)
    except Exception:
        module = simple_max_account_module
    return module.OPERATIONS, module.PRESETS

def transfer_storage_info() -> dict[str, str]:
    downloads_dir = Path.home() / "Documents" / "bcsfe" / "saves" / "transfer_downloads"
    return {
        "history_path": str(TRANSFER_CODES_PATH),
        "downloads_dir": str(downloads_dir),
    }


def _new_transfer_record_id() -> str:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d%H%M%S")
    return f"{stamp}_{uuid4().hex[:10]}"


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "pending"}:
        return True
    if text in {"0", "false", "no", "n", "off", "done", "uploaded"}:
        return False
    return default


def normalize_transfer_record(raw: dict[str, Any]) -> dict[str, Any]:
    kind = "upload" if str(raw.get("kind", "")).strip().lower() == "upload" else "download"
    default_needs_upload = kind == "download"
    now_ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return {
        "id": str(raw.get("id") or _new_transfer_record_id()),
        "timestamp": str(raw.get("timestamp") or now_ts),
        "kind": kind,
        "country": str(raw.get("country", "")).strip().lower(),
        "game_version": str(raw.get("game_version", "")).strip(),
        "transfer_code": str(raw.get("transfer_code", "")).strip(),
        "confirmation_code": str(raw.get("confirmation_code", "")).strip(),
        "path": str(raw.get("path", "")).strip(),
        "inquiry_code": str(raw.get("inquiry_code", "")).strip(),
        "note": str(raw.get("note", "")).strip(),
        "needs_upload": _to_bool(raw.get("needs_upload"), default=default_needs_upload),
        "uploaded_at": str(raw.get("uploaded_at", "")).strip(),
        "uploaded_by": str(raw.get("uploaded_by", "")).strip(),
    }


def load_transfer_records() -> None:
    if not TRANSFER_CODES_PATH.exists():
        state.transfer_records = []
        return
    try:
        records = json.loads(TRANSFER_CODES_PATH.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            state.transfer_records = []
            return
        cleaned: list[dict[str, Any]] = []
        for row in records:
            if not isinstance(row, dict):
                continue
            cleaned.append(normalize_transfer_record(row))
        state.transfer_records = cleaned[:TRANSFER_HISTORY_LIMIT]
        persist_transfer_records()
    except Exception:
        state.transfer_records = []


def persist_transfer_records() -> None:
    records = [normalize_transfer_record(row) for row in list(state.transfer_records or [])]
    state.transfer_records = records[:TRANSFER_HISTORY_LIMIT]
    TRANSFER_CODES_PATH.write_text(
        json.dumps(state.transfer_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def push_transfer_record(record: dict[str, Any]) -> dict[str, Any]:
    records = list(state.transfer_records or [])
    entry = normalize_transfer_record(
        {
            "id": _new_transfer_record_id(),
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            **record,
        }
    )
    records.insert(0, entry)
    state.transfer_records = records[:TRANSFER_HISTORY_LIMIT]
    persist_transfer_records()
    return entry


def _transfer_record_matches_fallback(row: dict[str, Any], fallback: dict[str, Any]) -> bool:
    checks = 0
    comparable_fields = (
        "timestamp",
        "transfer_code",
        "confirmation_code",
        "kind",
        "country",
        "game_version",
        "path",
        "inquiry_code",
    )
    for field in comparable_fields:
        expected = str(fallback.get(field, "") or "").strip()
        if not expected:
            continue
        checks += 1
        actual = str(row.get(field, "") or "").strip()
        if field in {"kind", "country"}:
            if actual.lower() != expected.lower():
                return False
        else:
            if actual != expected:
                return False
    return checks > 0


def resolve_transfer_record_id(record_id: str, fallback: dict[str, Any] | None = None) -> str:
    rid = str(record_id or "").strip()
    records = list(state.transfer_records or [])
    if rid:
        for row in records:
            if str(row.get("id", "")).strip() == rid:
                return rid
        raise RuntimeError("Transfer history record not found.")

    if isinstance(fallback, dict):
        for idx, row in enumerate(records):
            if not _transfer_record_matches_fallback(row, fallback):
                continue
            existing = str(row.get("id", "")).strip()
            if existing:
                return existing
            row["id"] = _new_transfer_record_id()
            state.transfer_records = [normalize_transfer_record(item) for item in records][:TRANSFER_HISTORY_LIMIT]
            persist_transfer_records()
            return str(state.transfer_records[idx].get("id", "")).strip()

    raise RuntimeError("Transfer history record id is required.")


def update_transfer_record(record_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    rid = str(record_id or "").strip()
    if not rid:
        raise RuntimeError("Transfer history record id is required.")
    records = list(state.transfer_records or [])
    for idx, current in enumerate(records):
        if str(current.get("id", "")) != rid:
            continue
        next_record = dict(current)
        editable_fields = {
            "kind",
            "country",
            "game_version",
            "transfer_code",
            "confirmation_code",
            "path",
            "inquiry_code",
            "note",
            "needs_upload",
            "uploaded_at",
            "uploaded_by",
        }
        for key in editable_fields:
            if key in patch:
                next_record[key] = patch.get(key)
        next_record["id"] = str(current.get("id", rid))
        next_record["timestamp"] = str(current.get("timestamp", ""))
        normalized = normalize_transfer_record(next_record)
        records[idx] = normalized
        state.transfer_records = records[:TRANSFER_HISTORY_LIMIT]
        persist_transfer_records()
        return normalized
    raise RuntimeError("Transfer history record not found.")


def delete_transfer_record(record_id: str) -> None:
    rid = str(record_id or "").strip()
    if not rid:
        raise RuntimeError("Transfer history record id is required.")
    records = list(state.transfer_records or [])
    filtered = [row for row in records if str(row.get("id", "")) != rid]
    if len(filtered) == len(records):
        raise RuntimeError("Transfer history record not found.")
    state.transfer_records = filtered[:TRANSFER_HISTORY_LIMIT]
    persist_transfer_records()


def mark_matching_downloads_uploaded(sf: core.SaveFile, upload_record_id: str) -> int:
    records = list(state.transfer_records or [])
    inquiry_code = str(getattr(sf, "inquiry_code", "") or "").strip()
    loaded_path = str(state.loaded_path or "").strip()
    uploaded_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    changed = 0
    for row in records:
        if str(row.get("id", "")) == str(upload_record_id):
            continue
        if row.get("kind") != "download" or not bool(row.get("needs_upload", False)):
            continue
        same_inquiry = bool(inquiry_code and str(row.get("inquiry_code", "")).strip() == inquiry_code)
        same_path = bool(loaded_path and str(row.get("path", "")).strip() == loaded_path)
        if not (same_inquiry or same_path):
            continue
        row["needs_upload"] = False
        row["uploaded_at"] = uploaded_at
        row["uploaded_by"] = str(upload_record_id)
        changed += 1
    if changed:
        state.transfer_records = [normalize_transfer_record(row) for row in records][:TRANSFER_HISTORY_LIMIT]
        persist_transfer_records()
    return changed


def build_transfer_backup_payload() -> dict[str, Any]:
    return {
        "version": TRANSFER_BACKUP_VERSION,
        "exported_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "records": list(state.transfer_records or []),
    }


def parse_game_version(raw: Any, fallback: core.GameVersion) -> core.GameVersion:
    text = str(raw or "").strip()
    if not text:
        return fallback
    try:
        if text.isdigit():
            return core.GameVersion(int(text))
        return core.GameVersion.from_string(text)
    except Exception:
        return fallback


def history_state() -> dict[str, Any]:
    size = len(state.history or [])
    index = state.history_index
    can_undo = bool(size > 0 and index > 0)
    can_redo = bool(size > 0 and index < size - 1)
    return {
        "size": size,
        "index": index,
        "can_undo": can_undo,
        "can_redo": can_redo,
        "safe_mode": bool(state.safe_mode),
    }


def snapshot_save(sf: core.SaveFile) -> dict[str, Any]:
    return sf.to_dict()


def restore_snapshot(snapshot: dict[str, Any]) -> core.SaveFile:
    restored = core.SaveFile.from_dict(snapshot, warn=False)
    state.save_file = restored
    state.name_cache = {}
    return restored


def reset_history(sf: core.SaveFile, reason: str = "load") -> None:
    snap = snapshot_save(sf)
    state.history = [snap]
    state.history_reasons = [reason]
    state.history_index = 0


def push_history(reason: str) -> None:
    sf = ensure_loaded()
    snap = snapshot_save(sf)
    history = state.history or []
    reasons = state.history_reasons or []
    index = state.history_index

    if index < len(history) - 1:
        history = history[: index + 1]
        reasons = reasons[: index + 1]

    history.append(snap)
    reasons.append(reason)

    if len(history) > state.history_limit:
        overflow = len(history) - state.history_limit
        history = history[overflow:]
        reasons = reasons[overflow:]

    state.history = history
    state.history_reasons = reasons
    state.history_index = len(history) - 1


def clone_save(sf: core.SaveFile) -> core.SaveFile:
    return core.SaveFile.from_dict(sf.to_dict(), warn=False)


def load_mygamatoto_index() -> None:
    if not INDEX_PATH.exists():
        return
    try:
        obj = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            state.mygamatoto_index = {str(k): str(v) for k, v in obj.items()}
    except Exception:
        state.mygamatoto_index = {}


def sync_mygamatoto_index() -> int:
    resp = requests.get("https://onestoppress.com/api/allcats", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    sample = data.get("sampledata", [])
    index: dict[str, str] = {}
    for row in sample:
        number = str(row.get("number", "")).strip()
        name = str(row.get("name", "")).strip()
        if number:
            index[number] = clean_name(name)
    if not index:
        raise RuntimeError("MyGamatoto response had no cat data.")
    state.mygamatoto_index = index
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    state.name_cache = {}
    return len(index)


def get_cat_name(cat: core.Cat) -> str:
    if state.name_cache is None:
        state.name_cache = {}
    cached = state.name_cache.get(cat.id)
    if cached is not None:
        return cached

    number = cat_number(cat)
    if state.mygamatoto_index:
        mg_name = state.mygamatoto_index.get(number)
        if mg_name:
            state.name_cache[cat.id] = clean_name(mg_name)
            return state.name_cache[cat.id]

    sf = ensure_loaded()
    try:
        names = cat.get_names_cls(sf) or []
        name = names[0] if names else f"Cat {cat.id}"
    except Exception:
        name = f"Cat {cat.id}"
    state.name_cache[cat.id] = clean_name(name)
    return state.name_cache[cat.id]


def is_hidden_cat_name(name: str) -> bool:
    """Hide known placeholder/debug cats from normal editor lists."""
    return "cheetah" in str(name or "").strip().lower()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def story_progress_stats(sf: core.SaveFile) -> dict[str, Any]:
    chapter_names = [
        "EoC Ch.1",
        "EoC Ch.2",
        "EoC Ch.3",
        "ItF Ch.1",
        "ItF Ch.2",
        "ItF Ch.3",
        "CotC Ch.1",
        "CotC Ch.2",
        "CotC Ch.3",
    ]

    rows: list[dict[str, Any]] = []
    total_clear = 0
    done_clear = 0
    total_treasure = 0
    superior_treasure = 0

    for i, chapter in enumerate(getattr(sf.story, "chapters", []) or []):
        stages = getattr(chapter, "stages", []) or []
        clear_total = min(48, len(stages))
        treasure_total = min(49, len(stages))
        clear_done = sum(
            1 for stage in stages[:clear_total] if safe_int(getattr(stage, "clear_times", 0)) > 0
        )
        superior_done = sum(
            1 for stage in stages[:treasure_total] if safe_int(getattr(stage, "treasure", 0)) >= 3
        )
        rows.append(
            {
                "index": i,
                "name": chapter_names[i] if i < len(chapter_names) else f"Chapter {i + 1}",
                "cleared": clear_done,
                "clear_total": clear_total,
                "superior": superior_done,
                "treasure_total": treasure_total,
            }
        )
        total_clear += clear_total
        done_clear += clear_done
        total_treasure += treasure_total
        superior_treasure += superior_done

    saga_defs = [("EoC", 0, 3), ("ItF", 3, 6), ("CotC", 6, 9)]
    saga_rows: list[dict[str, Any]] = []
    for label, start, end in saga_defs:
        subset = rows[start:end]
        if not subset:
            continue
        saga_clear_total = sum(r["clear_total"] for r in subset)
        saga_clear_done = sum(r["cleared"] for r in subset)
        saga_treasure_total = sum(r["treasure_total"] for r in subset)
        saga_superior_done = sum(r["superior"] for r in subset)
        saga_rows.append(
            {
                "name": label,
                "cleared": saga_clear_done,
                "clear_total": saga_clear_total,
                "superior": saga_superior_done,
                "treasure_total": saga_treasure_total,
            }
        )

    return {
        "chapters": rows,
        "sagas": saga_rows,
        "clear_total": total_clear,
        "clear_done": done_clear,
        "treasure_total": total_treasure,
        "superior_done": superior_treasure,
    }


def lineup_stats(sf: core.SaveFile) -> tuple[int, int]:
    total = safe_int(
        getattr(sf.lineups, "slot_names_length", len(getattr(sf.lineups, "slots", [])) or 15)
    )
    unlocked = safe_int(getattr(sf.lineups, "unlocked_slots", 0))
    unlocked = max(0, min(unlocked, max(total, 0)))
    return unlocked, max(total, 0)


def enemy_guide_stats(sf: core.SaveFile) -> tuple[int, int]:
    guide = list(getattr(sf, "enemy_guide", []) or [])
    total = len(guide)
    try:
        names = list(getattr(core.core_data.get_enemy_names(sf), "names", []) or [])
        total = max(total, len(names))
    except Exception:
        pass
    unlocked = sum(1 for x in guide if safe_int(x, 0) != 0)
    return unlocked, total


def cat_guide_stats(sf: core.SaveFile) -> tuple[int, int]:
    cats = list(getattr(sf.cats, "cats", []) or [])
    total = len(cats)
    claimed = sum(1 for cat in cats if bool(getattr(cat, "catguide_collected", False)))
    return claimed, total


def enemy_guide_payload(sf: core.SaveFile, query: str = "", filter_mode: str = "All") -> dict[str, Any]:
    guide = list(getattr(sf, "enemy_guide", []) or [])
    names_obj: core.EnemyNames | None = None
    names_raw: list[str] = []
    try:
        names_obj = core.core_data.get_enemy_names(sf)
        names_raw = list(getattr(names_obj, "names", []) or [])
    except Exception:
        names_obj = None
        names_raw = []

    total = max(len(guide), len(names_raw))
    q = query.strip().lower()
    mode = filter_mode.strip().lower()

    valid_ids: set[int] = set()
    try:
        valid = core.EnemyDictionary(sf).get_valid_enemies()
        if valid is not None:
            valid_ids = {safe_int(x, -1) for x in valid if safe_int(x, -1) >= 0}
    except Exception:
        valid_ids = set()
    has_valid_ids = len(valid_ids) > 0

    rows: list[dict[str, Any]] = []
    for enemy_id in range(total):
        unlocked = bool(enemy_id < len(guide) and safe_int(guide[enemy_id], 0) != 0)
        if mode in {"unlocked", "owned"} and not unlocked:
            continue
        if mode in {"missing", "locked"} and unlocked:
            continue
        if mode == "valid" and has_valid_ids and enemy_id not in valid_ids:
            continue
        if mode == "invalid" and has_valid_ids and enemy_id in valid_ids:
            continue

        try:
            raw_name = names_obj.get_name(enemy_id) if names_obj is not None else None
        except Exception:
            raw_name = None
        name = clean_name(raw_name or f"Enemy {enemy_id}")
        if q and q not in f"{enemy_id} {name}".lower():
            continue

        rows.append(
            {
                "id": enemy_id,
                "name": name,
                "unlocked": unlocked,
                "valid": (enemy_id in valid_ids) if has_valid_ids else True,
                "editable": enemy_id < len(guide),
                "image_url": enemy_icon_url(enemy_id),
            }
        )

    unlocked_count, total_count = enemy_guide_stats(sf)
    return {
        "ok": True,
        "enemies": rows,
        "enemy_guide": {"unlocked": unlocked_count, "total": total_count},
        "summary": summary(sf),
    }


def dashboard_payload(sf: core.SaveFile) -> dict[str, Any]:
    sp = story_progress_stats(sf)
    lineups_unlocked, lineups_total = lineup_stats(sf)
    enemy_unlocked, enemy_total = enemy_guide_stats(sf)
    catguide_claimed, catguide_total = cat_guide_stats(sf)
    user_rank = safe_int(sf.calculate_user_rank())
    trophy_owned = len(getattr(sf.medals, "medal_data_1", []) or [])

    def ratio(done: int, total: int) -> float:
        return (float(done) / float(total)) if total > 0 else 0.0

    cards = [
        {
            "id": "user_rank",
            "label": "User Rank",
            "value": user_rank,
            "subtitle": "Calculated from units + base upgrades",
        },
        {
            "id": "lineups",
            "label": "Lineups",
            "value": f"{lineups_unlocked}/{lineups_total}",
            "percent": ratio(lineups_unlocked, lineups_total),
        },
        {
            "id": "story_clear",
            "label": "Story Clears",
            "value": f"{sp['clear_done']}/{sp['clear_total']}",
            "percent": ratio(sp["clear_done"], sp["clear_total"]),
        },
        {
            "id": "superior_treasures",
            "label": "Superior Treasures",
            "value": f"{sp['superior_done']}/{sp['treasure_total']}",
            "percent": ratio(sp["superior_done"], sp["treasure_total"]),
        },
        {
            "id": "medals",
            "label": "Meow Medals",
            "value": trophy_owned,
            "subtitle": "Affects lineup unlock thresholds",
        },
        {
            "id": "enemy_guide",
            "label": "Enemy Guide",
            "value": f"{enemy_unlocked}/{enemy_total}",
            "percent": ratio(enemy_unlocked, enemy_total),
        },
        {
            "id": "cat_guide",
            "label": "Cat Guide Claimed",
            "value": f"{catguide_claimed}/{catguide_total}",
            "percent": ratio(catguide_claimed, catguide_total),
        },
    ]
    return {
        "ok": True,
        "cards": cards,
        "story_sagas": sp["sagas"],
        "story_chapters": sp["chapters"],
    }


def base_upgrades_payload(sf: core.SaveFile) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    names_o = core.core_data.get_gatya_item_names(sf)
    items = core.core_data.get_gatya_item_buy(sf).get_by_category(2) or []
    ability_data = core.core_data.get_ability_data(sf)
    valid = sf.special_skills.get_valid_skills()

    for i, skill in enumerate(valid):
        item_id = items[i].id if i < len(items) else None
        fallback_item_id = BASE_UPGRADE_ICON_FALLBACK_IDS.get(i)
        resolved_item_id = item_id if item_id is not None else fallback_item_id
        raw_name = names_o.get_name(resolved_item_id) if resolved_item_id is not None else None
        ability = ability_data.get_ability_data_item(i) if ability_data is not None else None
        max_base_raw = safe_int(getattr(ability, "max_base_level", 0))
        max_plus = safe_int(getattr(ability, "max_plus_level", 0))
        rows.append(
            {
                "id": i,
                "item_id": resolved_item_id,
                "icon_url": gatyaitem_icon_url(resolved_item_id),
                "name": clean_name(raw_name or f"Base Upgrade {i + 1}"),
                "base": safe_int(skill.upgrade.base) + 1,
                "plus": safe_int(skill.upgrade.plus),
                "max_base": max(1, max_base_raw),
                "max_plus": max(0, max_plus),
            }
        )
    return {"ok": True, "upgrades": rows}


def base_cannons_payload(sf: core.SaveFile) -> dict[str, Any]:
    ototo = getattr(sf, "ototo", None)
    cannons_obj = getattr(ototo, "cannons", None) if ototo is not None else None
    if cannons_obj is None:
        return {"ok": True, "cannons": [], "selected_parts": [0, 0, 0]}

    recipe = ototo_data.CastleRecipeUnlock(sf)
    descriptions = ototo_data.CannonDescriptions(sf)
    rows: list[dict[str, Any]] = []
    cannon_map = dict(getattr(cannons_obj, "cannons", {}) or {})

    for cannon_id, cannon in sorted(cannon_map.items(), key=lambda kv: safe_int(kv[0], 0)):
        cid = safe_int(cannon_id, 0)
        description = descriptions.get_cannon_description(cid) if descriptions is not None else None
        part_names = (
            description.get_part_names()
            if description is not None
            else ["Effect", "Foundation", "Style"]
        )
        levels = list(getattr(cannon, "levels", []) or [])
        while len(levels) < 3:
            levels.append(0)

        parts: list[dict[str, Any]] = []
        for part_id in range(3):
            max_level = recipe.get_max_level(cid, part_id) if recipe is not None else None
            if max_level is None:
                max_level = recipe.get_max_part_level(part_id) if recipe is not None else None
            max_level_i = max(0, safe_int(max_level, levels[part_id]))
            parts.append(
                {
                    "part_id": part_id,
                    "name": str(part_names[part_id]) if part_id < len(part_names) else f"Part {part_id + 1}",
                    "level": max(0, safe_int(levels[part_id], 0)),
                    "max_level": max_level_i,
                }
            )

        rows.append(
            {
                "cannon_id": cid,
                "name": clean_name(
                    description.get_cannon_name() if description is not None else f"Cannon {cid}"
                ),
                "development": max(0, safe_int(getattr(cannon, "development", 0), 0)),
                "max_development": 3,
                "parts": parts,
            }
        )

    selected_parts = [0, 0, 0]
    selected = list(getattr(cannons_obj, "selected_parts", []) or [])
    if selected:
        first = list(selected[0] or [])
        while len(first) < 3:
            first.append(0)
        selected_parts = [max(0, safe_int(first[i], 0)) for i in range(3)]

    return {"ok": True, "cannons": rows, "selected_parts": selected_parts}


def validation_payload(sf: core.SaveFile) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    max_mgr = core.core_data.max_value_manager

    resource_caps: list[tuple[str, core.MaxValueType]] = [
        ("catfood", core.MaxValueType.CATFOOD),
        ("xp", core.MaxValueType.XP),
        ("np", core.MaxValueType.NP),
        ("normal_tickets", core.MaxValueType.NORMAL_TICKETS),
        ("rare_tickets", core.MaxValueType.RARE_TICKETS),
        ("platinum_tickets", core.MaxValueType.PLATINUM_TICKETS),
        ("legend_tickets", core.MaxValueType.LEGEND_TICKETS),
        ("leadership", core.MaxValueType.LEADERSHIP),
    ]
    near_cap_count = 0
    for field, cap_key in resource_caps:
        value = safe_int(getattr(sf, field, 0))
        cap = max(0, safe_int(max_mgr.get(cap_key)))
        if value < 0 or value > cap:
            checks.append(
                {
                    "severity": "warning",
                    "domain": "resources",
                    "message": f"{field} is out of range ({value}, cap {cap}).",
                }
            )
        if cap > 0 and value >= int(cap * 0.95):
            near_cap_count += 1
            checks.append(
                {
                    "severity": "risk",
                    "domain": "ban_risk",
                    "message": f"{field} is near hard cap ({value}/{cap}).",
                }
            )
        if cap > 0 and value >= cap:
            checks.append(
                {
                    "severity": "risk",
                    "domain": "ban_risk",
                    "message": f"{field} is exactly at hard cap ({value}/{cap}).",
                }
            )

    user_rank = safe_int(sf.calculate_user_rank())
    if near_cap_count >= 4 and user_rank < 1500:
        checks.append(
            {
                "severity": "risk",
                "domain": "ban_risk",
                "message": "Many core resources are near cap while User Rank is still low.",
            }
        )

    invalid_form = 0
    invalid_fourth = 0
    for cat in sf.cats.cats:
        total_forms = get_cat_total_forms(sf, cat)
        if safe_int(cat.current_form) >= total_forms:
            invalid_form += 1
        if total_forms < 4 and safe_int(cat.fourth_form) > 0:
            invalid_fourth += 1
    if invalid_form:
        checks.append(
            {
                "severity": "warning",
                "domain": "cats",
                "message": f"{invalid_form} cats have a current form index above their form count.",
            }
        )
    if invalid_fourth:
        checks.append(
            {
                "severity": "warning",
                "domain": "cats",
                "message": f"{invalid_fourth} cats have 4th-form flags but no 4-form support.",
            }
        )

    locked_but_modified = 0
    for cat in sf.cats.cats:
        if bool(cat.unlocked):
            continue
        if (
            safe_int(cat.upgrade.base) > 0
            or safe_int(cat.upgrade.plus) > 0
            or safe_int(cat.current_form) > 0
            or safe_int(cat.unlocked_forms) > 0
            or safe_int(cat.fourth_form) > 0
        ):
            locked_but_modified += 1
    if locked_but_modified:
        checks.append(
            {
                "severity": "warning",
                "domain": "cats",
                "message": f"{locked_but_modified} locked cats have modified levels/forms.",
            }
        )

    cat_level_overflow = 0
    cat_plus_overflow = 0
    for cat in sf.cats.cats:
        if not bool(cat.unlocked):
            continue
        try:
            power = core.PowerUpHelper(cat, sf)
            max_base = max(0, safe_int(power.get_max_possible_base()))
            max_plus = max(0, safe_int(power.get_max_possible_plus()))
            if safe_int(cat.upgrade.base) > max_base:
                cat_level_overflow += 1
            if safe_int(cat.upgrade.plus) > max_plus:
                cat_plus_overflow += 1
        except Exception:
            continue
    if cat_level_overflow:
        checks.append(
            {
                "severity": "risk",
                "domain": "ban_risk",
                "message": f"{cat_level_overflow} cats exceed maximum base level limits.",
            }
        )
    if cat_plus_overflow:
        checks.append(
            {
                "severity": "risk",
                "domain": "ban_risk",
                "message": f"{cat_plus_overflow} cats exceed maximum plus level limits.",
            }
        )

    talent_overflow = 0
    try:
        talent_data = sf.cats.read_talent_data(sf)
        if talent_data is not None:
            for cat in sf.cats.cats:
                talents = list(getattr(cat, "talents", []) or [])
                if not talents:
                    continue
                for talent in talents:
                    skill = talent_data.get_skill_from_cat(cat.id, safe_int(getattr(talent, "id", -1)))
                    max_level = max(1, safe_int(getattr(skill, "max_lv", 1), 1)) if skill is not None else None
                    if max_level is not None and safe_int(getattr(talent, "level", 0)) > max_level:
                        talent_overflow += 1
        if talent_overflow:
            checks.append(
                {
                    "severity": "risk",
                    "domain": "ban_risk",
                    "message": f"{talent_overflow} talents exceed their legal max level.",
                }
            )
    except Exception:
        pass

    over_treasure = 0
    superior_without_clear = 0
    for chapter in getattr(sf.story, "chapters", []) or []:
        stages = (getattr(chapter, "stages", []) or [])[:49]
        for idx, stage in enumerate(stages):
            if safe_int(getattr(stage, "treasure", 0)) > 3:
                over_treasure += 1
            if idx < 48 and safe_int(getattr(stage, "treasure", 0)) > 0 and safe_int(getattr(stage, "clear_times", 0)) <= 0:
                superior_without_clear += 1
    if over_treasure:
        checks.append(
            {
                "severity": "warning",
                "domain": "progress",
                "message": f"{over_treasure} story treasure entries exceed Superior tier (3).",
            }
        )
    if superior_without_clear:
        checks.append(
            {
                "severity": "warning",
                "domain": "progress",
                "message": f"{superior_without_clear} stages have treasures without stage clear progress.",
            }
        )

    enemy_unlocked, enemy_total = enemy_guide_stats(sf)
    sp = story_progress_stats(sf)
    if enemy_total > 0 and enemy_unlocked >= int(enemy_total * 0.95) and safe_int(sp.get("clear_done", 0)) < 40:
        checks.append(
            {
                "severity": "risk",
                "domain": "ban_risk",
                "message": "Enemy guide is nearly fully unlocked while story progress is very low.",
            }
        )

    catguide_claimed, catguide_total = cat_guide_stats(sf)
    if catguide_total > 0 and catguide_claimed >= int(catguide_total * 0.9) and safe_int(sp.get("clear_done", 0)) < 40:
        checks.append(
            {
                "severity": "risk",
                "domain": "ban_risk",
                "message": "Cat guide is nearly fully claimed while story progress is very low.",
            }
        )

    try:
        trophy_owned = len(getattr(sf.medals, "medal_data_1", []) or [])
        if trophy_owned >= 250 and safe_int(sp.get("clear_done", 0)) < 60:
            checks.append(
                {
                    "severity": "risk",
                    "domain": "ban_risk",
                    "message": "Meow medal count is very high compared to story progression.",
                }
            )
    except Exception:
        pass

    try:
        ability_data = core.core_data.get_ability_data(sf)
        skills = list(sf.special_skills.get_valid_skills() or [])
        if ability_data is not None and skills:
            maxed_count = 0
            for i, skill in enumerate(skills):
                ability = ability_data.get_ability_data_item(i)
                if ability is None:
                    continue
                max_base = max(0, safe_int(getattr(ability, "max_base_level", 1)) - 1)
                max_plus = max(0, safe_int(getattr(ability, "max_plus_level", 0)))
                if safe_int(skill.upgrade.base) >= max_base and safe_int(skill.upgrade.plus) >= max_plus:
                    maxed_count += 1
            if maxed_count >= int(len(skills) * 0.9) and safe_int(sp.get("clear_done", 0)) < 30:
                checks.append(
                    {
                        "severity": "risk",
                        "domain": "ban_risk",
                        "message": "Base upgrades are almost fully maxed while story progress is low.",
                    }
                )
    except Exception:
        pass

    try:
        levels = core.core_data.get_gamatoto_levels(sf)
        max_helpers = safe_int(levels.get_total_helpers(), 0) if levels is not None else 0
        max_level = safe_int(levels.get_max_level(), 0) if levels is not None else 0
        helper_count = len(getattr(sf.gamatoto.helpers, "helpers", []) or [])
        current_level = safe_int(getattr(levels.get_level_from_xp(safe_int(sf.gamatoto.xp)), "level", 0), 0) if levels is not None else 0
        if max_helpers > 0 and helper_count > max_helpers:
            checks.append(
                {
                    "severity": "warning",
                    "domain": "gamatoto",
                    "message": f"Gamatoto helper slots exceed limit ({helper_count}/{max_helpers}).",
                }
            )
        if max_level > 0 and current_level > max_level:
            checks.append(
                {
                    "severity": "risk",
                    "domain": "ban_risk",
                    "message": f"Gamatoto level exceeds max ({current_level}/{max_level}).",
                }
            )
    except Exception:
        pass

    if not checks:
        checks.append({"severity": "ok", "domain": "integrity", "message": "No issues detected."})

    return {"ok": True, "checks": checks}


def diff_payload(before: core.SaveFile, after: core.SaveFile) -> dict[str, Any]:
    before_s = summary(before)
    after_s = summary(after)
    tracked = [
        ("catfood", "Catfood"),
        ("xp", "XP"),
        ("np", "NP"),
        ("normal_tickets", "Normal Tickets"),
        ("rare_tickets", "Rare Tickets"),
        ("platinum_tickets", "Platinum Tickets"),
        ("legend_tickets", "Legend Tickets"),
        ("leadership", "Leadership"),
        ("cats_unlocked", "Cats Unlocked"),
        ("trophies_owned", "Trophies"),
        ("user_rank", "User Rank"),
        ("story_cleared_stages", "Story Clears"),
        ("superior_treasures", "Superior Treasures"),
    ]
    summary_changes: list[dict[str, Any]] = []
    for key, label in tracked:
        b = before_s.get(key)
        a = after_s.get(key)
        if b != a:
            summary_changes.append({"key": key, "label": label, "before": b, "after": a})

    changed = 0
    unlocked = 0
    levels = 0
    forms = 0
    fourth = 0
    for b_cat, a_cat in zip(before.cats.cats, after.cats.cats):
        cat_changed = False
        if bool(b_cat.unlocked) != bool(a_cat.unlocked):
            unlocked += 1
            cat_changed = True
        if safe_int(b_cat.upgrade.base) != safe_int(a_cat.upgrade.base) or safe_int(
            b_cat.upgrade.plus
        ) != safe_int(a_cat.upgrade.plus):
            levels += 1
            cat_changed = True
        if safe_int(b_cat.current_form) != safe_int(a_cat.current_form) or safe_int(
            b_cat.unlocked_forms
        ) != safe_int(a_cat.unlocked_forms):
            forms += 1
            cat_changed = True
        if safe_int(b_cat.fourth_form) != safe_int(a_cat.fourth_form):
            fourth += 1
            cat_changed = True
        if cat_changed:
            changed += 1

    def changed_indexes(before_l: list[Any], after_l: list[Any]) -> int:
        return sum(1 for i in range(min(len(before_l), len(after_l))) if before_l[i] != after_l[i])

    before_mats = [safe_int(x.amount) for x in before.ototo.base_materials.materials]
    after_mats = [safe_int(x.amount) for x in after.ototo.base_materials.materials]
    before_battle = [safe_int(x.amount) for x in before.battle_items.items]
    after_battle = [safe_int(x.amount) for x in after.battle_items.items]

    inventory_changes = {
        "catseyes": changed_indexes(before.catseyes, after.catseyes),
        "catfruit": changed_indexes(before.catfruit, after.catfruit),
        "catamins": changed_indexes(before.catamins, after.catamins),
        "materials": changed_indexes(before_mats, after_mats),
        "battle_items": changed_indexes(before_battle, after_battle),
    }

    before_story = story_progress_stats(before)
    after_story = story_progress_stats(after)
    story_changes = {
        "clear_changed": safe_int(after_story["clear_done"]) - safe_int(before_story["clear_done"]),
        "superior_changed": safe_int(after_story["superior_done"])
        - safe_int(before_story["superior_done"]),
    }

    return {
        "summary_changes": summary_changes,
        "cats": {
            "changed": changed,
            "unlock_toggles": unlocked,
            "level_changes": levels,
            "form_changes": forms,
            "fourth_form_changes": fourth,
        },
        "inventory": inventory_changes,
        "story": story_changes,
    }


def summary(sf: core.SaveFile) -> dict[str, Any]:
    unlocked = sum(1 for c in sf.cats.cats if c.unlocked)
    user_rank = safe_int(sf.calculate_user_rank())
    lineups_unlocked, lineups_total = lineup_stats(sf)
    enemy_unlocked, enemy_total = enemy_guide_stats(sf)
    catguide_claimed, catguide_total = cat_guide_stats(sf)
    sp = story_progress_stats(sf)
    trophy_owned = 0
    trophy_total = 0
    try:
        trophy_owned = len(getattr(sf.medals, "medal_data_1", []))
        medal_names = core.core_data.get_medal_names(sf)
        names = getattr(medal_names, "medal_names", None)
        if isinstance(names, list):
            trophy_total = sum(1 for row in names if isinstance(row, list) and len(row) > 0)
        else:
            trophy_total = trophy_owned
    except Exception:
        trophy_total = trophy_owned
    return {
        "path": str(state.loaded_path) if state.loaded_path else "",
        "inquiry_code": sf.inquiry_code,
        "country": str(sf.cc),
        "game_version": sf.game_version.to_string(),
        "cats_unlocked": unlocked,
        "cats_total": len(sf.cats.cats),
        "catfood": sf.catfood,
        "xp": sf.xp,
        "np": sf.np,
        "normal_tickets": sf.normal_tickets,
        "rare_tickets": sf.rare_tickets,
        "platinum_tickets": sf.platinum_tickets,
        "legend_tickets": sf.legend_tickets,
        "leadership": sf.leadership,
        "trophies_owned": trophy_owned,
        "trophies_total": trophy_total,
        "user_rank": user_rank,
        "lineups_unlocked": lineups_unlocked,
        "lineups_total": lineups_total,
        "enemy_guide_unlocked": enemy_unlocked,
        "enemy_guide_total": enemy_total,
        "cat_guide_claimed": catguide_claimed,
        "cat_guide_total": catguide_total,
        "story_cleared_stages": safe_int(sp["clear_done"]),
        "story_total_stages": safe_int(sp["clear_total"]),
        "superior_treasures": safe_int(sp["superior_done"]),
        "total_treasures": safe_int(sp["treasure_total"]),
        "history": history_state(),
    }


def story_chapter_names() -> list[str]:
    return [
        "EoC Ch.1",
        "EoC Ch.2",
        "EoC Ch.3",
        "ItF Ch.1",
        "ItF Ch.2",
        "ItF Ch.3",
        "CotC Ch.1",
        "CotC Ch.2",
        "CotC Ch.3",
        "Chapter 10",
    ]


def story_editor_payload(sf: core.SaveFile) -> dict[str, Any]:
    names = story_chapter_names()
    rows: list[dict[str, Any]] = []
    chapters = list(getattr(sf.story, "chapters", []) or [])
    for i, chapter in enumerate(chapters):
        stages = list(getattr(chapter, "stages", []) or [])
        clear_total = min(48, len(stages))
        treasure_total = min(49, len(stages))
        clear_done = sum(1 for stage in stages[:clear_total] if safe_int(getattr(stage, "clear_times", 0)) > 0)
        superior_done = sum(1 for stage in stages[:treasure_total] if safe_int(getattr(stage, "treasure", 0)) >= 3)
        rows.append(
            {
                "index": i,
                "name": names[i] if i < len(names) else f"Chapter {i + 1}",
                "clear_total": clear_total,
                "cleared": clear_done,
                "treasure_total": treasure_total,
                "superior": superior_done,
                "progress": safe_int(getattr(chapter, "progress", 0)),
            }
        )
    return {"ok": True, "chapters": rows, "summary": summary(sf)}


def apply_story_chapter_values(chapter: core.Chapter, clear_count: int, superior_count: int, clear_amount: int = 1) -> None:
    stages = list(getattr(chapter, "stages", []) or [])
    clear_total = min(48, len(stages))
    treasure_total = min(49, len(stages))
    clear_count = max(0, min(clear_count, clear_total))
    superior_count = max(0, min(superior_count, treasure_total))

    for i, stage in enumerate(stages[:clear_total]):
        if i < clear_count:
            stage.clear_times = max(1, clear_amount)
        else:
            stage.clear_times = 0

    for i, stage in enumerate(stages[:treasure_total]):
        stage.treasure = 3 if i < superior_count else 0

    chapter.progress = max(0, min(clear_count, clear_total))


def gamatoto_payload(sf: core.SaveFile) -> dict[str, Any]:
    gam = sf.gamatoto
    levels = core.core_data.get_gamatoto_levels(sf)
    members = core.core_data.get_gamatoto_members_name(sf)
    current_level = levels.get_level_from_xp(safe_int(gam.xp)) if levels is not None else None
    max_level = levels.get_max_level() if levels is not None else None
    max_helpers = levels.get_total_helpers() if levels is not None else None
    helper_rows: list[dict[str, Any]] = []
    helper_ids = [safe_int(helper.id, -1) for helper in list(getattr(gam.helpers, "helpers", []) or [])]

    target_len = max(len(helper_ids), safe_int(max_helpers, 0))
    for slot in range(target_len):
        member_id = helper_ids[slot] if slot < len(helper_ids) else -1
        member = members.get_member(member_id) if members is not None and member_id >= 0 else None
        helper_rows.append(
            {
                "slot": slot,
                "id": member_id,
                "name": clean_name(member.name) if member is not None else ("Empty" if member_id < 0 else f"Member {member_id}"),
                "rarity": safe_int(getattr(member, "rarity", 0)),
                "bonus": safe_int(getattr(member, "bonus", 0)),
            }
        )

    return {
        "ok": True,
        "summary": summary(sf),
        "current_level": safe_int(getattr(current_level, "level", 1), 1),
        "max_level": safe_int(max_level, 1),
        "max_helpers": safe_int(max_helpers, max(0, len(helper_rows))),
        "xp": safe_int(gam.xp),
        "remaining_seconds": float(getattr(gam, "remaining_seconds", 0.0)),
        "return_flag": bool(getattr(gam, "return_flag", False)),
        "dest_id": safe_int(getattr(gam, "dest_id", 0)),
        "recon_length": safe_int(getattr(gam, "recon_length", 0)),
        "skin": safe_int(getattr(gam, "skin", 0)),
        "is_ad_present": bool(getattr(gam, "is_ad_present", False)),
        "helpers": helper_rows,
    }


def set_gamatoto_level(sf: core.SaveFile, level: int) -> int:
    levels = core.core_data.get_gamatoto_levels(sf)
    if levels is None:
        return max(0, level)
    max_level = safe_int(levels.get_max_level(), 1)
    target = max(1, min(level, max_level))
    xp = levels.get_xp_from_level(target)
    if xp is None:
        return safe_int(sf.gamatoto.xp)
    return safe_int(xp)


def cat_talents_payload(sf: core.SaveFile, cat: core.Cat) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    talents = list(getattr(cat, "talents", []) or [])
    talent_data = sf.cats.read_talent_data(sf)

    for talent in talents:
        talent_id = safe_int(getattr(talent, "id", -1), -1)
        if talent_id < 0:
            continue
        level = max(0, safe_int(getattr(talent, "level", 0)))
        max_level = max(1, level)
        name = f"Talent {talent_id}"
        if talent_data is not None:
            skill = talent_data.get_skill_from_cat(cat.id, talent_id)
            if skill is not None:
                max_level = max(1, safe_int(getattr(skill, "max_lv", 1), 1))
                skill_name = talent_data.get_skill_name(getattr(skill, "text_id", 0))
                if skill_name:
                    name = clean_name(skill_name.split("<br>")[0])
        rows.append(
            {
                "id": talent_id,
                "name": name,
                "level": min(level, max_level),
                "max_level": max_level,
            }
        )

    rows.sort(key=lambda row: int(row["id"]))
    return {"ok": True, "cat_id": int(cat.id), "talents": rows}


def get_cat_total_forms(sf: core.SaveFile, cat: core.Cat) -> int:
    try:
        pic_book = sf.cats.read_nyanko_picture_book(sf)
        pb_cat = pic_book.get_cat(cat.id) if pic_book is not None else None
        if pb_cat is not None:
            return max(1, min(4, int(pb_cat.total_forms)))
    except Exception:
        pass
    return 4


def clamp_cat_forms(sf: core.SaveFile, cat: core.Cat) -> None:
    total_forms = get_cat_total_forms(sf, cat)
    max_form_index = max(0, total_forms - 1)

    cat.current_form = max(0, min(int(cat.current_form), max_form_index))
    cat.unlocked_forms = max(0, min(int(cat.unlocked_forms), total_forms))

    # 4th form flag should only exist on 4-form units.
    if total_forms < 4:
        cat.fourth_form = 0
    else:
        cat.fourth_form = max(0, min(int(cat.fourth_form), 2))


def inventory_payload(sf: core.SaveFile) -> dict[str, Any]:
    battle_items: list[dict[str, Any]] = []
    catamins: list[dict[str, Any]] = []
    catseyes: list[dict[str, Any]] = []
    catfruit: list[dict[str, Any]] = []
    materials: list[dict[str, Any]] = []

    try:
        battle_defs = core.core_data.get_gatya_item_buy(sf).get_by_category(3) or []
        names = sf.battle_items.get_names(sf) or []
        for i, item in enumerate(getattr(sf.battle_items, "items", []) or []):
            item_id = int(battle_defs[i].id) if i < len(battle_defs) else None
            name = names[i] if i < len(names) and names[i] else f"Battle Item {i + 1}"
            battle_items.append(
                {
                    "index": i,
                    "item_id": item_id,
                    "icon_url": gatyaitem_icon_url(item_id),
                    "name": clean_name(name),
                    "amount": safe_int(item.amount),
                }
            )
    except Exception:
        pass

    try:
        names_o = core.core_data.get_gatya_item_names(sf)
        items = core.core_data.get_gatya_item_buy(sf).get_by_category(6)
        if items is not None:
            for i, item in enumerate(items):
                if i >= len(sf.catamins):
                    break
                catamins.append(
                    {
                        "index": i,
                        "item_id": int(item.id),
                        "icon_url": gatyaitem_icon_url(item.id),
                        "name": clean_name(names_o.get_name(item.id) or f"Catamin {item.id}"),
                        "amount": safe_int(sf.catamins[i]),
                    }
                )
    except Exception:
        pass

    try:
        names_o = core.core_data.get_gatya_item_names(sf)
        items = core.core_data.get_gatya_item_buy(sf).get_by_category(5)
        if items is not None:
            for i, item in enumerate(items):
                if i >= len(sf.catseyes):
                    break
                catseyes.append(
                    {
                        "index": i,
                        "item_id": int(item.id),
                        "icon_url": gatyaitem_icon_url(item.id),
                        "name": clean_name(names_o.get_name(item.id) or f"Catseye {item.id}"),
                        "amount": int(sf.catseyes[i]),
                    }
                )
    except Exception:
        pass

    try:
        matatabi = core.Matatabi(sf)
        names = matatabi.get_names() or []
        fruits = matatabi.matatabi or []
        for i, amount in enumerate(sf.catfruit):
            item_id = int(fruits[i].id) if i < len(fruits) else None
            name = names[i] if i < len(names) and names[i] else f"Catfruit {i}"
            catfruit.append(
                {
                    "index": i,
                    "item_id": item_id,
                    "icon_url": gatyaitem_icon_url(item_id),
                    "name": clean_name(name),
                    "amount": int(amount),
                }
            )
    except Exception:
        pass

    try:
        names_o = core.core_data.get_gatya_item_names(sf)
        items = core.core_data.get_gatya_item_buy(sf).get_by_category(7)
        mats = sf.ototo.base_materials.materials
        if items is not None:
            for i, item in enumerate(items):
                if i >= len(mats):
                    break
                materials.append(
                    {
                        "index": i,
                        "item_id": int(item.id),
                        "icon_url": gatyaitem_icon_url(item.id),
                        "name": clean_name(names_o.get_name(item.id) or f"Material {item.id}"),
                        "amount": int(mats[i].amount),
                    }
                )
    except Exception:
        pass

    return {
        "ok": True,
        "battle_items": battle_items,
        "catamins": catamins,
        "catseyes": catseyes,
        "catfruit": catfruit,
        "materials": materials,
    }


def trophies_payload(sf: core.SaveFile) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    owned = set(getattr(sf.medals, "medal_data_1", []))
    value_map = getattr(sf.medals, "medal_data_2", {}) or {}

    medal_names_list: list[list[str]] | None = None
    try:
        medal_names = core.core_data.get_medal_names(sf)
        names = getattr(medal_names, "medal_names", None)
        if isinstance(names, list):
            medal_names_list = names
    except Exception:
        medal_names_list = None

    if medal_names_list is not None:
        for medal_id, row in enumerate(medal_names_list):
            if not row:
                continue
            name = clean_name(row[0]) if row[0] else f"Trophy {medal_id}"
            desc = row[1] if len(row) > 1 else ""
            rows.append(
                {
                    "id": int(medal_id),
                    "name": name,
                    "description": str(desc),
                    "owned": medal_id in owned,
                    "value": int(value_map.get(medal_id, 0)),
                    "icon_url": medal_icon_url(medal_id),
                }
            )
    else:
        for medal_id in sorted(owned):
            rows.append(
                {
                    "id": int(medal_id),
                    "name": f"Trophy {medal_id}",
                    "description": "",
                    "owned": True,
                    "value": int(value_map.get(medal_id, 0)),
                    "icon_url": medal_icon_url(medal_id),
                }
            )

    rows.sort(key=lambda r: (not bool(r["owned"]), int(r["id"])))
    return {"ok": True, "trophies": rows}


def clamp_resource_value(sf: core.SaveFile, key: str, value: Any) -> int:
    value_i = max(0, safe_int(value))
    map_types: dict[str, core.MaxValueType] = {
        "catfood": core.MaxValueType.CATFOOD,
        "xp": core.MaxValueType.XP,
        "np": core.MaxValueType.NP,
        "normal_tickets": core.MaxValueType.NORMAL_TICKETS,
        "rare_tickets": core.MaxValueType.RARE_TICKETS,
        "platinum_tickets": core.MaxValueType.PLATINUM_TICKETS,
        "legend_tickets": core.MaxValueType.LEGEND_TICKETS,
        "leadership": core.MaxValueType.LEADERSHIP,
    }
    value_type = map_types.get(key)
    if value_type is None:
        return value_i
    max_value = max(0, safe_int(core.core_data.max_value_manager.get(value_type)))
    return min(value_i, max_value)


def select_bulk_cats(sf: core.SaveFile, payload: dict[str, Any]) -> list[core.Cat]:
    ids_raw = payload.get("ids")
    cats: list[core.Cat] = []
    if isinstance(ids_raw, list) and ids_raw:
        wanted = {int(x) for x in ids_raw}
        for cat in sf.cats.cats:
            if cat.id in wanted:
                cats.append(cat)
    else:
        cats = list(sf.cats.cats)

    if bool(payload.get("owned_only", False)):
        cats = [c for c in cats if bool(c.unlocked)]
    return cats


def apply_bulk_changes(sf: core.SaveFile, payload: dict[str, Any]) -> int:
    cats = select_bulk_cats(sf, payload)
    if not cats:
        return 0

    if bool(payload.get("unlock", False)):
        for cat in cats:
            cat.unlock(sf)

    if bool(payload.get("legit_max", False)):
        for cat in cats:
            cat.unlock(sf)
            cat.catguide_collected = True
            power_up = core.PowerUpHelper(cat, sf)
            power_up.max_upgrade()
            cat.upgrade.plus = max(cat.upgrade.plus, power_up.get_max_possible_plus())

    if "base" in payload:
        base_level = max(1, int(payload.get("base")))
        for cat in cats:
            cat.upgrade.base = base_level - 1

    if "plus" in payload:
        plus = max(0, int(payload.get("plus")))
        for cat in cats:
            cat.upgrade.plus = plus

    if "form" in payload:
        form = max(0, min(3, int(payload.get("form"))))
        for cat in cats:
            cat.current_form = form

    if "unlocked_forms" in payload:
        unlocked_forms = max(0, min(4, int(payload.get("unlocked_forms"))))
        for cat in cats:
            cat.unlocked_forms = unlocked_forms

    if bool(payload.get("true_form", False)):
        sf.cats.true_form_cats(sf, cats, force=False, set_current_forms=True)

    if bool(payload.get("fourth_form", False)):
        sf.cats.fourth_form_cats(sf, cats, force=False, set_current_forms=True)

    for cat in cats:
        clamp_cat_forms(sf, cat)
    return len(cats)


def apply_preset_changes(sf: core.SaveFile, preset: str) -> tuple[list[str], list[str]]:
    operations, presets = get_ops_and_presets()
    keys = presets.get(resolve_preset_key(preset))
    if not keys:
        raise RuntimeError(f"Unknown preset: {preset}")
    failed: list[str] = []
    applied: list[str] = []
    for key in keys:
        try:
            if key not in operations:
                failed.append(key)
                continue
            _, op = operations[key]
            op(sf)
            applied.append(key)
        except Exception:
            failed.append(key)
    return applied, failed

@app.get("/")
def index():
    return send_from_directory("webui", "index.html")


@app.get("/api/status")
def api_status():
    loaded = state.save_file is not None
    if not loaded:
        return jsonify({"loaded": False, "summary": None, "history": history_state()})
    sf = ensure_loaded()
    return jsonify({"loaded": True, "summary": summary(sf), "history": history_state()})


@app.get("/api/history")
def api_history():
    return jsonify({"ok": True, "history": history_state()})


@app.post("/api/undo")
def api_undo():
    try:
        ensure_loaded()
        if not state.history or state.history_index <= 0:
            raise RuntimeError("Nothing to undo.")
        state.history_index -= 1
        snapshot = state.history[state.history_index]
        sf = restore_snapshot(snapshot)
        return jsonify({"ok": True, "summary": summary(sf), "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/redo")
def api_redo():
    try:
        ensure_loaded()
        if not state.history or state.history_index >= len(state.history) - 1:
            raise RuntimeError("Nothing to redo.")
        state.history_index += 1
        snapshot = state.history[state.history_index]
        sf = restore_snapshot(snapshot)
        return jsonify({"ok": True, "summary": summary(sf), "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/safe_mode")
def api_safe_mode():
    try:
        payload = request.get_json(force=True)
        state.safe_mode = bool(payload.get("enabled", True))
        return jsonify({"ok": True, "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/load")
def api_load():
    try:
        payload = request.get_json(force=True)
        raw_path = Path(payload.get("path", ""))
        file_path = resolve_input_path(raw_path)
        result = SaveManagement.load_save_file_path(core.Path(str(file_path)), None, False)
        if result is None:
            raise RuntimeError("Could not parse save file.")
        save_file, _backup = result
        state.save_file = save_file
        state.loaded_path = file_path
        state.name_cache = {}
        reset_history(save_file, reason="load")
        return jsonify({"ok": True, "summary": summary(save_file), "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/pick_path")
def api_pick_path():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        initial = Path.home() / "Documents" / "bcsfe" / "saves"
        path = filedialog.askopenfilename(
            title="Select SAVE_DATA file",
            initialdir=str(initial),
        )
        root.destroy()
        if not path:
            return jsonify({"ok": False, "error": "No file selected."}), 400
        return jsonify({"ok": True, "path": path})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/save")
def api_save():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        out_path = Path(payload.get("path", "")).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.to_file(core.Path(str(out_path)))
        return jsonify({"ok": True, "path": str(out_path)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/pick_save_path")
def api_pick_save_path():
    try:
        sf = ensure_loaded()
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        default_name = (state.loaded_path.name + ".edited") if state.loaded_path else "SAVE_DATA.edited"
        path = filedialog.asksaveasfilename(
            title="Save edited save file",
            initialfile=default_name,
            initialdir=str((Path.home() / "Documents" / "bcsfe" / "saves")),
        )
        root.destroy()
        if not path:
            return jsonify({"ok": False, "error": "No output path selected."}), 400
        # keep linter quiet about used sf
        _ = sf
        return jsonify({"ok": True, "path": path})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/transfer/history")
def api_transfer_history():
    try:
        return jsonify(
            {
                "ok": True,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/clear")
def api_transfer_clear():
    try:
        state.transfer_records = []
        persist_transfer_records()
        return jsonify({"ok": True, "records": [], "storage": transfer_storage_info()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/update")
def api_transfer_update():
    try:
        payload = request.get_json(force=True)
        record_id = str(payload.get("id", "")).strip()
        fallback = payload.get("fallback", {})
        record_id = resolve_transfer_record_id(record_id, fallback if isinstance(fallback, dict) else None)
        patch = payload.get("patch", {})
        if not isinstance(patch, dict):
            raise RuntimeError("Patch must be an object.")
        record = update_transfer_record(record_id, patch)
        return jsonify(
            {
                "ok": True,
                "record": record,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/delete")
def api_transfer_delete():
    try:
        payload = request.get_json(force=True)
        record_id = str(payload.get("id", "")).strip()
        fallback = payload.get("fallback", {})
        record_id = resolve_transfer_record_id(record_id, fallback if isinstance(fallback, dict) else None)
        delete_transfer_record(record_id)
        return jsonify(
            {
                "ok": True,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/transfer/backup")
def api_transfer_backup():
    try:
        stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
        filename = f"transfer_history_backup_{stamp}.json"
        return jsonify(
            {
                "ok": True,
                "filename": filename,
                "backup": build_transfer_backup_payload(),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/download")
def api_transfer_download():
    try:
        payload = request.get_json(force=True)
        transfer_code = str(payload.get("transfer_code", "")).strip()
        confirmation_code = str(payload.get("confirmation_code", "")).strip()
        if not transfer_code or not confirmation_code:
            raise RuntimeError("Transfer code and confirmation code are required.")

        fallback_cc = ensure_loaded().cc.get_code() if state.save_file is not None else "en"
        country_code = str(payload.get("country", fallback_cc)).strip().lower()
        valid_ccs = set(core.CountryCode.get_all_str())
        if country_code not in valid_ccs:
            raise RuntimeError(f"Invalid country code: {country_code}")
        cc = core.CountryCode.from_code(country_code)

        fallback_gv = ensure_loaded().game_version if state.save_file is not None else core.GameVersion(120200)
        gv = parse_game_version(payload.get("game_version"), fallback_gv)

        server_handler, result = core.ServerHandler.from_codes(
            transfer_code,
            confirmation_code,
            cc,
            gv,
            print=False,
            save_backup=True,
        )
        if server_handler is None:
            if result is not None and result.response is not None:
                raise RuntimeError(
                    f"Failed to download save data (HTTP {result.response.status_code}). Check codes/country."
                )
            raise RuntimeError("Failed to download save data from server.")

        downloaded_save = server_handler.save_file
        download_dir = Path.home() / "Documents" / "bcsfe" / "saves" / "transfer_downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        suffix = re.sub(r"[^A-Za-z0-9]", "", transfer_code)[-6:] or "code"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = download_dir / f"SAVE_DATA_{country_code}_{suffix}_{ts}"
        downloaded_save.to_file(core.Path(str(out_path)))

        state.save_file = downloaded_save
        state.loaded_path = out_path
        state.name_cache = {}
        reset_history(downloaded_save, reason="transfer_download")

        record = push_transfer_record(
            {
                "kind": "download",
                "country": country_code,
                "game_version": gv.to_string(),
                "transfer_code": transfer_code,
                "confirmation_code": confirmation_code,
                "path": str(out_path),
                "inquiry_code": downloaded_save.inquiry_code,
                "needs_upload": True,
            }
        )
        return jsonify(
            {
                "ok": True,
                "summary": summary(downloaded_save),
                "history": history_state(),
                "path": str(out_path),
                "record": record,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/upload")
def api_transfer_upload():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        upload_managed_items = bool(payload.get("upload_managed_items", True))
        result = core.ServerHandler(sf, print=False).get_codes(
            upload_managed_items=upload_managed_items
        )
        if result is None:
            raise RuntimeError("Upload failed. Could not get transfer/confirmation codes.")
        transfer_code, confirmation_code = result

        record = push_transfer_record(
            {
                "kind": "upload",
                "country": sf.cc.get_code(),
                "game_version": sf.game_version.to_string(),
                "transfer_code": transfer_code,
                "confirmation_code": confirmation_code,
                "path": str(state.loaded_path) if state.loaded_path else "",
                "inquiry_code": sf.inquiry_code,
                "needs_upload": False,
            }
        )
        linked_count = mark_matching_downloads_uploaded(sf, str(record.get("id", "")))
        return jsonify(
            {
                "ok": True,
                "transfer_code": transfer_code,
                "confirmation_code": confirmation_code,
                "record": record,
                "linked_downloads": linked_count,
                "records": list(state.transfer_records or []),
                "summary": summary(sf),
                "history": history_state(),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/sync_mygamatoto")
def api_sync_mygamatoto():
    try:
        count = sync_mygamatoto_index()
        return jsonify({"ok": True, "count": count})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/gamatoto")
def api_gamatoto():
    try:
        sf = ensure_loaded()
        payload = gamatoto_payload(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/gamatoto/update")
def api_gamatoto_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        gam = sf.gamatoto

        if "level" in payload:
            gam.xp = max(0, set_gamatoto_level(sf, int(payload.get("level", 1))))
        if "xp" in payload:
            gam.xp = max(0, safe_int(payload.get("xp"), 0))
        if "remaining_seconds" in payload:
            gam.remaining_seconds = max(0.0, float(payload.get("remaining_seconds", 0.0)))
        if "return_flag" in payload:
            gam.return_flag = bool(payload.get("return_flag"))
        if "dest_id" in payload:
            gam.dest_id = max(0, safe_int(payload.get("dest_id"), 0))
        if "recon_length" in payload:
            gam.recon_length = max(0, safe_int(payload.get("recon_length"), 0))
        if "skin" in payload:
            gam.skin = max(0, safe_int(payload.get("skin"), 0))
        if "is_ad_present" in payload:
            gam.is_ad_present = bool(payload.get("is_ad_present"))

        push_history("gamatoto_update")
        updated = gamatoto_payload(sf)
        updated["history"] = history_state()
        return jsonify(updated)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/gamatoto/helper")
def api_gamatoto_helper():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        slot = max(0, int(payload.get("slot", 0)))
        helper_id = int(payload.get("id", -1))
        gam = sf.gamatoto
        helpers = list(getattr(gam.helpers, "helpers", []) or [])
        while slot >= len(helpers):
            helpers.append(GamatotoHelper.init())
        helpers[slot].id = helper_id if helper_id >= 0 else -1
        gam.helpers.helpers = helpers

        push_history(f"gamatoto_helper:{slot}")
        updated = gamatoto_payload(sf)
        updated["history"] = history_state()
        return jsonify(updated)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/cats")
def api_cats():
    try:
        sf = ensure_loaded()
        query = request.args.get("query", "").strip().lower()
        mode = request.args.get("filter", "All")

        rows: list[dict[str, Any]] = []
        for cat in sf.cats.cats:
            if mode == "Unlocked" and not cat.unlocked:
                continue
            if mode == "Locked" and cat.unlocked:
                continue

            name = get_cat_name(cat)
            if is_hidden_cat_name(name):
                continue
            haystack = f"{cat.id} {name}".lower()
            if query and query not in haystack:
                continue

            number = cat_number(cat)
            total_forms = get_cat_total_forms(sf, cat)
            rows.append(
                {
                    "id": cat.id,
                    "number": number,
                    "name": name,
                    "owned": bool(cat.unlocked),
                    "base": int(cat.upgrade.base + 1),
                    "plus": int(cat.upgrade.plus),
                    "form": int(cat.current_form),
                    "unlocked_forms": int(cat.unlocked_forms),
                    "fourth": int(cat.fourth_form),
                    "total_forms": int(total_forms),
                    "image_url": f"https://onestoppress.com/images/{number}_square.png",
                    "sprite_url": cat_sprite_url(cat.id, cat.current_form),
                    "talent_count": len(list(getattr(cat, "talents", []) or [])),
                }
            )
        return jsonify({"ok": True, "cats": rows})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/cats/talents")
def api_cats_talents():
    try:
        sf = ensure_loaded()
        cat_id = int(request.args.get("cat_id", "-1"))
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is None:
            raise RuntimeError(f"Cat not found: {cat_id}")
        payload = cat_talents_payload(sf, cat)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/talents/update")
def api_cats_talent_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        cat_id = int(payload.get("cat_id"))
        talent_id = int(payload.get("talent_id"))
        new_level = max(0, int(payload.get("level", 0)))
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is None:
            raise RuntimeError(f"Cat not found: {cat_id}")
        talents = list(getattr(cat, "talents", []) or [])
        target = next((t for t in talents if safe_int(getattr(t, "id", -1)) == talent_id), None)
        if target is None:
            raise RuntimeError(f"Talent not found for cat {cat_id}: {talent_id}")

        max_level = max(1, new_level)
        try:
            talent_data = sf.cats.read_talent_data(sf)
            if talent_data is not None:
                skill = talent_data.get_skill_from_cat(cat.id, talent_id)
                if skill is not None:
                    max_level = max(1, safe_int(getattr(skill, "max_lv", 1), 1))
        except Exception:
            pass

        target.level = max(0, min(new_level, max_level))
        cat.talents = talents
        push_history(f"cat_talent:{cat_id}:{talent_id}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
                "talents": cat_talents_payload(sf, cat).get("talents", []),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/dashboard")
def api_dashboard():
    try:
        sf = ensure_loaded()
        payload = dashboard_payload(sf)
        payload["summary"] = summary(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/progress/story")
def api_progress_story():
    try:
        sf = ensure_loaded()
        return jsonify({"ok": True, "story": story_progress_stats(sf), "summary": summary(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/story/editor")
def api_story_editor():
    try:
        sf = ensure_loaded()
        payload = story_editor_payload(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/story/update")
def api_story_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        chapter_index = int(payload.get("chapter"))
        clear_count = max(0, int(payload.get("cleared", 0)))
        superior_count = max(0, int(payload.get("superior", 0)))
        clear_amount = max(1, int(payload.get("clear_amount", 1)))

        chapters = list(getattr(sf.story, "chapters", []) or [])
        if chapter_index < 0 or chapter_index >= len(chapters):
            raise RuntimeError(f"Story chapter out of range: {chapter_index}")

        apply_story_chapter_values(chapters[chapter_index], clear_count, superior_count, clear_amount=clear_amount)
        push_history(f"story_chapter:{chapter_index}")

        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "story": story_editor_payload(sf).get("chapters", []),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/story/bulk")
def api_story_bulk():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        action = str(payload.get("action", "")).strip().lower()
        chapters = list(getattr(sf.story, "chapters", []) or [])
        if not chapters:
            raise RuntimeError("No story chapters available.")

        changed = 0
        for chapter in chapters:
            stages = list(getattr(chapter, "stages", []) or [])
            clear_total = min(48, len(stages))
            treasure_total = min(49, len(stages))
            if action == "set_all_superior":
                apply_story_chapter_values(chapter, clear_total, treasure_total)
            elif action == "set_all_cleared":
                apply_story_chapter_values(chapter, clear_total, 0)
            elif action == "reset_all":
                apply_story_chapter_values(chapter, 0, 0)
            else:
                raise RuntimeError(f"Unknown story bulk action: {action}")
            changed += 1

        push_history(f"story_bulk:{action}:{changed}")
        return jsonify(
            {
                "ok": True,
                "changed": changed,
                "summary": summary(sf),
                "story": story_editor_payload(sf).get("chapters", []),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/base/upgrades")
def api_base_upgrades():
    try:
        sf = ensure_loaded()
        payload = base_upgrades_payload(sf)
        payload["summary"] = summary(sf)
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/base/cannons")
def api_base_cannons():
    try:
        sf = ensure_loaded()
        payload = base_cannons_payload(sf)
        payload["summary"] = summary(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/base/cannons/update")
def api_base_cannons_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)

        if sf.ototo.cannons is None:
            sf.ototo.cannons = ototo_data.Cannons.init(sf.game_version)
        cannons_obj = sf.ototo.cannons
        recipe = ototo_data.CastleRecipeUnlock(sf)

        if "selected_parts" in payload:
            selected_parts = list(payload.get("selected_parts") or [])
            while len(selected_parts) < 3:
                selected_parts.append(0)
            cleaned = [max(0, safe_int(selected_parts[i], 0)) for i in range(3)]
            if not cannons_obj.selected_parts:
                cannons_obj.selected_parts = [cleaned]
            else:
                cannons_obj.selected_parts[0] = cleaned

        if "cannon_id" in payload:
            cannon_id = max(0, safe_int(payload.get("cannon_id"), 0))
            cannon = cannons_obj.cannons.get(cannon_id)
            if cannon is None:
                cannon = ototo_data.Cannon.init()
                cannons_obj.cannons[cannon_id] = cannon

            if "development" in payload:
                cannon.development = max(0, min(3, safe_int(payload.get("development"), 0)))

            if "levels" in payload:
                levels = list(payload.get("levels") or [])
                while len(levels) < 3:
                    levels.append(0)
                while len(cannon.levels) < 3:
                    cannon.levels.append(0)
                for part_id in range(3):
                    max_level = recipe.get_max_level(cannon_id, part_id) if recipe is not None else None
                    if max_level is None:
                        max_level = recipe.get_max_part_level(part_id) if recipe is not None else None
                    max_level_i = max(0, safe_int(max_level, 0))
                    cannon.levels[part_id] = max(
                        0,
                        min(safe_int(levels[part_id], 0), max_level_i),
                    )

        push_history("base_cannons_update")
        updated = base_cannons_payload(sf)
        updated["summary"] = summary(sf)
        updated["history"] = history_state()
        return jsonify(updated)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/base/update")
def api_base_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        skill_id = int(payload.get("id"))
        base_level = max(1, int(payload.get("base", 1)))
        plus_level = max(0, int(payload.get("plus", 0)))

        ability_data = core.core_data.get_ability_data(sf)
        ability = ability_data.get_ability_data_item(skill_id) if ability_data is not None else None
        max_base = max(0, safe_int(getattr(ability, "max_base_level", 1)) - 1)
        max_plus = max(0, safe_int(getattr(ability, "max_plus_level", 0)))

        sf.special_skills.set_upgrade(
            skill_id,
            core.Upgrade(min(plus_level, max_plus), min(base_level - 1, max_base)),
            max_base=max_base,
            max_plus=max_plus,
        )
        push_history(f"base:{skill_id}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
                "base": base_upgrades_payload(sf)["upgrades"],
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/validation")
def api_validation():
    try:
        sf = ensure_loaded()
        payload = validation_payload(sf)
        payload["summary"] = summary(sf)
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/encyclopedias")
def api_encyclopedias():
    try:
        sf = ensure_loaded()
        enemy_unlocked, enemy_total = enemy_guide_stats(sf)
        catguide_claimed, catguide_total = cat_guide_stats(sf)
        return jsonify(
            {
                "ok": True,
                "enemy_guide": {"unlocked": enemy_unlocked, "total": enemy_total},
                "cat_guide": {"claimed": catguide_claimed, "total": catguide_total},
                "summary": summary(sf),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/enemies")
def api_enemies():
    try:
        sf = ensure_loaded()
        query = request.args.get("query", "")
        mode = request.args.get("filter", "All")
        payload = enemy_guide_payload(sf, query=query, filter_mode=mode)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/enemies/update")
def api_enemies_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        enemy_id = int(payload.get("id"))
        unlocked = bool(payload.get("unlocked"))

        guide = list(getattr(sf, "enemy_guide", []) or [])
        if enemy_id < 0 or enemy_id >= len(guide):
            raise RuntimeError(f"Enemy index out of range: {enemy_id}")

        guide[enemy_id] = 1 if unlocked else 0
        sf.enemy_guide = guide
        if unlocked and safe_int(getattr(sf, "unlock_enemy_guide", 0)) == 0:
            sf.unlock_enemy_guide = 1

        push_history(f"enemy:{enemy_id}:{'unlock' if unlocked else 'clear'}")
        enemy_unlocked, enemy_total = enemy_guide_stats(sf)
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
                "enemy_guide": {"unlocked": enemy_unlocked, "total": enemy_total},
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/enemies/bulk")
def api_enemies_bulk():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        action = str(payload.get("action", "")).strip().lower()
        query = str(payload.get("query", ""))
        mode = str(payload.get("filter", "All"))

        guide = list(getattr(sf, "enemy_guide", []) or [])
        if not guide:
            raise RuntimeError("Enemy guide data is empty.")

        if action in {"unlock_all", "clear_all"}:
            target_ids = list(range(len(guide)))
        elif action in {"unlock_filtered", "clear_filtered"}:
            filtered = enemy_guide_payload(sf, query=query, filter_mode=mode).get("enemies", [])
            target_ids = [
                safe_int(row.get("id"), -1)
                for row in filtered
                if 0 <= safe_int(row.get("id"), -1) < len(guide)
            ]
        else:
            raise RuntimeError(f"Unsupported enemy bulk action: {action}")

        new_value = 1 if action.startswith("unlock") else 0
        changed = 0
        seen: set[int] = set()
        for enemy_id in target_ids:
            if enemy_id in seen:
                continue
            seen.add(enemy_id)
            if safe_int(guide[enemy_id], 0) != new_value:
                guide[enemy_id] = new_value
                changed += 1

        sf.enemy_guide = guide
        if new_value == 1 and changed > 0 and safe_int(getattr(sf, "unlock_enemy_guide", 0)) == 0:
            sf.unlock_enemy_guide = 1

        push_history(f"enemy_bulk:{action}:{changed}")
        enemy_unlocked, enemy_total = enemy_guide_stats(sf)
        return jsonify(
            {
                "ok": True,
                "changed": changed,
                "summary": summary(sf),
                "history": history_state(),
                "enemy_guide": {"unlocked": enemy_unlocked, "total": enemy_total},
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/inventory")
def api_inventory():
    try:
        sf = ensure_loaded()
        return jsonify(inventory_payload(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/trophies")
def api_trophies():
    try:
        sf = ensure_loaded()
        return jsonify(trophies_payload(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/trophies/update")
def api_trophies_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        medal_id = int(payload.get("id"))
        owned = bool(payload.get("owned"))
        if medal_id < 0:
            raise RuntimeError(f"Invalid trophy id: {medal_id}")

        if owned:
            sf.medals.add_medal(medal_id)
        else:
            sf.medals.remove_medal(medal_id)
        push_history(f"trophy:{medal_id}:{'add' if owned else 'remove'}")

        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "trophies": trophies_payload(sf)["trophies"],
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/inventory/update")
def api_inventory_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        category = str(payload.get("category", "")).strip().lower()
        index = int(payload.get("index"))
        amount = max(0, int(payload.get("amount")))

        if category == "catseyes":
            if index < 0 or index >= len(sf.catseyes):
                raise RuntimeError(f"Catseye index out of range: {index}")
            max_value = core.core_data.max_value_manager.get(core.MaxValueType.CATSEYES)
            sf.catseyes[index] = min(amount, int(max_value))
        elif category == "catfruit":
            if index < 0 or index >= len(sf.catfruit):
                raise RuntimeError(f"Catfruit index out of range: {index}")
            if sf.game_version < 110400:
                max_value = core.core_data.max_value_manager.get_old(core.MaxValueType.CATFRUIT)
            else:
                max_value = core.core_data.max_value_manager.get_new(core.MaxValueType.CATFRUIT)
            sf.catfruit[index] = min(amount, int(max_value))
        elif category == "catamins":
            if index < 0 or index >= len(sf.catamins):
                raise RuntimeError(f"Catamin index out of range: {index}")
            max_value = core.core_data.max_value_manager.get(core.MaxValueType.CATAMINS)
            sf.catamins[index] = min(amount, int(max_value))
        elif category == "battle_items":
            if index < 0 or index >= len(sf.battle_items.items):
                raise RuntimeError(f"Battle item index out of range: {index}")
            max_value = core.core_data.max_value_manager.get(core.MaxValueType.BATTLE_ITEMS)
            sf.battle_items.items[index].amount = min(amount, int(max_value))
        elif category == "materials":
            mats = sf.ototo.base_materials.materials
            if index < 0 or index >= len(mats):
                raise RuntimeError(f"Material index out of range: {index}")
            max_value = core.core_data.max_value_manager.get(core.MaxValueType.BASE_MATERIALS)
            mats[index].amount = min(amount, int(max_value))
        else:
            raise RuntimeError(f"Unsupported inventory category: {category}")

        push_history(f"inventory:{category}:{index}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "inventory": inventory_payload(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/resources")
def api_resources():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        allowed = {
            "catfood",
            "xp",
            "np",
            "normal_tickets",
            "rare_tickets",
            "platinum_tickets",
            "legend_tickets",
            "leadership",
        }
        for key, value in payload.items():
            if key not in allowed or not hasattr(sf, key):
                continue
            setattr(sf, key, clamp_resource_value(sf, key, value))
        push_history("resources")
        return jsonify({"ok": True, "summary": summary(sf), "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/action")
def api_cats_action():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        action = payload.get("action", "")
        ids = [int(x) for x in payload.get("ids", [])]

        cats: list[core.Cat] = []
        for cid in ids:
            cat = sf.cats.get_cat_by_id(cid)
            if cat is not None:
                cats.append(cat)

        if action == "unlock":
            for cat in cats:
                cat.unlock(sf)
        elif action == "true_form":
            sf.cats.true_form_cats(sf, cats, force=False, set_current_forms=True)
        elif action == "fourth_form":
            sf.cats.fourth_form_cats(sf, cats, force=False, set_current_forms=True)
        elif action == "legit_max":
            for cat in cats:
                cat.unlock(sf)
                cat.catguide_collected = True
                power_up = core.PowerUpHelper(cat, sf)
                power_up.max_upgrade()
                cat.upgrade.plus = max(cat.upgrade.plus, power_up.get_max_possible_plus())
        else:
            raise RuntimeError(f"Unknown action: {action}")

        push_history(f"cat_action:{action}")
        return jsonify({"ok": True, "summary": summary(sf), "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/update")
def api_cats_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        cat_id = int(payload.get("id"))
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is None:
            raise RuntimeError(f"Cat not found: {cat_id}")

        if "owned" in payload:
            owned = bool(payload.get("owned"))
            if owned:
                cat.unlock(sf)
            else:
                cat.unlocked = 0

        if "base" in payload:
            base_level = max(1, int(payload.get("base")))
            cat.upgrade.base = base_level - 1

        if "plus" in payload:
            cat.upgrade.plus = max(0, int(payload.get("plus")))

        if "form" in payload:
            cat.current_form = max(0, min(3, int(payload.get("form"))))

        if "unlocked_forms" in payload:
            cat.unlocked_forms = max(0, min(4, int(payload.get("unlocked_forms"))))

        if "fourth" in payload:
            cat.fourth_form = max(0, int(payload.get("fourth")))

        clamp_cat_forms(sf, cat)
        push_history(f"cat_update:{cat_id}")
        return jsonify({"ok": True, "summary": summary(sf), "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/bulk")
def api_cats_bulk():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        count = apply_bulk_changes(sf, payload)
        if count > 0:
            push_history("cats_bulk")
        return jsonify(
            {
                "ok": True,
                "count": count,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/bulk/preview")
def api_cats_bulk_preview():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        before = clone_save(sf)
        preview = clone_save(sf)
        count = apply_bulk_changes(preview, payload)
        return jsonify({"ok": True, "count": count, "diff": diff_payload(before, preview)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/op")
def api_op():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        key = payload.get("key", "")
        operations, _ = get_ops_and_presets()
        if key not in operations:
            raise RuntimeError(f"Unknown operation: {key}")
        risky_keys = {"clear_story_only", "clear_story_superior_treasures", "clear_story_treasures", "clear_all_maps"}
        allow_risky = bool(payload.get("allow_risky", False))
        if state.safe_mode and key in risky_keys and not allow_risky:
            raise RuntimeError("Safe Mode is enabled. Disable it or confirm risky edits.")
        _, op = operations[key]
        op(sf)
        push_history(f"op:{key}")
        return jsonify({"ok": True, "summary": summary(sf), "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/op/preview")
def api_op_preview():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        key = payload.get("key", "")
        operations, _ = get_ops_and_presets()
        if key not in operations:
            raise RuntimeError(f"Unknown operation: {key}")
        before = clone_save(sf)
        preview = clone_save(sf)
        _, op = operations[key]
        op(preview)
        return jsonify({"ok": True, "diff": diff_payload(before, preview)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/preset")
def api_preset():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        preset = resolve_preset_key(payload.get("preset", ""))
        _, presets = get_ops_and_presets()
        keys = presets.get(preset) or []
        if not keys:
            raise RuntimeError(f"Unknown preset: {preset}")
        risky_keys = {"clear_story_only", "clear_story_superior_treasures", "clear_story_treasures", "clear_all_maps"}
        allow_risky = bool(payload.get("allow_risky", False))
        has_risky = any(k in risky_keys for k in keys)
        if state.safe_mode and has_risky and not allow_risky:
            raise RuntimeError("Safe Mode is enabled. Disable it or confirm risky edits.")

        applied, failed = apply_preset_changes(sf, preset)
        if applied:
            push_history(f"preset:{preset}")
        return jsonify(
            {
                "ok": True,
                "applied": applied,
                "failed": failed,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/preset/preview")
def api_preset_preview():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        preset = resolve_preset_key(payload.get("preset", ""))
        _, presets = get_ops_and_presets()
        if preset not in presets:
            raise RuntimeError(f"Unknown preset: {preset}")
        before = clone_save(sf)
        preview = clone_save(sf)
        _applied, failed = apply_preset_changes(preview, preset)
        return jsonify({"ok": True, "failed": failed, "diff": diff_payload(before, preview)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


def main():
    core.core_data.init_data()
    load_mygamatoto_index()
    load_transfer_records()
    app.run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()




