from __future__ import annotations

from ..core import clean_name
from ..core import core
from ..core import enemy_icon_url
from ..core import safe_int

StoryRow = dict[str, object]
LegendRow = dict[str, object]


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


def _stage_clear_count(stage: object) -> int:
    """Return stage clear count across map structures with different field names."""
    clear_times = safe_int(getattr(stage, "clear_times", 0), 0)
    if clear_times > 0:
        return clear_times
    return safe_int(getattr(stage, "clear_amount", 0), 0)


def _legend_map_names(
    save_file: core.SaveFile,
    base_index: int,
    map_count: int,
) -> dict[int, str | None]:
    """Load map-name lookup from Map_Name.csv for one base-index range."""
    if map_count <= 0:
        return {}

    try:
        gdg = core.core_data.get_game_data_getter(save_file)
        map_name_data = gdg.download("resLocal", "Map_Name.csv")
        if map_name_data is None:
            return {}
        csv = core.CSV(
            map_name_data,
            core.Delimeter.from_country_code_res(save_file.cc),
        )
    except Exception:
        return {}

    names: dict[int, str | None] = {}
    end_index = base_index + map_count
    for row in csv:
        map_id = safe_int(row[0].to_int(), -1)
        if map_id < base_index or map_id >= end_index:
            continue
        local_index = map_id - base_index
        raw_name = row[1].to_str().strip()
        names[local_index] = clean_name(raw_name) if raw_name else None
    return names


def _legend_map_names_range(
    save_file: core.SaveFile,
    base_index: int,
    end_index: int,
) -> dict[int, str | None]:
    """Load map names from Map_Name.csv for a fixed [base, end) id range."""
    if end_index <= base_index:
        return {}
    try:
        gdg = core.core_data.get_game_data_getter(save_file)
        map_name_data = gdg.download("resLocal", "Map_Name.csv")
        if map_name_data is None:
            return {}
        csv = core.CSV(
            map_name_data,
            core.Delimeter.from_country_code_res(save_file.cc),
        )
    except Exception:
        return {}

    names: dict[int, str | None] = {}
    for row in csv:
        map_id = safe_int(row[0].to_int(), -1)
        if map_id < base_index or map_id >= end_index:
            continue
        local_index = map_id - base_index
        raw_name = row[1].to_str().strip()
        names[local_index] = clean_name(raw_name) if raw_name else None
    return names


def _legend_stage_totals_from_stage_names(
    save_file: core.SaveFile,
    code: str,
    base_index: int,
    no_r_prefix: bool = False,
) -> dict[int, int]:
    """Resolve per-map stage counts from StageName CSV rows."""
    try:
        map_names = core.MapNames(
            save_file,
            code,
            base_index=base_index,
            output=False,
            no_r_prefix=no_r_prefix,
        )
    except Exception:
        return {}
    totals: dict[int, int] = {}
    for map_index, stage_names in (map_names.stage_names or {}).items():
        names = tuple(stage_names or ())
        non_placeholder = sum(
            1
            for name in names
            if str(name).strip() and str(name).strip() != "＠"
        )
        totals[map_index] = non_placeholder
    return totals


def _legend_star_totals_from_map_option(
    save_file: core.SaveFile,
    base_index: int,
    map_indexes: set[int],
) -> dict[int, int]:
    """Resolve per-map star counts from Map_option.csv crown counts."""
    map_option = core.MapOption.from_save(save_file)
    if map_option is None:
        return {}
    totals: dict[int, int] = {}
    for map_index in map_indexes:
        line = map_option.get_map(base_index + map_index)
        if line is None:
            continue
        totals[map_index] = max(0, safe_int(getattr(line, "crown_count", 0), 0))
    return totals


def _legend_rows_from_maps(
    maps: tuple[object, ...],
    names: dict[int, str | None],
    fallback_stage_totals: dict[int, int] | None = None,
    fallback_star_totals: dict[int, int] | None = None,
) -> list[LegendRow]:
    """Build map-level legend rows from star/stage chapter structures."""
    rows: list[LegendRow] = []
    if not names:
        return rows
    indexes = sorted(set(names.keys()) | set(range(len(maps))))
    for map_index in indexes:
        display_name = names.get(map_index)
        # Hide unnamed/placeholder map slots and only show known map ids.
        if not display_name:
            continue
        stars_total = 0
        stars_cleared = 0
        total_stages = 0
        cleared_stages = 0
        if map_index < len(maps):
            chapter_stars = maps[map_index]
            stars = tuple(getattr(chapter_stars, "chapters", ()) or ())
            stars_total = len(stars)
            for star in stars:
                stages = tuple(getattr(star, "stages", ()) or ())
                star_total = len(stages)
                star_cleared = sum(
                    1
                    for stage in stages
                    if _stage_clear_count(stage) > 0
                )
                total_stages += star_total
                cleared_stages += star_cleared
                if star_total > 0 and star_cleared >= star_total:
                    stars_cleared += 1
        else:
            per_star_total = safe_int(
                (fallback_stage_totals or {}).get(map_index),
                0,
            )
            stars_total = safe_int(
                (fallback_star_totals or {}).get(map_index),
                0,
            )
            if per_star_total > 0 and stars_total <= 0:
                stars_total = 1
            total_stages = max(0, per_star_total) * max(0, stars_total)
            # Ignore metadata-only placeholders that have no stage definitions.
            if total_stages <= 0:
                continue
        name = display_name
        rows.append(
            {
                "index": map_index,
                "name": name,
                "stars_total": stars_total,
                "stars_cleared": stars_cleared,
                "total_stages": total_stages,
                "cleared_stages": cleared_stages,
            }
        )
    return rows


