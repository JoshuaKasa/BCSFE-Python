from __future__ import annotations

from ..core import clean_name
from ..core import core
from ..core import gatyaitem_icon_url
from ..core import medal_icon_url
from ..core import safe_int
from ..core import talent_orb_icon_url
from ..core import talent_orb_rank_icon_url

ItemRow = dict[str, object]


def _build_battle_items(save_file: core.SaveFile) -> list[ItemRow]:
    """Build battle-item inventory rows."""
    rows: list[ItemRow] = []
    try:
        battle_defs = core.core_data.get_gatya_item_buy(save_file)
        battle_defs = battle_defs.get_by_category(3)
        names = save_file.battle_items.get_names(save_file) or []
        defs = battle_defs or []
        battle_items = getattr(save_file.battle_items, "items", ()) or ()
        for index, item in enumerate(battle_items):
            item_id = int(defs[index].id) if index < len(defs) else None
            default_name = f"Battle Item {index + 1}"
            raw_name = names[index] if index < len(names) else default_name
            name = raw_name if raw_name else default_name
            rows.append(
                {
                    "index": index,
                    "item_id": item_id,
                    "icon_url": gatyaitem_icon_url(item_id),
                    "name": clean_name(name),
                    "amount": safe_int(item.amount),
                }
            )
    except Exception:
        return rows
    return rows


def _build_catamins(save_file: core.SaveFile) -> list[ItemRow]:
    """Build catamin inventory rows."""
    rows: list[ItemRow] = []
    try:
        item_names = core.core_data.get_gatya_item_names(save_file)
        items = core.core_data.get_gatya_item_buy(save_file).get_by_category(6)
        if items is None:
            return rows
        for index, item in enumerate(items):
            if index >= len(save_file.catamins):
                break
            item_id = int(item.id)
            default_name = f"Catamin {item_id}"
            name = clean_name(item_names.get_name(item_id) or default_name)
            rows.append(
                {
                    "index": index,
                    "item_id": item_id,
                    "icon_url": gatyaitem_icon_url(item_id),
                    "name": name,
                    "amount": safe_int(save_file.catamins[index]),
                }
            )
    except Exception:
        return rows
    return rows


def _build_catseyes(save_file: core.SaveFile) -> list[ItemRow]:
    """Build catseye inventory rows."""
    rows: list[ItemRow] = []
    try:
        item_names = core.core_data.get_gatya_item_names(save_file)
        items = core.core_data.get_gatya_item_buy(save_file).get_by_category(5)
        if items is None:
            return rows
        for index, item in enumerate(items):
            if index >= len(save_file.catseyes):
                break
            item_id = int(item.id)
            default_name = f"Catseye {item_id}"
            name = clean_name(item_names.get_name(item_id) or default_name)
            rows.append(
                {
                    "index": index,
                    "item_id": item_id,
                    "icon_url": gatyaitem_icon_url(item_id),
                    "name": name,
                    "amount": int(save_file.catseyes[index]),
                }
            )
    except Exception:
        return rows
    return rows


def _build_catfruit(save_file: core.SaveFile) -> list[ItemRow]:
    """Build catfruit inventory rows."""
    rows: list[ItemRow] = []
    try:
        matatabi = core.Matatabi(save_file)
        names = matatabi.get_names() or []
        fruits = matatabi.matatabi or []
        for index, amount in enumerate(save_file.catfruit):
            item_id = int(fruits[index].id) if index < len(fruits) else None
            default_name = f"Catfruit {index}"
            raw_name = names[index] if index < len(names) else default_name
            name = clean_name(raw_name or default_name)
            rows.append(
                {
                    "index": index,
                    "item_id": item_id,
                    "icon_url": gatyaitem_icon_url(item_id),
                    "name": name,
                    "amount": int(amount),
                }
            )
    except Exception:
        return rows
    return rows


def _build_materials(save_file: core.SaveFile) -> list[ItemRow]:
    """Build base-material inventory rows."""
    rows: list[ItemRow] = []
    try:
        item_names = core.core_data.get_gatya_item_names(save_file)
        items = core.core_data.get_gatya_item_buy(save_file).get_by_category(7)
        materials = save_file.ototo.base_materials.materials
        if items is None:
            return rows
        for index, item in enumerate(items):
            if index >= len(materials):
                break
            item_id = int(item.id)
            default_name = f"Material {item_id}"
            name = clean_name(item_names.get_name(item_id) or default_name)
            rows.append(
                {
                    "index": index,
                    "item_id": item_id,
                    "icon_url": gatyaitem_icon_url(item_id),
                    "name": name,
                    "amount": int(materials[index].amount),
                }
            )
    except Exception:
        return rows
    return rows


def _build_orb_counts(save_file: core.SaveFile) -> dict[int, int]:
    """Build a map of orb_id to inventory count."""
    counts: dict[int, int] = {}
    source = getattr(getattr(save_file, "talent_orbs", None), "orbs", {}) or {}
    for orb_id, orb in source.items():
        parsed_id = safe_int(orb_id, -1)
        if parsed_id < 0:
            continue
        counts[parsed_id] = safe_int(getattr(orb, "value", 0), 0)
    return counts


def _build_talent_orb_label(target: str, rank: str, effect: str) -> str:
    """Build the display label used for a talent-orb row."""
    label = f"{target} {rank} Orb"
    if effect:
        return f"{label} - {effect}"
    return label


