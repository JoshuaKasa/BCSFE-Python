from __future__ import annotations

from flask import jsonify
from flask import request

from ..core import app
from ..core import core
from ..core import ensure_loaded
from ..core import history_state
from ..core import push_history
from ..services import clamp_resource_value
from ..services import inventory_payload
from ..services import summary
from ..services import trophies_payload


def _validate_index(index: int, size: int, label: str) -> None:
    """Validate a 0-based index for a fixed-size collection."""
    if index < 0 or index >= size:
        raise RuntimeError(f"{label} index out of range: {index}")


def _update_catseyes(sf: core.SaveFile, index: int, amount: int) -> None:
    """Apply catseye inventory value with cap clamp."""
    _validate_index(index, len(sf.catseyes), "Catseye")
    max_value = core.core_data.max_value_manager.get(
        core.MaxValueType.CATSEYES,
    )
    sf.catseyes[index] = min(amount, int(max_value))


def _resolve_catfruit_max_value(sf: core.SaveFile) -> int:
    """Resolve catfruit cap for old/new game version format."""
    manager = core.core_data.max_value_manager
    if sf.game_version < 110400:
        return int(manager.get_old(core.MaxValueType.CATFRUIT))
    return int(manager.get_new(core.MaxValueType.CATFRUIT))


def _update_catfruit(sf: core.SaveFile, index: int, amount: int) -> None:
    """Apply catfruit inventory value with version-aware cap."""
    _validate_index(index, len(sf.catfruit), "Catfruit")
    sf.catfruit[index] = min(amount, _resolve_catfruit_max_value(sf))


def _update_catamins(sf: core.SaveFile, index: int, amount: int) -> None:
    """Apply catamin inventory value with cap clamp."""
    _validate_index(index, len(sf.catamins), "Catamin")
    max_value = core.core_data.max_value_manager.get(
        core.MaxValueType.CATAMINS,
    )
    sf.catamins[index] = min(amount, int(max_value))


def _update_battle_items(sf: core.SaveFile, index: int, amount: int) -> None:
    """Apply battle-item inventory value with cap clamp."""
    items = sf.battle_items.items
    _validate_index(index, len(items), "Battle item")
    max_value = core.core_data.max_value_manager.get(
        core.MaxValueType.BATTLE_ITEMS,
    )
    items[index].amount = min(amount, int(max_value))


def _update_materials(sf: core.SaveFile, index: int, amount: int) -> None:
    """Apply base-material inventory value with cap clamp."""
    mats = sf.ototo.base_materials.materials
    _validate_index(index, len(mats), "Material")
    max_value = core.core_data.max_value_manager.get(
        core.MaxValueType.BASE_MATERIALS,
    )
    mats[index].amount = min(amount, int(max_value))


def _ensure_talent_orbs(sf: core.SaveFile) -> None:
    """Ensure talent orb storage object exists on save file."""
    if getattr(sf, "talent_orbs", None) is not None:
        return
    sf.talent_orbs = core.TalentOrbs.init()


def _update_talent_orbs(sf: core.SaveFile, index: int, amount: int) -> None:
    """Apply talent-orb inventory value with cap clamp."""
    if index < 0:
        raise RuntimeError(f"Talent orb id out of range: {index}")
    max_value = core.core_data.max_value_manager.get(
        core.MaxValueType.TALENT_ORBS,
    )
    capped = min(amount, int(max_value))
    _ensure_talent_orbs(sf)
    if capped <= 0:
        sf.talent_orbs.orbs.pop(index, None)
        return
    sf.talent_orbs.orbs[index] = core.TalentOrb(index, capped)


def _apply_inventory_update(
    sf: core.SaveFile,
    category: str,
    index: int,
    amount: int,
) -> None:
    """Dispatch category-specific inventory update handlers."""
    if category == "catseyes":
        _update_catseyes(sf, index, amount)
        return
    if category == "catfruit":
        _update_catfruit(sf, index, amount)
        return
    if category == "catamins":
        _update_catamins(sf, index, amount)
        return
    if category == "battle_items":
        _update_battle_items(sf, index, amount)
        return
    if category == "materials":
        _update_materials(sf, index, amount)
        return
    if category == "talent_orbs":
        _update_talent_orbs(sf, index, amount)
        return
    raise RuntimeError(f"Unsupported inventory category: {category}")


@app.get("/api/inventory")
def api_inventory():
    """Return inventory page payload."""
    try:
        sf = ensure_loaded()
        return jsonify(inventory_payload(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/trophies")
def api_trophies():
    """Return trophy table payload."""
    try:
        sf = ensure_loaded()
        return jsonify(trophies_payload(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/trophies/update")
def api_trophies_update():
    """Toggle one trophy ownership flag."""
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
    """Update one inventory row amount."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        category = str(payload.get("category", "")).strip().lower()
        index = int(payload.get("index"))
        amount = max(0, int(payload.get("amount")))
        _apply_inventory_update(sf, category, index, amount)
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
    """Update editable top-level resources in one request."""
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
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
