from __future__ import annotations

from flask import jsonify
from flask import request

from ..core import app
from ..core import core
from ..core import ensure_loaded
from ..core import history_state
from ..core import push_history
from ..core import safe_int
from ..services import apply_story_chapter_values
from ..services import dashboard_payload
from ..services import legend_progress_stats
from ..services import playtime_payload
from ..services import story_editor_payload
from ..services import story_progress_stats
from ..services import summary


def _build_story_update_rows(sf: core.SaveFile) -> list[dict[str, object]]:
    """Build story editor rows after an update."""
    return story_editor_payload(sf).get("chapters", [])


def _apply_story_bulk_action(action: str, chapter: core.Chapter) -> None:
    """Apply one bulk story action to a chapter."""
    stages = list(getattr(chapter, "stages", []) or [])
    clear_total = min(48, len(stages))
    treasure_total = min(49, len(stages))
    if action == "set_all_superior":
        apply_story_chapter_values(chapter, clear_total, treasure_total)
        return
    if action == "set_all_cleared":
        apply_story_chapter_values(chapter, clear_total, 0)
        return
    if action == "reset_all":
        apply_story_chapter_values(chapter, 0, 0)
        return
    raise RuntimeError(f"Unknown story bulk action: {action}")


@app.get("/api/dashboard")
def api_dashboard():
    """Return dashboard payload."""
    try:
        sf = ensure_loaded()
        payload = dashboard_payload(sf)
        payload["summary"] = summary(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/playtime")
def api_playtime():
    """Return current playtime payload."""
    try:
        sf = ensure_loaded()
        payload = playtime_payload(sf)
        payload["summary"] = summary(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/playtime/update")
def api_playtime_update():
    """Update playtime fields."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        hours = max(0, safe_int(payload.get("hours"), 0))
        minutes = max(0, min(59, safe_int(payload.get("minutes"), 0)))
        seconds = max(0, min(59, safe_int(payload.get("seconds"), 0)))
        play_time = core.PlayTime.from_hours_mins_secs(hours, minutes, seconds)
        sf.officer_pass.play_time = max(0, safe_int(play_time.frames, 0))

        push_history("playtime_update")
        updated = playtime_payload(sf)
        updated["summary"] = summary(sf)
        updated["history"] = history_state()
        return jsonify(updated)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/progress/story")
def api_progress_story():
    """Return story progress stats."""
    try:
        sf = ensure_loaded()
        return jsonify(
            {
                "ok": True,
                "story": story_progress_stats(sf),
                "legend": legend_progress_stats(sf),
                "summary": summary(sf),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/story/editor")
def api_story_editor():
    """Return chapter-level story editor payload."""
    try:
        sf = ensure_loaded()
        payload = story_editor_payload(sf)
        payload["history"] = history_state()
        return jsonify(payload)
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/story/update")
def api_story_update():
    """Update one story chapter clear and treasure counts."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        chapter_index = int(payload.get("chapter"))
        clear_count = max(0, int(payload.get("cleared", 0)))
        superior_count = max(0, int(payload.get("superior", 0)))
        clear_amount = max(1, int(payload.get("clear_amount", 1)))

        chapters = list(getattr(sf.story, "chapters", []) or [])
        if chapter_index < 0 or chapter_index >= len(chapters):
            raise RuntimeError(f"Story chapter out of range: {chapter_index}")
        chapter = chapters[chapter_index]
        apply_story_chapter_values(
            chapter,
            clear_count,
            superior_count,
            clear_amount=clear_amount,
        )
        push_history(f"story_chapter:{chapter_index}")
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "story": _build_story_update_rows(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/story/bulk")
def api_story_bulk():
    """Apply bulk story action to all chapters."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        action = str(payload.get("action", "")).strip().lower()
        chapters = list(getattr(sf.story, "chapters", []) or [])
        if not chapters:
            raise RuntimeError("No story chapters available.")

        changed = 0
        for chapter in chapters:
            _apply_story_bulk_action(action, chapter)
            changed += 1

        push_history(f"story_bulk:{action}:{changed}")
        return jsonify(
            {
                "ok": True,
                "changed": changed,
                "summary": summary(sf),
                "story": _build_story_update_rows(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
