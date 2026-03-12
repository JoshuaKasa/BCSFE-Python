from __future__ import annotations

from flask import jsonify

from ..core import app
from ..core import ensure_loaded
from ..services import cat_guide_stats
from ..services import enemy_guide_stats
from ..services import summary
from ..services import validation_payload


@app.get("/api/validation")
def api_validation():
    """Return full validation payload for loaded save."""
    try:
        sf = ensure_loaded()
        payload = validation_payload(sf)
        payload["summary"] = summary(sf)
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/encyclopedias")
def api_encyclopedias():
    """Return enemy/cat guide summary stats."""
    try:
        sf = ensure_loaded()
        enemy_unlocked, enemy_total = enemy_guide_stats(sf)
        catguide_claimed, catguide_total = cat_guide_stats(sf)
        return jsonify(
            {
                "ok": True,
                "enemy_guide": {
                    "unlocked": enemy_unlocked,
                    "total": enemy_total,
                },
                "cat_guide": {
                    "claimed": catguide_claimed,
                    "total": catguide_total,
                },
                "summary": summary(sf),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
