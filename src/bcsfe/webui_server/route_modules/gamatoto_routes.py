from __future__ import annotations

from flask import jsonify
from flask import request

from ..core import app
from ..core import GamatotoHelper
from ..core import ensure_loaded
from ..core import history_state
from ..core import push_history
from ..core import safe_int
from ..core import sync_mygamatoto_index
from ..services import gamatoto_payload
from ..services import set_gamatoto_level


@app.post("/api/sync_mygamatoto")
def api_sync_mygamatoto():
    """Refresh MyGamatoto cache from remote API."""
    try:
        count = sync_mygamatoto_index()
        return jsonify({"ok": True, "count": count})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/gamatoto")
def api_gamatoto():
    """Return Gamatoto editor payload."""
    try:
        sf = ensure_loaded()
        payload = gamatoto_payload(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/gamatoto/update")
def api_gamatoto_update():
    """Update top-level Gamatoto fields."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        gam = sf.gamatoto
        if "level" in payload:
            value = int(payload.get("level", 1))
            gam.xp = max(0, set_gamatoto_level(sf, value))
        if "xp" in payload:
            gam.xp = max(0, safe_int(payload.get("xp"), 0))
        if "remaining_seconds" in payload:
            seconds = float(payload.get("remaining_seconds", 0.0))
            gam.remaining_seconds = max(0.0, seconds)
        if "return_flag" in payload:
            gam.return_flag = bool(payload.get("return_flag"))
        if "dest_id" in payload:
            gam.dest_id = max(0, safe_int(payload.get("dest_id"), 0))
        if "recon_length" in payload:
            value = safe_int(payload.get("recon_length"), 0)
            gam.recon_length = max(0, value)
        if "skin" in payload:
            gam.skin = max(0, safe_int(payload.get("skin"), 0))
        if "is_ad_present" in payload:
            gam.is_ad_present = bool(payload.get("is_ad_present"))

        push_history("gamatoto_update")
        updated = gamatoto_payload(sf)
        updated["history"] = history_state()
        return jsonify(updated)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/gamatoto/helper")
def api_gamatoto_helper():
    """Update one Gamatoto helper slot."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        slot = max(0, int(payload.get("slot", 0)))
        helper_id = int(payload.get("id", -1))
        gam = sf.gamatoto
        helpers = list(getattr(gam.helpers, "helpers", []) or [])
        while slot >= len(helpers):
            helpers.append(GamatotoHelper.init())
        helpers[slot].id = helper_id if helper_id >= 0 else -1
        gam.helpers.helpers = helpers
        push_history(f"gamatoto_helper:{slot}")
        updated = gamatoto_payload(sf)
        updated["history"] = history_state()
        return jsonify(updated)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
