from __future__ import annotations

from ..core import BASE_UPGRADE_ICON_FALLBACK_IDS
from ..core import clean_name
from ..core import core
from ..core import gatyaitem_icon_url
from ..core import ototo_data
from ..core import safe_int

ItemRow = dict[str, object]


def _get_cannon_sort_key(kv: tuple[object, object]) -> int:
    """Return integer cannon id sort key for cannon map rows."""
    cannon_id, _cannon = kv
    return safe_int(cannon_id, 0)


def _build_base_upgrade_row(
    save_file: core.SaveFile,
    names: core.GatyaItemNames,
    items: list[core.GatyaItemBuyItem],
    ability_data: core.AbilityData | None,
    index: int,
    skill: core.SpecialSkill,
) -> ItemRow:
    """Build one base-upgrade row."""
    item_id = items[index].id if index < len(items) else None
    fallback_id = BASE_UPGRADE_ICON_FALLBACK_IDS.get(index)
    resolved_id = item_id if item_id is not None else fallback_id
    raw_name = names.get_name(resolved_id) if resolved_id is not None else None
    ability = None
    if ability_data is not None:
        ability = ability_data.get_ability_data_item(index)
    max_base_raw = safe_int(getattr(ability, "max_base_level", 0))
    max_plus_raw = safe_int(getattr(ability, "max_plus_level", 0))
    return {
        "id": index,
        "item_id": resolved_id,
        "icon_url": gatyaitem_icon_url(resolved_id),
        "name": clean_name(raw_name or f"Base Upgrade {index + 1}"),
        "base": safe_int(skill.upgrade.base) + 1,
        "plus": safe_int(skill.upgrade.plus),
        "max_base": max(1, max_base_raw),
        "max_plus": max(0, max_plus_raw),
    }


def base_upgrades_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build base-upgrades payload for the web UI."""
    rows: list[ItemRow] = []
    item_names = core.core_data.get_gatya_item_names(save_file)
    items = core.core_data.get_gatya_item_buy(save_file).get_by_category(2)
    if items is None:
        items = []
    ability_data = core.core_data.get_ability_data(save_file)
    skills = save_file.special_skills.get_valid_skills()

    for index, skill in enumerate(skills):
        row = _build_base_upgrade_row(
            save_file,
            item_names,
            items,
            ability_data,
            index,
            skill,
        )
        rows.append(row)
    return {"ok": True, "upgrades": rows}


def _build_cannon_parts(
    cannon_id: int,
    levels: list[int],
    part_names: list[str],
    recipe: ototo_data.CastleRecipeUnlock,
) -> list[ItemRow]:
    """Build cannon-part rows for one cannon."""
    parts: list[ItemRow] = []
    for part_id in range(3):
        max_level = recipe.get_max_level(cannon_id, part_id)
        if max_level is None:
            max_level = recipe.get_max_part_level(part_id)
        max_level_i = max(0, safe_int(max_level, levels[part_id]))
        part_name = part_names[part_id] if part_id < len(part_names) else ""
        parts.append(
            {
                "part_id": part_id,
                "name": str(part_name) or f"Part {part_id + 1}",
                "level": max(0, safe_int(levels[part_id], 0)),
                "max_level": max_level_i,
            }
        )
    return parts


def _build_selected_parts(cannons_obj: object) -> list[int]:
    """Build selected part IDs payload list."""
    selected = list(getattr(cannons_obj, "selected_parts", ()) or ())
    if not selected:
        return [0, 0, 0]

    first = list(selected[0] or [])
    while len(first) < 3:
        first.append(0)
    return [max(0, safe_int(first[index], 0)) for index in range(3)]


def _build_cannon_rows(
    save_file: core.SaveFile,
    cannons_obj: object,
) -> list[ItemRow]:
    """Build cannon rows from save data."""
    recipe = ototo_data.CastleRecipeUnlock(save_file)
    descriptions = ototo_data.CannonDescriptions(save_file)
    cannon_map = dict(getattr(cannons_obj, "cannons", {}) or {})
    rows: list[ItemRow] = []

    for raw_id, cannon in sorted(cannon_map.items(), key=_get_cannon_sort_key):
        cannon_id = safe_int(raw_id, 0)
        description = descriptions.get_cannon_description(cannon_id)
        default_parts = ["Effect", "Foundation", "Style"]
        if description is None:
            part_names = default_parts
        else:
            part_names = description.get_part_names()
        levels = list(getattr(cannon, "levels", []) or [])
        while len(levels) < 3:
            levels.append(0)

        parts = _build_cannon_parts(cannon_id, levels, part_names, recipe)
        cannon_name = None
        if description is not None:
            cannon_name = description.get_cannon_name()
        rows.append(
            {
                "cannon_id": cannon_id,
                "name": clean_name(cannon_name or f"Cannon {cannon_id}"),
                "development": max(
                    0,
                    safe_int(getattr(cannon, "development", 0), 0),
                ),
                "max_development": 3,
                "parts": parts,
            }
        )

    return rows


def base_cannons_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build base-cannons payload for the web UI."""
    ototo = getattr(save_file, "ototo", None)
    cannons_obj = getattr(ototo, "cannons", None) if ototo is not None else None
    if cannons_obj is None:
        return {"ok": True, "cannons": [], "selected_parts": [0, 0, 0]}

    rows = _build_cannon_rows(save_file, cannons_obj)
    selected_parts = _build_selected_parts(cannons_obj)
    return {
        "ok": True,
        "cannons": rows,
        "selected_parts": selected_parts,
    }
