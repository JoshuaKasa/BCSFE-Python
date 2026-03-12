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
from ..core import push_history
from ..core import reset_history
from ..core import reset_core_data_caches
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


def _resolve_version_country(raw: object | None = None) -> core.CountryCode:
    """Resolve country for game-version checks."""
    text = str(raw or "").strip().lower()
    if text in set(core.CountryCode.get_all_str()):
        return core.CountryCode.from_code(text)
    if state.save_file is not None:
        return ensure_loaded().cc
    return core.CountryCode.from_code("en")


def _latest_downloaded_version(country: core.CountryCode) -> core.GameVersion | None:
    """Return latest locally downloaded game-data version for country."""
    versions = core.GameDataGetter.get_all_downloaded_versions().get(
        country.get_code(),
        [],
    )
    if not versions:
        return None
    try:
        latest = max(
            versions,
            key=lambda v: core.GameVersion.from_string(v).game_version,
        )
        return core.GameVersion.from_string(latest)
    except Exception:
        return None


def _latest_remote_version(country: core.CountryCode) -> core.GameVersion | None:
    """Return latest remote metadata game-data version for country."""
    try:
        gdg = core.GameDataGetter(country, core.GameVersion(1), do_print=False)
        if gdg.metadata is None:
            return None
        versions = gdg.get_versions(gdg.metadata) or {}
        cc_versions = versions.get(country.get_code(), {})
        keys = list(cc_versions.keys()) if isinstance(cc_versions, dict) else []
        if not keys:
            return None
        latest = max(
            keys,
            key=lambda v: core.GameVersion.from_string(v).game_version,
        )
        return core.GameVersion.from_string(latest)
    except Exception:
        return None


def _resolve_latest_version(
    country: core.CountryCode,
) -> tuple[core.GameVersion | None, str]:
    """Resolve latest game version using remote metadata with local fallback."""
    remote = _latest_remote_version(country)
    if remote is not None:
        return remote, "remote"
    local = _latest_downloaded_version(country)
    if local is not None:
        return local, "local"
    return None, "none"


def _build_game_version_payload(
    country: core.CountryCode,
    latest: core.GameVersion | None,
    source: str,
) -> dict[str, object]:
    """Build web payload for save-vs-latest game-version status."""
    save_version = None
    outdated = None
    if state.save_file is not None:
        sf = ensure_loaded()
        save_version = sf.game_version.to_string()
        if latest is not None:
            outdated = sf.game_version < latest
    return {
        "ok": True,
        "country": country.get_code(),
        "save_game_version": save_version,
        "latest_game_version": latest.to_string() if latest else None,
        "latest_source": source,
        "is_outdated": outdated,
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


@app.get("/api/game_version/latest")
def api_game_version_latest():
    """Return latest known game version and loaded-save version status."""
    try:
        country = _resolve_version_country(request.args.get("country"))
        latest, source = _resolve_latest_version(country)
        return jsonify(_build_game_version_payload(country, latest, source))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/game_version/update_latest")
def api_game_version_update_latest():
    """Set loaded save game version to latest known version."""
    try:
        sf = ensure_loaded()
        latest, source = _resolve_latest_version(sf.cc)
        if latest is None:
            raise RuntimeError("Could not resolve latest game version.")

        changed = sf.game_version != latest
        if changed:
            sf.set_gv(latest)
            reset_core_data_caches()
            push_history(f"set_game_version:{latest.to_string()}")

        return jsonify(
            {
                "ok": True,
                "changed": changed,
                "summary": summary(sf),
                "history": history_state(),
                "version": _build_game_version_payload(sf.cc, latest, source),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


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
        reset_core_data_caches()
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