def _legend_group(
    key: str,
    name: str,
    maps: tuple[object, ...],
    map_names: dict[int, str | None],
    fallback_stage_totals: dict[int, int] | None = None,
    fallback_star_totals: dict[int, int] | None = None,
) -> LegendRow:
    """Build one legend progress group with map rows and summary totals."""
    map_rows = _legend_rows_from_maps(
        maps,
        map_names,
        fallback_stage_totals=fallback_stage_totals,
        fallback_star_totals=fallback_star_totals,
    )
    maps_total = len(map_rows)
    maps_started = sum(
        1
        for row in map_rows
        if safe_int(row.get("cleared_stages"), 0) > 0
    )
    maps_cleared = sum(
        1
        for row in map_rows
        if safe_int(row.get("total_stages"), 0) > 0
        and safe_int(row.get("cleared_stages"), 0) >= safe_int(row.get("total_stages"), 0)
    )
    total_stages = sum(safe_int(row.get("total_stages"), 0) for row in map_rows)
    cleared_stages = sum(safe_int(row.get("cleared_stages"), 0) for row in map_rows)
    return {
        "key": key,
        "name": name,
        "maps_total": maps_total,
        "maps_started": maps_started,
        "maps_cleared": maps_cleared,
        "total_stages": total_stages,
        "cleared_stages": cleared_stages,
        "maps": map_rows,
    }


def _event_group_maps(save_file: core.SaveFile, type_index: int) -> tuple[object, ...]:
    """Resolve one event map group (e.g., SoL) by type index."""
    event = getattr(save_file, "event_stages", None)
    groups = tuple(getattr(event, "chapters", ()) or ())
    if type_index < 0 or type_index >= len(groups):
        return ()
    group = groups[type_index]
    return tuple(getattr(group, "chapters", ()) or ())


def _chapters_maps(container: object | None) -> tuple[object, ...]:
    """Resolve map list from chapter-like containers."""
    if container is None:
        return ()
    return tuple(getattr(container, "chapters", ()) or ())


def legend_progress_stats(save_file: core.SaveFile) -> dict[str, object]:
    """Build legend-related progression payload for SoL/UL/ZL/LQ."""
    sol_maps = _event_group_maps(save_file, 0)
    uncanny_container = getattr(getattr(save_file, "uncanny", None), "chapters", None)
    zero_legends = getattr(save_file, "zero_legends", None)
    legend_quest = getattr(save_file, "legend_quest", None)
    zero_maps = _chapters_maps(zero_legends)
    zero_names = _legend_map_names_range(save_file, 34000, 37000)
    zero_indexes = set(zero_names.keys()) | set(range(len(zero_maps)))
    zero_stage_totals = _legend_stage_totals_from_stage_names(
        save_file,
        "ND",
        base_index=34000,
    )
    zero_star_totals = _legend_star_totals_from_map_option(
        save_file,
        34000,
        zero_indexes,
    )

    groups = [
        _legend_group(
            "sol",
            "Stories of Legend",
            sol_maps,
            _legend_map_names(save_file, 0, len(sol_maps)),
        ),
        _legend_group(
            "uncanny",
            "Uncanny Legends",
            _chapters_maps(uncanny_container),
            _legend_map_names(
                save_file,
                13000,
                len(_chapters_maps(uncanny_container)),
            ),
        ),
        _legend_group(
            "zero_legends",
            "Zero Legends",
            zero_maps,
            zero_names,
            fallback_stage_totals=zero_stage_totals,
            fallback_star_totals=zero_star_totals,
        ),
        _legend_group(
            "legend_quest",
            "Legend Quest",
            _chapters_maps(legend_quest),
            _legend_map_names(
                save_file,
                16000,
                len(_chapters_maps(legend_quest)),
            ),
        ),
    ]

    maps_total = sum(safe_int(group.get("maps_total"), 0) for group in groups)
    maps_started = sum(safe_int(group.get("maps_started"), 0) for group in groups)
    maps_cleared = sum(safe_int(group.get("maps_cleared"), 0) for group in groups)
    total_stages = sum(safe_int(group.get("total_stages"), 0) for group in groups)
    cleared_stages = sum(safe_int(group.get("cleared_stages"), 0) for group in groups)
    return {
        "groups": groups,
        "maps_total": maps_total,
        "maps_started": maps_started,
        "maps_cleared": maps_cleared,
        "total_stages": total_stages,
        "cleared_stages": cleared_stages,
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
