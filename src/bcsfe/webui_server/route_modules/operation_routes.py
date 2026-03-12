from __future__ import annotations

from flask import jsonify
from flask import request

from ..core import app
from ..core import clone_save
from ..core import ensure_loaded
from ..core import get_ops_and_presets
from ..core import history_state
from ..core import push_history
from ..core import resolve_preset_key
from ..core import state
from ..services import apply_preset_changes
from ..services import diff_payload
from ..services import summary

RISKY_KEYS = frozenset(
    {
        "clear_story_only",
        "clear_story_superior_treasures",
        "clear_story_treasures",
        "clear_all_maps",
    }
)


def _validate_operation_key(
    key: str,
    operations: dict[str, tuple[str, object]],
) -> None:
    """Validate operation key exists in operation registry."""
    if key not in operations:
        raise RuntimeError(f"Unknown operation: {key}")


def _validate_safe_mode_for_operation(
    key: str,
    allow_risky: bool,
) -> None:
    """Validate risky operation against Safe Mode settings."""
    if state.safe_mode and key in RISKY_KEYS and not allow_risky:
        raise RuntimeError(
            "Safe Mode is enabled. Disable it or confirm risky edits."
        )


def _validate_safe_mode_for_preset(
    keys: list[str],
    allow_risky: bool,
) -> None:
    """Validate risky preset operations against Safe Mode settings."""
    has_risky = any(key in RISKY_KEYS for key in keys)
    if state.safe_mode and has_risky and not allow_risky:
        raise RuntimeError(
            "Safe Mode is enabled. Disable it or confirm risky edits."
        )


@app.post("/api/op")
def api_op():
    """Apply one named operation."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        key = payload.get("key", "")
        operations, _ = get_ops_and_presets()
        _validate_operation_key(key, operations)
        allow_risky = bool(payload.get("allow_risky", False))
        _validate_safe_mode_for_operation(key, allow_risky)
        _, operation = operations[key]
        operation(sf)
        push_history(f"op:{key}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/op/preview")
def api_op_preview():
    """Preview one operation diff without applying it."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        key = payload.get("key", "")
        operations, _ = get_ops_and_presets()
        _validate_operation_key(key, operations)
        before = clone_save(sf)
        preview = clone_save(sf)
        _, operation = operations[key]
        operation(preview)
        return jsonify({"ok": True, "diff": diff_payload(before, preview)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/preset")
def api_preset():
    """Apply one named preset."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        preset = resolve_preset_key(payload.get("preset", ""))
        _, presets = get_ops_and_presets()
        keys = presets.get(preset) or []
        if not keys:
            raise RuntimeError(f"Unknown preset: {preset}")
        allow_risky = bool(payload.get("allow_risky", False))
        _validate_safe_mode_for_preset(keys, allow_risky)

        applied, failed = apply_preset_changes(sf, preset)
        if applied:
            push_history(f"preset:{preset}")
        return jsonify(
            {
                "ok": True,
                "applied": applied,
                "failed": failed,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/preset/preview")
def api_preset_preview():
    """Preview one preset diff without applying it."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        preset = resolve_preset_key(payload.get("preset", ""))
        _, presets = get_ops_and_presets()
        if preset not in presets:
            raise RuntimeError(f"Unknown preset: {preset}")
        before = clone_save(sf)
        preview = clone_save(sf)
        _applied, failed = apply_preset_changes(preview, preset)
        return jsonify(
            {
                "ok": True,
                "failed": failed,
                "diff": diff_payload(before, preview),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
