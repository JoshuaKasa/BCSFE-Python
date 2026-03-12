from __future__ import annotations

from ..core import clean_name
from ..core import core
from ..core import enemy_icon_url
from ..core import safe_int

StoryRow = dict[str, object]


STORY_CHAPTER_NAMES: tuple[str, ...] = (
    "EoC Ch.1",
    "EoC Ch.2",
    "EoC Ch.3",
    "ItF Ch.1",
    "ItF Ch.2",
    "ItF Ch.3",
    "CotC Ch.1",
    "CotC Ch.2",
    "CotC Ch.3",
)


def _build_story_chapter_row(
    index: int,
    chapter: core.Chapter,
) -> StoryRow:
    """Build one story progress row from a chapter."""
    stages = tuple(getattr(chapter, "stages", ()) or ())
    clear_total = min(48, len(stages))
    treasure_total = min(49, len(stages))
    clear_done = sum(
        1
        for stage in stages[:clear_total]
        if safe_int(getattr(stage, "clear_times", 0)) > 0
    )
    superior_done = sum(
        1
        for stage in stages[:treasure_total]
        if safe_int(getattr(stage, "treasure", 0)) >= 3
    )
    chapter_name = (
        STORY_CHAPTER_NAMES[index]
        if index < len(STORY_CHAPTER_NAMES)
        else f"Chapter {index + 1}"
    )
    return {
        "index": index,
        "name": chapter_name,
        "cleared": clear_done,
        "clear_total": clear_total,
        "superior": superior_done,
        "treasure_total": treasure_total,
    }


def _build_story_saga_rows(chapter_rows: list[StoryRow]) -> list[StoryRow]:
    """Build grouped saga rows from chapter rows."""
    saga_defs: tuple[tuple[str, int, int], ...] = (
        ("EoC", 0, 3),
        ("ItF", 3, 6),
        ("CotC", 6, 9),
    )
    saga_rows: list[StoryRow] = []
    for label, start, end in saga_defs:
        subset = chapter_rows[start:end]
        if not subset:
            continue
        clear_total = sum(safe_int(row.get("clear_total"), 0) for row in subset)
        cleared = sum(safe_int(row.get("cleared"), 0) for row in subset)
        treasure_total = sum(
            safe_int(row.get("treasure_total"), 0)
            for row in subset
        )
        superior = sum(safe_int(row.get("superior"), 0) for row in subset)
        saga_rows.append(
            {
                "name": label,
                "cleared": cleared,
                "clear_total": clear_total,
                "superior": superior,
                "treasure_total": treasure_total,
            }
        )
    return saga_rows


def story_progress_stats(save_file: core.SaveFile) -> dict[str, object]:
    """Build chapter and saga progress statistics."""
    chapter_rows = [
        _build_story_chapter_row(index, chapter)
        for index, chapter in enumerate(
            getattr(save_file.story, "chapters", ()) or ()
        )
    ]
    saga_rows = _build_story_saga_rows(chapter_rows)
    clear_total = sum(
        safe_int(row.get("clear_total"), 0)
        for row in chapter_rows
    )
    clear_done = sum(safe_int(row.get("cleared"), 0) for row in chapter_rows)
    treasure_total = sum(
        safe_int(row.get("treasure_total"), 0)
        for row in chapter_rows
    )
    superior_done = sum(
        safe_int(row.get("superior"), 0)
        for row in chapter_rows
    )
    return {
        "chapters": chapter_rows,
        "sagas": saga_rows,
        "clear_total": clear_total,
        "clear_done": clear_done,
        "treasure_total": treasure_total,
        "superior_done": superior_done,
    }


def lineup_stats(save_file: core.SaveFile) -> tuple[int, int]:
    """Return lineup unlocked/total stats."""
    fallback_total = len(getattr(save_file.lineups, "slots", ()) or ())
    slot_length = getattr(
        save_file.lineups,
        "slot_names_length",
        fallback_total,
    )
    total = safe_int(slot_length, 15)
    unlocked = safe_int(getattr(save_file.lineups, "unlocked_slots", 0))
    clamped_unlocked = max(0, min(unlocked, max(total, 0)))
    return clamped_unlocked, max(total, 0)


