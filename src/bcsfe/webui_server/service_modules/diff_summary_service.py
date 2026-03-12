from __future__ import annotations

from ..core import core
from ..core import history_state
from ..core import safe_int
from ..core import state
from .story_stats_service import cat_guide_stats
from .story_stats_service import enemy_guide_stats
from .story_stats_service import lineup_stats
from .story_stats_service import story_progress_stats

DiffRow = dict[str, object]


TRACKED_SUMMARY_FIELDS: tuple[tuple[str, str], ...] = (
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
)


def _build_summary_changes(
    before_summary: dict[str, object],
    after_summary: dict[str, object],
) -> list[DiffRow]:
    """Build summary-level diff rows."""
    rows: list[DiffRow] = []
    for key, label in TRACKED_SUMMARY_FIELDS:
        before_value = before_summary.get(key)
        after_value = after_summary.get(key)
        if before_value == after_value:
            continue
        rows.append(
            {
                "key": key,
                "label": label,
                "before": before_value,
                "after": after_value,
            }
        )
    return rows


def _build_cat_changes(
    before_save: core.SaveFile,
    after_save: core.SaveFile,
) -> DiffRow:
    """Build cat-change stats between two saves."""
    changed = 0
    unlocked = 0
    levels = 0
    forms = 0
    fourth_forms = 0
    for before_cat, after_cat in zip(
        before_save.cats.cats,
        after_save.cats.cats,
    ):
        flags = _collect_cat_change_flags(before_cat, after_cat)
        unlocked += int(flags["unlocked"])
        levels += int(flags["levels"])
        forms += int(flags["forms"])
        fourth_forms += int(flags["fourth"])
        changed += int(flags["changed"])
    return {
        "changed": changed,
        "unlock_toggles": unlocked,
        "level_changes": levels,
        "form_changes": forms,
        "fourth_form_changes": fourth_forms,
    }


def _collect_cat_change_flags(
    before_cat: core.Cat,
    after_cat: core.Cat,
) -> dict[str, bool]:
    """Collect all cat-level change flags for one cat pair."""
    unlocked_changed = bool(before_cat.unlocked) != bool(after_cat.unlocked)
    levels_changed = _has_cat_level_change(before_cat, after_cat)
    forms_changed = _has_cat_form_change(before_cat, after_cat)
    fourth_changed = _has_cat_fourth_form_change(before_cat, after_cat)
    changed = (
        unlocked_changed
        or levels_changed
        or forms_changed
        or fourth_changed
    )
    return {
        "unlocked": unlocked_changed,
        "levels": levels_changed,
        "forms": forms_changed,
        "fourth": fourth_changed,
        "changed": changed,
    }


def _has_cat_level_change(before_cat: core.Cat, after_cat: core.Cat) -> bool:
    """Return whether base/plus levels changed for a cat."""
    base_changed = safe_int(before_cat.upgrade.base) != safe_int(
        after_cat.upgrade.base
    )
    plus_changed = safe_int(before_cat.upgrade.plus) != safe_int(
        after_cat.upgrade.plus
    )
    return base_changed or plus_changed


def _has_cat_form_change(before_cat: core.Cat, after_cat: core.Cat) -> bool:
    """Return whether active/unlocked forms changed for a cat."""
    form_changed = safe_int(before_cat.current_form) != safe_int(
        after_cat.current_form
    )
    unlocked_forms_changed = safe_int(before_cat.unlocked_forms) != safe_int(
        after_cat.unlocked_forms
    )
    return form_changed or unlocked_forms_changed


def _has_cat_fourth_form_change(
    before_cat: core.Cat,
    after_cat: core.Cat,
) -> bool:
    """Return whether fourth-form flag changed for a cat."""
    return safe_int(before_cat.fourth_form) != safe_int(after_cat.fourth_form)


def _count_changed_indexes(
    before_values: list[object],
    after_values: list[object],
) -> int:
    """Count differing values by index over two equal-domain lists."""
    size = min(len(before_values), len(after_values))
    return sum(
        1
        for index in range(size)
        if before_values[index] != after_values[index]
    )


