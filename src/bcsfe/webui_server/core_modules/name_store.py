from __future__ import annotations

import json

import requests

from bcsfe import core

from .bootstrap import INDEX_PATH
from .bootstrap import cat_number
from .bootstrap import clean_name
from .bootstrap import state
from .helpers import ensure_loaded


def load_mygamatoto_index() -> None:
    """Load cached MyGamatoto cat-name index into process state."""
    if not INDEX_PATH.exists():
        return
    try:
        obj = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            state.mygamatoto_index = {
                str(key): str(value)
                for key, value in obj.items()
            }
    except Exception:
        state.mygamatoto_index = {}


def sync_mygamatoto_index() -> int:
    """Fetch latest MyGamatoto index and persist it to cache."""
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
    serialized = json.dumps(
        index,
        ensure_ascii=False,
        indent=2,
    )
    INDEX_PATH.write_text(serialized, encoding="utf-8")
    state.name_cache = {}
    return len(index)


def get_cat_name(cat: core.Cat) -> str:
    """Resolve a cat display name with cache + fallback sources."""
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