def _build_known_talent_orbs(
    save_file: core.SaveFile,
    orb_counts: dict[int, int],
) -> list[ItemRow]:
    """Build rows from known game-data orb definitions."""
    rows: list[ItemRow] = []
    orb_info_list = core.OrbInfoList.create(save_file)
    has_rows = getattr(orb_info_list, "orb_info_list", None)
    if orb_info_list is None or not has_rows:
        return rows

    for index, orb_info in enumerate(orb_info_list.orb_info_list):
        raw_orb_info = getattr(orb_info, "raw_orb_info", None)
        orb_id = safe_int(getattr(raw_orb_info, "orb_id", index), index)
        if orb_id < 0:
            continue

        rank = clean_name(str(getattr(orb_info, "rank", "") or "Unknown"))
        target_raw = getattr(orb_info, "target", None)
        target = clean_name(str(target_raw)) if target_raw else "All"
        raw_effect = str(getattr(orb_info, "effect", "") or "")
        clean_effect = raw_effect.replace("%@", "")
        clean_effect = clean_effect.replace("  ", " ")
        clean_effect = clean_effect.strip(" -:()")
        effect = clean_name(clean_effect)
        rank_id = safe_int(getattr(raw_orb_info, "rank_id", -1), -1)
        target_id = safe_int(getattr(raw_orb_info, "target_id", -1), -1)
        effect_id = safe_int(getattr(raw_orb_info, "effect_id", -1), -1)

        rows.append(
            {
                "index": int(orb_id),
                "item_id": -1,
                "icon_url": talent_orb_rank_icon_url(rank),
                "name": _build_talent_orb_label(target, rank, effect),
                "amount": int(max(0, orb_counts.get(orb_id, 0))),
                "group": target,
                "rank": rank,
                "effect": effect,
                "target_id": target_id,
                "rank_id": rank_id,
                "effect_id": effect_id,
            }
        )

    return rows


def _build_unknown_talent_orbs(orb_counts: dict[int, int]) -> list[ItemRow]:
    """Build fallback rows when orb metadata cannot be loaded."""
    rows: list[ItemRow] = []
    for orb_id in sorted(orb_counts.keys()):
        rows.append(
            {
                "index": int(orb_id),
                "item_id": -1,
                "icon_url": talent_orb_icon_url(),
                "name": f"Talent Orb {orb_id}",
                "amount": int(max(0, orb_counts.get(orb_id, 0))),
                "group": "Unknown",
                "rank": "",
                "effect": "",
                "target_id": -1,
                "rank_id": -1,
                "effect_id": -1,
            }
        )
    return rows


def _get_talent_orb_sort_key(row: ItemRow) -> tuple[str, str, str, int]:
    """Return stable sorting tuple for talent orb rows."""
    group = str(row.get("group", "Unknown"))
    effect = str(row.get("effect", ""))
    rank = str(row.get("rank", ""))
    index = safe_int(row.get("index"), 0)
    return group, effect, rank, index


def _build_talent_orbs(save_file: core.SaveFile) -> list[ItemRow]:
    """Build talent-orb inventory rows from game-data and save counts."""
    orb_counts = _build_orb_counts(save_file)
    try:
        rows = _build_known_talent_orbs(save_file, orb_counts)
        if not rows:
            rows = _build_unknown_talent_orbs(orb_counts)
    except Exception:
        rows = _build_unknown_talent_orbs(orb_counts)
    rows.sort(key=_get_talent_orb_sort_key)
    return rows


def inventory_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build inventory payload used by the web UI."""
    return {
        "ok": True,
        "battle_items": _build_battle_items(save_file),
        "catamins": _build_catamins(save_file),
        "catseyes": _build_catseyes(save_file),
        "catfruit": _build_catfruit(save_file),
        "materials": _build_materials(save_file),
        "talent_orbs": _build_talent_orbs(save_file),
    }


def _get_trophy_sort_key(row: ItemRow) -> tuple[bool, int]:
    """Return stable sorting tuple for trophy rows."""
    owned = bool(row.get("owned", False))
    trophy_id = safe_int(row.get("id"), 0)
    return (not owned, trophy_id)


def trophies_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build trophy payload used by the web UI."""
    rows: list[ItemRow] = []
    owned = set(getattr(save_file.medals, "medal_data_1", ()) or ())
    value_map = getattr(save_file.medals, "medal_data_2", {}) or {}

    medal_names_list: list[list[str]] | None = None
    try:
        medal_names = core.core_data.get_medal_names(save_file)
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
            description = row[1] if len(row) > 1 else ""
            rows.append(
                {
                    "id": int(medal_id),
                    "name": name,
                    "description": str(description),
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

    rows.sort(key=_get_trophy_sort_key)
    return {"ok": True, "trophies": rows}


def clamp_resource_value(
    save_file: core.SaveFile,
    key: str,
    value: object,
) -> int:
    """Clamp a resource value against its legal maximum."""
    value_i = max(0, safe_int(value))
    value_type_map: dict[str, core.MaxValueType] = {
        "catfood": core.MaxValueType.CATFOOD,
        "xp": core.MaxValueType.XP,
        "np": core.MaxValueType.NP,
        "normal_tickets": core.MaxValueType.NORMAL_TICKETS,
        "rare_tickets": core.MaxValueType.RARE_TICKETS,
        "platinum_tickets": core.MaxValueType.PLATINUM_TICKETS,
        "legend_tickets": core.MaxValueType.LEGEND_TICKETS,
        "leadership": core.MaxValueType.LEADERSHIP,
    }
    value_type = value_type_map.get(key)
    if value_type is None:
        return value_i
    max_value = safe_int(core.core_data.max_value_manager.get(value_type), 0)
    return min(value_i, max(0, max_value))