def _extract_amounts(items: list[object]) -> list[int]:
    """Extract integer amount values from item containers."""
    return [safe_int(getattr(item, "amount", 0)) for item in items]


def _extract_talent_orbs(save_file: core.SaveFile) -> dict[object, object]:
    """Extract talent-orb map from a save file."""
    orbs = getattr(getattr(save_file, "talent_orbs", None), "orbs", {}) or {}
    return dict(orbs)


def _count_talent_orb_changes(
    before_orbs: dict[object, object],
    after_orbs: dict[object, object],
) -> int:
    """Count changed talent orb values between two maps."""
    orb_ids = set(before_orbs.keys()) | set(after_orbs.keys())
    return sum(
        1
        for orb_id in orb_ids
        if safe_int(getattr(before_orbs.get(orb_id), "value", 0), 0)
        != safe_int(getattr(after_orbs.get(orb_id), "value", 0), 0)
    )


def _build_inventory_changes(
    before_save: core.SaveFile,
    after_save: core.SaveFile,
) -> DiffRow:
    """Build inventory-change stats between two saves."""
    before_materials = _extract_amounts(
        before_save.ototo.base_materials.materials
    )
    after_materials = _extract_amounts(
        after_save.ototo.base_materials.materials
    )
    before_battle_items = _extract_amounts(before_save.battle_items.items)
    after_battle_items = _extract_amounts(after_save.battle_items.items)
    before_orbs = _extract_talent_orbs(before_save)
    after_orbs = _extract_talent_orbs(after_save)
    talent_orb_changes = _count_talent_orb_changes(before_orbs, after_orbs)
    return {
        "catseyes": _count_changed_indexes(
            before_save.catseyes,
            after_save.catseyes,
        ),
        "catfruit": _count_changed_indexes(
            before_save.catfruit,
            after_save.catfruit,
        ),
        "catamins": _count_changed_indexes(
            before_save.catamins,
            after_save.catamins,
        ),
        "materials": _count_changed_indexes(before_materials, after_materials),
        "battle_items": _count_changed_indexes(
            before_battle_items,
            after_battle_items,
        ),
        "talent_orbs": talent_orb_changes,
    }


def _build_story_changes(
    before_save: core.SaveFile,
    after_save: core.SaveFile,
) -> DiffRow:
    """Build story progress deltas between two saves."""
    before_story = story_progress_stats(before_save)
    after_story = story_progress_stats(after_save)
    clear_changed = (
        safe_int(after_story["clear_done"])
        - safe_int(before_story["clear_done"])
    )
    superior_changed = (
        safe_int(after_story["superior_done"])
        - safe_int(before_story["superior_done"])
    )
    return {
        "clear_changed": clear_changed,
        "superior_changed": superior_changed,
    }


def diff_payload(
    before_save: core.SaveFile,
    after_save: core.SaveFile,
) -> dict[str, object]:
    """Build high-level diff payload between two save states."""
    before_summary = summary(before_save)
    after_summary = summary(after_save)
    summary_changes = _build_summary_changes(before_summary, after_summary)
    cat_changes = _build_cat_changes(before_save, after_save)
    inventory_changes = _build_inventory_changes(before_save, after_save)
    story_changes = _build_story_changes(before_save, after_save)
    return {
        "summary_changes": summary_changes,
        "cats": cat_changes,
        "inventory": inventory_changes,
        "story": story_changes,
    }


def _resolve_trophy_totals(save_file: core.SaveFile) -> tuple[int, int]:
    """Resolve owned and total trophy counts."""
    owned = 0
    total = 0
    try:
        owned = len(getattr(save_file.medals, "medal_data_1", ()) or ())
        medal_names = core.core_data.get_medal_names(save_file)
        names = getattr(medal_names, "medal_names", None)
        if isinstance(names, list):
            total = sum(
                1
                for row in names
                if isinstance(row, list) and len(row) > 0
            )
        else:
            total = owned
    except Exception:
        total = owned
    return owned, total


