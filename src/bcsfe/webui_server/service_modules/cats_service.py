from __future__ import annotations

from ..core import clean_name
from ..core import core
from ..core import safe_int


def _get_cat_talent_sort_key(row: dict[str, object]) -> int:
    """Return stable integer sort key for talent rows."""
    return int(row["id"])


def cat_talents_payload(sf: core.SaveFile, cat: core.Cat) -> dict[str, object]:
    """Build talents payload for one cat row."""
    rows: list[dict[str, object]] = []
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
                skill_name = talent_data.get_skill_name(
                    getattr(skill, "text_id", 0),
                )
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
    rows.sort(key=_get_cat_talent_sort_key)
    return {"ok": True, "cat_id": int(cat.id), "talents": rows}


def get_cat_total_forms(sf: core.SaveFile, cat: core.Cat) -> int:
    """Return supported form count for one cat."""
    try:
        pic_book = sf.cats.read_nyanko_picture_book(sf)
        pb_cat = pic_book.get_cat(cat.id) if pic_book is not None else None
        if pb_cat is not None:
            return max(1, min(4, int(pb_cat.total_forms)))
    except Exception:
        pass
    return 4


def clamp_cat_forms(sf: core.SaveFile, cat: core.Cat) -> None:
    """Clamp cat form flags to legal values from form count."""
    total_forms = get_cat_total_forms(sf, cat)
    max_form_index = max(0, total_forms - 1)
    cat.current_form = max(0, min(int(cat.current_form), max_form_index))
    cat.unlocked_forms = max(0, min(int(cat.unlocked_forms), total_forms))
    if total_forms < 4:
        cat.fourth_form = 0
        return
    cat.fourth_form = max(0, min(int(cat.fourth_form), 2))
