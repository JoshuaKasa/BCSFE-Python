from __future__ import annotations

from flask import jsonify
from flask import request

from ..core import app
from ..core import ensure_loaded
from ..core import history_state
from ..core import push_history
from ..core import safe_int
from ..services import enemy_guide_payload
from ..services import enemy_guide_stats
from ..services import summary


def _build_enemy_guide_summary(sf: object) -> dict[str, int]:
    """Build enemy guide unlocked/total summary payload."""
    enemy_unlocked, enemy_total = enemy_guide_stats(sf)
    return {"unlocked": enemy_unlocked, "total": enemy_total}


def _resolve_enemy_target_ids(
    guide: list[object],
    sf: object,
    action: str,
    query: str,
    mode: str,
) -> list[int]:
    """Resolve target enemy ids for one bulk action."""
    if action in {"unlock_all", "clear_all"}:
        return list(range(len(guide)))
    if action in {"unlock_filtered", "clear_filtered"}:
        filtered = enemy_guide_payload(
            sf,
            query=query,
            filter_mode=mode,
        ).get("enemies", [])
        return [
            safe_int(row.get("id"), -1)
            for row in filtered
            if 0 <= safe_int(row.get("id"), -1) < len(guide)
        ]
    raise RuntimeError(f"Unsupported enemy bulk action: {action}")


def _apply_enemy_bulk_value(
    guide: list[object],
    target_ids: list[int],
    new_value: int,
) -> int:
    """Apply one unlock/clear value to target ids and return change count."""
    changed = 0
    seen: set[int] = set()
    for enemy_id in target_ids:
        if enemy_id in seen:
            continue
        seen.add(enemy_id)
        if safe_int(guide[enemy_id], 0) == new_value:
            continue
        guide[enemy_id] = new_value
        changed += 1
    return changed


@app.get("/api/enemies")
def api_enemies():
    """Return enemy guide rows with current query/filter."""
    try:
        sf = ensure_loaded()
        query = request.args.get("query", "")
        mode = request.args.get("filter", "All")
        payload = enemy_guide_payload(sf, query=query, filter_mode=mode)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/enemies/update")
def api_enemies_update():
    """Update one enemy guide unlock flag."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        enemy_id = int(payload.get("id"))
        unlocked = bool(payload.get("unlocked"))

        guide = list(getattr(sf, "enemy_guide", []) or [])
        if enemy_id < 0 or enemy_id >= len(guide):
            raise RuntimeError(f"Enemy index out of range: {enemy_id}")

        guide[enemy_id] = 1 if unlocked else 0
        sf.enemy_guide = guide
        has_unlock_flag = safe_int(
            getattr(sf, "unlock_enemy_guide", 0),
            0,
        )
        if unlocked and has_unlock_flag == 0:
            sf.unlock_enemy_guide = 1

        push_history(f"enemy:{enemy_id}:{'unlock' if unlocked else 'clear'}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
                "enemy_guide": _build_enemy_guide_summary(sf),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/enemies/bulk")
def api_enemies_bulk():
    """Apply bulk unlock/clear enemy guide actions."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        action = str(payload.get("action", "")).strip().lower()
        query = str(payload.get("query", ""))
        mode = str(payload.get("filter", "All"))

        guide = list(getattr(sf, "enemy_guide", []) or [])
        if not guide:
            raise RuntimeError("Enemy guide data is empty.")

        target_ids = _resolve_enemy_target_ids(guide, sf, action, query, mode)
        new_value = 1 if action.startswith("unlock") else 0
        changed = _apply_enemy_bulk_value(guide, target_ids, new_value)

        sf.enemy_guide = guide
        has_unlock_flag = safe_int(
            getattr(sf, "unlock_enemy_guide", 0),
            0,
        )
        if new_value == 1 and changed > 0 and has_unlock_flag == 0:
            sf.unlock_enemy_guide = 1

        push_history(f"enemy_bulk:{action}:{changed}")
        return jsonify(
            {
                "ok": True,
                "changed": changed,
                "summary": summary(sf),
                "history": history_state(),
                "enemy_guide": _build_enemy_guide_summary(sf),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
