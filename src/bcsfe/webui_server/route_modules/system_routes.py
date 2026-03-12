from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from flask import jsonify
from flask import request
from flask import send_from_directory

from ..core import app
from ..core import core
from ..core import ensure_loaded
from ..core import history_state
from ..core import reset_history
from ..core import resolve_input_path
from ..core import restore_snapshot
from ..core import SaveManagement
from ..core import state
from ..core import WEBUI_DIR
from ..services import summary


def _build_status_payload(loaded: bool) -> dict[str, object]:
    """Build status payload for loaded/unloaded state."""
    if not loaded:
        return {
            "loaded": False,
            "summary": None,
            "history": history_state(),
        }
    sf = ensure_loaded()
    return {
        "loaded": True,
        "summary": summary(sf),
        "history": history_state(),
    }


def _pick_open_path(initial: Path) -> str:
    """Open file picker and return chosen path or empty string."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Select SAVE_DATA file",
        initialdir=str(initial),
    )
    root.destroy()
    return str(path)


def _pick_save_path(initial_dir: Path, default_name: str) -> str:
    """Open save-file picker and return chosen path or empty string."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.asksaveasfilename(
        title="Save edited save file",
        initialfile=default_name,
        initialdir=str(initial_dir),
    )
    root.destroy()
    return str(path)


@app.get("/")
def index():
    """Serve web UI root page."""
    return send_from_directory(str(WEBUI_DIR), "index.html")


@app.get("/api/status")
def api_status():
    """Return editor load status."""
    loaded = state.save_file is not None
    return jsonify(_build_status_payload(loaded))


@app.get("/api/history")
def api_history():
    """Return undo/redo state."""
    return jsonify({"ok": True, "history": history_state()})


@app.post("/api/undo")
def api_undo():
    """Move history pointer backward by one."""
    try:
        ensure_loaded()
        if not state.history or state.history_index <= 0:
            raise RuntimeError("Nothing to undo.")
        state.history_index -= 1
        snapshot = state.history[state.history_index]
        sf = restore_snapshot(snapshot)
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/redo")
def api_redo():
    """Move history pointer forward by one."""
    try:
        ensure_loaded()
        if not state.history or state.history_index >= len(state.history) - 1:
            raise RuntimeError("Nothing to redo.")
        state.history_index += 1
        snapshot = state.history[state.history_index]
        sf = restore_snapshot(snapshot)
        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/safe_mode")
def api_safe_mode():
    """Set Safe Mode toggle flag."""
    try:
        payload = request.get_json(force=True)
        state.safe_mode = bool(payload.get("enabled", True))
        return jsonify({"ok": True, "history": history_state()})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/load")
def api_load():
    """Load save file from provided path."""
    try:
        payload = request.get_json(force=True)
        raw_path = Path(payload.get("path", ""))
        file_path = resolve_input_path(raw_path)
        result = SaveManagement.load_save_file_path(
            core.Path(str(file_path)),
            None,
            False,
        )
        if result is None:
            raise RuntimeError("Could not parse save file.")
        save_file, _backup = result
        state.save_file = save_file
        state.loaded_path = file_path
        state.name_cache = {}
        reset_history(save_file, reason="load")
        return jsonify(
            {
                "ok": True,
                "summary": summary(save_file),
                "history": history_state(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/pick_path")
def api_pick_path():
    """Open file picker for SAVE_DATA input path."""
    try:
        initial = Path.home() / "Documents" / "bcsfe" / "saves"
        path = _pick_open_path(initial)
        if not path:
            return jsonify({"ok": False, "error": "No file selected."}), 400
        return jsonify({"ok": True, "path": path})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/save")
def api_save():
    """Write current save file to output path."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        out_path = Path(payload.get("path", "")).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.to_file(core.Path(str(out_path)))
        return jsonify({"ok": True, "path": str(out_path)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/pick_save_path")
def api_pick_save_path():
    """Open save picker for edited output path."""
    try:
        ensure_loaded()
        initial_dir = Path.home() / "Documents" / "bcsfe" / "saves"
        if state.loaded_path is None:
            default_name = "SAVE_DATA.edited"
        else:
            default_name = f"{state.loaded_path.name}.edited"
        path = _pick_save_path(initial_dir, default_name)
        if not path:
            return jsonify(
                {"ok": False, "error": "No output path selected."}
            ), 400
        return jsonify({"ok": True, "path": path})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
