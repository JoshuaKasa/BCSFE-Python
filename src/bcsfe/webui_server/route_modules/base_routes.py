from __future__ import annotations

from flask import jsonify
from flask import request

from ..core import app
from ..core import core
from ..core import ensure_loaded
from ..core import history_state
from ..core import ototo_data
from ..core import push_history
from ..core import safe_int
from ..services import base_cannons_payload
from ..services import base_upgrades_payload
from ..services import summary


def _build_cannons_response(sf: core.SaveFile) -> dict[str, object]:
    """Build common response payload after cannon mutations."""
    payload = base_cannons_payload(sf)
    payload["summary"] = summary(sf)
    payload["history"] = history_state()
    return payload


def _ensure_cannons_object(sf: core.SaveFile) -> object:
    """Ensure save has initialized cannon data structure."""
    if sf.ototo.cannons is None:
        sf.ototo.cannons = ototo_data.Cannons.init(sf.game_version)
    return sf.ototo.cannons


def _parse_selected_parts(payload: dict[str, object]) -> list[int]:
    """Parse and clamp selected cannon part ids from payload."""
    selected_parts = list(payload.get("selected_parts") or [])
    while len(selected_parts) < 3:
        selected_parts.append(0)
    return [
        max(0, safe_int(selected_parts[index], 0))
        for index in range(3)
    ]


def _apply_selected_parts(
    cannons_obj: object,
    payload: dict[str, object],
) -> None:
    """Apply selected cannon part ids."""
    if "selected_parts" not in payload:
        return
    cleaned = _parse_selected_parts(payload)
    if not cannons_obj.selected_parts:
        cannons_obj.selected_parts = [cleaned]
        return
    cannons_obj.selected_parts[0] = cleaned


def _get_or_create_cannon(cannons_obj: object, cannon_id: int) -> object:
    """Resolve existing cannon row or create a new one."""
    cannon = cannons_obj.cannons.get(cannon_id)
    if cannon is None:
        cannon = ototo_data.Cannon.init()
        cannons_obj.cannons[cannon_id] = cannon
    return cannon


def _apply_cannon_development(
    cannon: object,
    payload: dict[str, object],
) -> None:
    """Apply development state update to one cannon."""
    if "development" not in payload:
        return
    value = safe_int(payload.get("development"), 0)
    cannon.development = max(0, min(3, value))


def _parse_levels(payload: dict[str, object], cannon: object) -> list[int]:
    """Parse incoming part levels and ensure cannon array shape."""
    levels = list(payload.get("levels") or [])
    while len(levels) < 3:
        levels.append(0)
    while len(cannon.levels) < 3:
        cannon.levels.append(0)
    return levels


def _resolve_part_max_level(
    recipe: ototo_data.CastleRecipeUnlock | None,
    cannon_id: int,
    part_id: int,
) -> int:
    """Resolve max legal level for one cannon part."""
    if recipe is None:
        return 0
    max_level = recipe.get_max_level(cannon_id, part_id)
    if max_level is None:
        max_level = recipe.get_max_part_level(part_id)
    return max(0, safe_int(max_level, 0))


def _apply_cannon_levels(
    recipe: ototo_data.CastleRecipeUnlock | None,
    cannon_id: int,
    cannon: object,
    payload: dict[str, object],
) -> None:
    """Apply part level changes to one cannon."""
    if "levels" not in payload:
        return
    levels = _parse_levels(payload, cannon)
    for part_id in range(3):
        max_level = _resolve_part_max_level(recipe, cannon_id, part_id)
        next_level = safe_int(levels[part_id], 0)
        cannon.levels[part_id] = max(0, min(next_level, max_level))


def _apply_cannon_patch(sf: core.SaveFile, payload: dict[str, object]) -> None:
    """Apply selected-parts and cannon-level updates from payload."""
    cannons_obj = _ensure_cannons_object(sf)
    recipe = ototo_data.CastleRecipeUnlock(sf)
    _apply_selected_parts(cannons_obj, payload)
    if "cannon_id" not in payload:
        return
    cannon_id = max(0, safe_int(payload.get("cannon_id"), 0))
    cannon = _get_or_create_cannon(cannons_obj, cannon_id)
    _apply_cannon_development(cannon, payload)
    _apply_cannon_levels(recipe, cannon_id, cannon, payload)


@app.get("/api/base/upgrades")
def api_base_upgrades():
    """Return base-upgrade rows and summary."""
    try:
        sf = ensure_loaded()
        payload = base_upgrades_payload(sf)
        payload["summary"] = summary(sf)
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/base/cannons")
def api_base_cannons():
    """Return base-cannon table payload."""
    try:
        sf = ensure_loaded()
        return jsonify(_build_cannons_response(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/base/cannons/update")
def api_base_cannons_update():
    """Update base-cannon fields and return refreshed table."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        _apply_cannon_patch(sf, payload)
        push_history("base_cannons_update")
        return jsonify(_build_cannons_response(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/base/update")
def api_base_update():
    """Update one base upgrade level pair."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        skill_id = int(payload.get("id"))
        base_level = max(1, int(payload.get("base", 1)))
        plus_level = max(0, int(payload.get("plus", 0)))

        ability_data = core.core_data.get_ability_data(sf)
        ability = None
        if ability_data is not None:
            ability = ability_data.get_ability_data_item(skill_id)
        max_base = max(
            0,
            safe_int(getattr(ability, "max_base_level", 1)) - 1,
        )
        max_plus = max(0, safe_int(getattr(ability, "max_plus_level", 0)))
        upgrade = core.Upgrade(
            min(plus_level, max_plus),
            min(base_level - 1, max_base),
        )
        sf.special_skills.set_upgrade(
            skill_id,
            upgrade,
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