def enemy_guide_stats(save_file: core.SaveFile) -> tuple[int, int]:
    """Return enemy guide unlocked/total stats."""
    guide = tuple(getattr(save_file, "enemy_guide", ()) or ())
    total = len(guide)
    try:
        names_obj = core.core_data.get_enemy_names(save_file)
        names = tuple(getattr(names_obj, "names", ()) or ())
        total = max(total, len(names))
    except Exception:
        pass
    unlocked = sum(1 for value in guide if safe_int(value, 0) != 0)
    return unlocked, total


def cat_guide_stats(save_file: core.SaveFile) -> tuple[int, int]:
    """Return cat guide claimed/total stats."""
    cats = tuple(getattr(save_file.cats, "cats", ()) or ())
    total = len(cats)
    claimed = sum(
        1
        for cat in cats
        if bool(getattr(cat, "catguide_collected", False))
    )
    return claimed, total


def _matches_enemy_filter(mode: str, unlocked: bool) -> bool:
    """Return whether an enemy row matches unlocked/missing mode filters."""
    if mode in {"unlocked", "owned"}:
        return unlocked
    if mode in {"missing", "locked"}:
        return not unlocked
    return True


def _matches_enemy_valid_filter(
    mode: str,
    enemy_id: int,
    valid_ids: set[int],
    has_valid_ids: bool,
) -> bool:
    """Return whether an enemy row matches valid/invalid filters."""
    if not has_valid_ids:
        return True
    if mode == "valid":
        return enemy_id in valid_ids
    if mode == "invalid":
        return enemy_id not in valid_ids
    return True


def _get_enemy_valid_ids(save_file: core.SaveFile) -> set[int]:
    """Load valid enemy IDs from game dictionaries."""
    valid_ids: set[int] = set()
    try:
        valid = core.EnemyDictionary(save_file).get_valid_enemies()
        if valid is not None:
            valid_ids = {
                safe_int(enemy_id, -1)
                for enemy_id in valid
                if safe_int(enemy_id, -1) >= 0
            }
    except Exception:
        return set()
    return valid_ids


def _build_enemy_rows(
    save_file: core.SaveFile,
    total: int,
    query: str,
    mode: str,
    names_obj: core.EnemyNames | None,
    guide: tuple[object, ...],
    valid_ids: set[int],
) -> list[StoryRow]:
    """Build filtered enemy guide rows."""
    has_valid_ids = len(valid_ids) > 0
    rows: list[StoryRow] = []
    for enemy_id in range(total):
        unlocked = enemy_id < len(guide) and safe_int(guide[enemy_id], 0) != 0
        if not _matches_enemy_filter(mode, bool(unlocked)):
            continue
        if not _matches_enemy_valid_filter(
            mode,
            enemy_id,
            valid_ids,
            has_valid_ids,
        ):
            continue

        try:
            if names_obj is None:
                raw_name = None
            else:
                raw_name = names_obj.get_name(enemy_id)
        except Exception:
            raw_name = None
        name = clean_name(raw_name or f"Enemy {enemy_id}")
        search_blob = f"{enemy_id} {name}".lower()
        if query and query not in search_blob:
            continue

        rows.append(
            {
                "id": enemy_id,
                "name": name,
                "unlocked": bool(unlocked),
                "valid": (enemy_id in valid_ids) if has_valid_ids else True,
                "editable": enemy_id < len(guide),
                "image_url": enemy_icon_url(enemy_id),
            }
        )

    return rows


def enemy_guide_payload(
    save_file: core.SaveFile,
    query: str = "",
    filter_mode: str = "All",
) -> dict[str, object]:
    """Build enemy guide payload with current filters and query."""
    from .diff_summary_service import summary

    guide = tuple(getattr(save_file, "enemy_guide", ()) or ())
    names_obj: core.EnemyNames | None = None
    names_raw: tuple[str, ...] = ()
    try:
        names_obj = core.core_data.get_enemy_names(save_file)
        names_raw = tuple(getattr(names_obj, "names", ()) or ())
    except Exception:
        names_obj = None

    total = max(len(guide), len(names_raw))
    query_text = query.strip().lower()
    mode = filter_mode.strip().lower()
    valid_ids = _get_enemy_valid_ids(save_file)
    rows = _build_enemy_rows(
        save_file,
        total,
        query_text,
        mode,
        names_obj,
        guide,
        valid_ids,
    )
    unlocked_count, total_count = enemy_guide_stats(save_file)
    return {
        "ok": True,
        "enemies": rows,
        "enemy_guide": {"unlocked": unlocked_count, "total": total_count},
        "summary": summary(save_file),
    }
