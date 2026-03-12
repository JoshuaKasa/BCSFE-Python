from __future__ import annotations

from flask import jsonify
from flask import request

from ..core import app
from ..core import cat_number
from ..core import cat_sprite_url
from ..core import clone_save
from ..core import core
from ..core import ensure_loaded
from ..core import get_cat_name
from ..core import history_state
from ..core import is_hidden_cat_name
from ..core import push_history
from ..core import safe_int
from ..services import apply_bulk_changes
from ..services import cat_talents_payload
from ..services import clamp_cat_forms
from ..services import diff_payload
from ..services import get_cat_total_forms
from ..services import summary


def _collect_selected_cats(
    sf: core.SaveFile,
    ids: list[int],
) -> list[core.Cat]:
    """Resolve selected cat objects from numeric ids."""
    cats: list[core.Cat] = []
    for cat_id in ids:
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is not None:
            cats.append(cat)
    return cats


def _resolve_talent(
    talents: list[core.CatTalent],
    talent_id: int,
) -> core.CatTalent | None:
    """Resolve one talent row by id."""
    for talent in talents:
        if safe_int(getattr(talent, "id", -1)) == talent_id:
            return talent
    return None


def _resolve_talent_max_level(
    sf: core.SaveFile,
    cat: core.Cat,
    talent_id: int,
    fallback_level: int,
) -> int:
    """Resolve legal maximum level for a cat talent."""
    max_level = max(1, fallback_level)
    try:
        talent_data = sf.cats.read_talent_data(sf)
        if talent_data is None:
            return max_level
        skill = talent_data.get_skill_from_cat(cat.id, talent_id)
        if skill is None:
            return max_level
        return max(1, safe_int(getattr(skill, "max_lv", 1), 1))
    except Exception:
        return max_level


def _build_cats_payload(
    sf: core.SaveFile,
    query: str,
    mode: str,
) -> list[dict[str, object]]:
    """Build filtered cat rows for cat table view."""
    rows: list[dict[str, object]] = []
    for cat in sf.cats.cats:
        if mode == "Unlocked" and not cat.unlocked:
            continue
        if mode == "Locked" and cat.unlocked:
            continue

        name = get_cat_name(cat)
        if is_hidden_cat_name(name):
            continue
        search_blob = f"{cat.id} {name}".lower()
        if query and query not in search_blob:
            continue

        number = cat_number(cat)
        total_forms = get_cat_total_forms(sf, cat)
        rows.append(
            {
                "id": cat.id,
                "number": number,
                "name": name,
                "owned": bool(cat.unlocked),
                "base": int(cat.upgrade.base + 1),
                "plus": int(cat.upgrade.plus),
                "form": int(cat.current_form),
                "unlocked_forms": int(cat.unlocked_forms),
                "fourth": int(cat.fourth_form),
                "total_forms": int(total_forms),
                "image_url": (
                    f"https://onestoppress.com/images/{number}_square.png"
                ),
                "sprite_url": cat_sprite_url(cat.id, cat.current_form),
                "talent_count": len(list(getattr(cat, "talents", []) or [])),
            }
        )
    return rows


@app.get("/api/cats")
def api_cats():
    """Return filtered cat table rows."""
    try:
        sf = ensure_loaded()
        query = request.args.get("query", "").strip().lower()
        mode = request.args.get("filter", "All")
        rows = _build_cats_payload(sf, query, mode)
        return jsonify({"ok": True, "cats": rows})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/cats/talents")
def api_cats_talents():
    """Return talents payload for one cat."""
    try:
        sf = ensure_loaded()
        cat_id = int(request.args.get("cat_id", "-1"))
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is None:
            raise RuntimeError(f"Cat not found: {cat_id}")
        payload = cat_talents_payload(sf, cat)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/talents/update")
def api_cats_talent_update():
    """Update one talent level for a cat."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        cat_id = int(payload.get("cat_id"))
        talent_id = int(payload.get("talent_id"))
        new_level = max(0, int(payload.get("level", 0)))
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is None:
            raise RuntimeError(f"Cat not found: {cat_id}")
        talents = list(getattr(cat, "talents", []) or [])
        target = _resolve_talent(talents, talent_id)
        if target is None:
            raise RuntimeError(
                f"Talent not found for cat {cat_id}: {talent_id}"
            )
        max_level = _resolve_talent_max_level(sf, cat, talent_id, new_level)
        target.level = max(0, min(new_level, max_level))
        cat.talents = talents
        push_history(f"cat_talent:{cat_id}:{talent_id}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
                "talents": cat_talents_payload(sf, cat).get("talents", []),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/action")
def api_cats_action():
    """Apply one action to selected cat ids."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        action = payload.get("action", "")
        ids = [int(value) for value in payload.get("ids", [])]
        cats = _collect_selected_cats(sf, ids)

        if action == "unlock":
            for cat in cats:
                cat.unlock(sf)
        elif action == "true_form":
            sf.cats.true_form_cats(
                sf,
                cats,
                force=False,
                set_current_forms=True,
            )
        elif action == "fourth_form":
            sf.cats.fourth_form_cats(
                sf,
                cats,
                force=False,
                set_current_forms=True,
            )
        elif action == "legit_max":
            for cat in cats:
                cat.unlock(sf)
                cat.catguide_collected = True
                power_up = core.PowerUpHelper(cat, sf)
                power_up.max_upgrade()
                cat.upgrade.plus = max(
                    cat.upgrade.plus,
                    power_up.get_max_possible_plus(),
                )
        else:
            raise RuntimeError(f"Unknown action: {action}")

        push_history(f"cat_action:{action}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/update")
def api_cats_update():
    """Update one cat row fields."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        cat_id = int(payload.get("id"))
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is None:
            raise RuntimeError(f"Cat not found: {cat_id}")

        if "owned" in payload:
            owned = bool(payload.get("owned"))
            if owned:
                cat.unlock(sf)
            else:
                cat.unlocked = 0
        if "base" in payload:
            base_level = max(1, int(payload.get("base")))
            cat.upgrade.base = base_level - 1
        if "plus" in payload:
            cat.upgrade.plus = max(0, int(payload.get("plus")))
        if "form" in payload:
            cat.current_form = max(0, min(3, int(payload.get("form"))))
        if "unlocked_forms" in payload:
            cat.unlocked_forms = max(
                0,
                min(4, int(payload.get("unlocked_forms"))),
            )
        if "fourth" in payload:
            cat.fourth_form = max(0, int(payload.get("fourth")))

        clamp_cat_forms(sf, cat)
        push_history(f"cat_update:{cat_id}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/bulk")
def api_cats_bulk():
    """Apply bulk cat updates to selected rows."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        count = apply_bulk_changes(sf, payload)
        if count > 0:
            push_history("cats_bulk")
        return jsonify(
            {
                "ok": True,
                "count": count,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/bulk/preview")
def api_cats_bulk_preview():
    """Preview bulk cat changes without persisting."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        before = clone_save(sf)
        preview = clone_save(sf)
        count = apply_bulk_changes(preview, payload)
        return jsonify(
            {
                "ok": True,
                "count": count,
                "diff": diff_payload(before, preview),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
