from __future__ import annotations

from ..core import core
from ..core import get_ops_and_presets
from ..core import resolve_preset_key
from .cats_service import clamp_cat_forms


def select_bulk_cats(
    sf: core.SaveFile,
    payload: dict[str, object],
) -> list[core.Cat]:
    """Resolve targeted cats for bulk operations."""
    ids_raw = payload.get("ids")
    cats: list[core.Cat] = []
    if isinstance(ids_raw, list) and ids_raw:
        wanted = {int(cat_id) for cat_id in ids_raw}
        for cat in sf.cats.cats:
            if cat.id in wanted:
                cats.append(cat)
    else:
        cats = list(sf.cats.cats)

    if bool(payload.get("owned_only", False)):
        cats = [cat for cat in cats if bool(cat.unlocked)]
    return cats


def _apply_unlock(cats: list[core.Cat], sf: core.SaveFile) -> None:
    """Unlock selected cats."""
    for cat in cats:
        cat.unlock(sf)


def _apply_legit_max(cats: list[core.Cat], sf: core.SaveFile) -> None:
    """Apply legal max upgrades/forms for selected cats."""
    for cat in cats:
        cat.unlock(sf)
        cat.catguide_collected = True
        power_up = core.PowerUpHelper(cat, sf)
        power_up.max_upgrade()
        cat.upgrade.plus = max(
            cat.upgrade.plus,
            power_up.get_max_possible_plus(),
        )


def _apply_base(cats: list[core.Cat], payload: dict[str, object]) -> None:
    """Apply base-level override."""
    if "base" not in payload:
        return
    base_level = max(1, int(payload.get("base")))
    for cat in cats:
        cat.upgrade.base = base_level - 1


def _apply_plus(cats: list[core.Cat], payload: dict[str, object]) -> None:
    """Apply plus-level override."""
    if "plus" not in payload:
        return
    plus = max(0, int(payload.get("plus")))
    for cat in cats:
        cat.upgrade.plus = plus


def _apply_form(cats: list[core.Cat], payload: dict[str, object]) -> None:
    """Apply current-form override."""
    if "form" not in payload:
        return
    form = max(0, min(3, int(payload.get("form"))))
    for cat in cats:
        cat.current_form = form


def _apply_unlocked_forms(
    cats: list[core.Cat],
    payload: dict[str, object],
) -> None:
    """Apply unlocked-form-count override."""
    if "unlocked_forms" not in payload:
        return
    unlocked_forms = max(0, min(4, int(payload.get("unlocked_forms"))))
    for cat in cats:
        cat.unlocked_forms = unlocked_forms


def apply_bulk_changes(sf: core.SaveFile, payload: dict[str, object]) -> int:
    """Apply all requested bulk cat edits and return affected count."""
    cats = select_bulk_cats(sf, payload)
    if not cats:
        return 0

    if bool(payload.get("unlock", False)):
        _apply_unlock(cats, sf)
    if bool(payload.get("legit_max", False)):
        _apply_legit_max(cats, sf)
    _apply_base(cats, payload)
    _apply_plus(cats, payload)
    _apply_form(cats, payload)
    _apply_unlocked_forms(cats, payload)
    if bool(payload.get("true_form", False)):
        sf.cats.true_form_cats(sf, cats, force=False, set_current_forms=True)
    if bool(payload.get("fourth_form", False)):
        sf.cats.fourth_form_cats(sf, cats, force=False, set_current_forms=True)
    for cat in cats:
        clamp_cat_forms(sf, cat)
    return len(cats)


def apply_preset_changes(
    sf: core.SaveFile,
    preset: str,
) -> tuple[list[str], list[str]]:
    """Apply all operations in one named preset."""
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