def _resolve_metadata_cat_total(save_file: core.SaveFile) -> int:
    """Resolve total cat count from save + game metadata."""
    total = len(tuple(getattr(save_file.cats, "cats", ()) or ()))
    try:
        pic_book = save_file.cats.read_nyanko_picture_book(save_file)
        pb_cats = tuple(getattr(pic_book, "cats", ()) or ())
        total = max(total, len(pb_cats))
    except Exception:
        pass
    return max(total, 0)


def summary(save_file: core.SaveFile) -> dict[str, object]:
    """Build summary payload for the currently loaded save."""
    unlocked_cats = sum(1 for cat in save_file.cats.cats if cat.unlocked)
    user_rank = safe_int(save_file.calculate_user_rank())
    lineups_unlocked, lineups_total = lineup_stats(save_file)
    enemy_unlocked, enemy_total = enemy_guide_stats(save_file)
    cat_claimed, cat_total = cat_guide_stats(save_file)
    story_stats = story_progress_stats(save_file)
    trophy_owned, trophy_total = _resolve_trophy_totals(save_file)

    return {
        "path": str(state.loaded_path) if state.loaded_path else "",
        "inquiry_code": save_file.inquiry_code,
        "country": str(save_file.cc),
        "game_version": save_file.game_version.to_string(),
        "cats_unlocked": unlocked_cats,
        "cats_total": _resolve_metadata_cat_total(save_file),
        "catfood": save_file.catfood,
        "xp": save_file.xp,
        "np": save_file.np,
        "normal_tickets": save_file.normal_tickets,
        "rare_tickets": save_file.rare_tickets,
        "platinum_tickets": save_file.platinum_tickets,
        "legend_tickets": save_file.legend_tickets,
        "leadership": save_file.leadership,
        "trophies_owned": trophy_owned,
        "trophies_total": trophy_total,
        "user_rank": user_rank,
        "lineups_unlocked": lineups_unlocked,
        "lineups_total": lineups_total,
        "enemy_guide_unlocked": enemy_unlocked,
        "enemy_guide_total": enemy_total,
        "cat_guide_claimed": cat_claimed,
        "cat_guide_total": cat_total,
        "story_cleared_stages": safe_int(story_stats["clear_done"]),
        "story_total_stages": safe_int(story_stats["clear_total"]),
        "superior_treasures": safe_int(story_stats["superior_done"]),
        "total_treasures": safe_int(story_stats["treasure_total"]),
        "history": history_state(),
    }


def story_chapter_names() -> list[str]:
    """Return story chapter names for the editor table."""
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


def _build_story_editor_row(index: int, chapter: core.Chapter) -> DiffRow:
    """Build one story-editor row."""
    stages = list(getattr(chapter, "stages", []) or [])
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
    names = story_chapter_names()
    if index < len(names):
        chapter_name = names[index]
    else:
        chapter_name = f"Chapter {index + 1}"
    return {
        "index": index,
        "name": chapter_name,
        "clear_total": clear_total,
        "cleared": clear_done,
        "treasure_total": treasure_total,
        "superior": superior_done,
        "progress": safe_int(getattr(chapter, "progress", 0)),
    }


def story_editor_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build story-editor payload for chapter-level editing."""
    chapters = list(getattr(save_file.story, "chapters", []) or [])
    rows = [
        _build_story_editor_row(index, chapter)
        for index, chapter in enumerate(chapters)
    ]
    return {"ok": True, "chapters": rows, "summary": summary(save_file)}


def apply_story_chapter_values(
    chapter: core.Chapter,
    clear_count: int,
    superior_count: int,
    clear_amount: int = 1,
) -> None:
    """Apply clear/treasure counts to a story chapter structure."""
    stages = list(getattr(chapter, "stages", []) or [])
    clear_total = min(48, len(stages))
    treasure_total = min(49, len(stages))
    clamped_clear_count = max(0, min(clear_count, clear_total))
    clamped_superior_count = max(0, min(superior_count, treasure_total))

    for index, stage in enumerate(stages[:clear_total]):
        if index < clamped_clear_count:
            stage.clear_times = max(1, clear_amount)
        else:
            stage.clear_times = 0

    for index, stage in enumerate(stages[:treasure_total]):
        stage.treasure = 3 if index < clamped_superior_count else 0

    chapter.progress = max(0, min(clamped_clear_count, clear_total))
