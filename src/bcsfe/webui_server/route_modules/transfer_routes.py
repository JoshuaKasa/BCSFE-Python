from __future__ import annotations

import re
from datetime import datetime
from datetime import timezone
from pathlib import Path

from flask import jsonify
from flask import request

from ..core import app
from ..core import build_transfer_backup_payload
from ..core import core
from ..core import delete_transfer_record
from ..core import ensure_loaded
from ..core import history_state
from ..core import mark_matching_downloads_uploaded
from ..core import parse_game_version
from ..core import persist_transfer_records
from ..core import push_transfer_record
from ..core import reset_history
from ..core import resolve_transfer_record_id
from ..core import state
from ..core import transfer_storage_info
from ..core import update_transfer_record
from ..services import summary


def _resolve_fallback_country_code() -> str:
    """Resolve default country code from loaded save or fallback."""
    if state.save_file is None:
        return "en"
    return ensure_loaded().cc.get_code()


def _resolve_country_code(
    payload: dict[str, object],
) -> tuple[str, core.CountryCode]:
    """Parse and validate country code payload field."""
    fallback_cc = _resolve_fallback_country_code()
    country_code = str(payload.get("country", fallback_cc)).strip().lower()
    valid_ccs = set(core.CountryCode.get_all_str())
    if country_code not in valid_ccs:
        raise RuntimeError(f"Invalid country code: {country_code}")
    return country_code, core.CountryCode.from_code(country_code)


def _resolve_fallback_game_version() -> core.GameVersion:
    """Resolve default game version from loaded save or fallback."""
    if state.save_file is None:
        return core.GameVersion(120200)
    return ensure_loaded().game_version


def _resolve_game_version(payload: dict[str, object]) -> core.GameVersion:
    """Parse game version from payload with default fallback."""
    fallback_gv = _resolve_fallback_game_version()
    return parse_game_version(payload.get("game_version"), fallback_gv)


def _resolve_download_path(transfer_code: str, country_code: str) -> Path:
    """Build output path for downloaded transfer save file."""
    download_dir = (
        Path.home() / "Documents" / "bcsfe" / "saves" / "transfer_downloads"
    )
    download_dir.mkdir(parents=True, exist_ok=True)
    suffix = re.sub(r"[^A-Za-z0-9]", "", transfer_code)[-6:] or "code"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"SAVE_DATA_{country_code}_{suffix}_{timestamp}"
    return download_dir / name


def _download_transfer_save(
    transfer_code: str,
    confirmation_code: str,
    country: core.CountryCode,
    game_version: core.GameVersion,
) -> core.SaveFile:
    """Download one save file from transfer and confirmation codes."""
    server_handler, result = core.ServerHandler.from_codes(
        transfer_code,
        confirmation_code,
        country,
        game_version,
        print=False,
        save_backup=True,
    )
    if server_handler is not None:
        return server_handler.save_file
    if result is not None and result.response is not None:
        status_code = result.response.status_code
        raise RuntimeError(
            (
                "Failed to download save data "
                f"(HTTP {status_code}). Check codes/country."
            )
        )
    raise RuntimeError("Failed to download save data from server.")


def _replace_loaded_save(
    downloaded_save: core.SaveFile,
    out_path: Path,
) -> None:
    """Replace currently loaded save context with downloaded save."""
    state.save_file = downloaded_save
    state.loaded_path = out_path
    state.name_cache = {}
    reset_history(downloaded_save, reason="transfer_download")


def _build_download_record(
    downloaded_save: core.SaveFile,
    transfer_code: str,
    confirmation_code: str,
    country_code: str,
    game_version: core.GameVersion,
    out_path: Path,
) -> dict[str, object]:
    """Build transfer-history row for a successful download."""
    return {
        "kind": "download",
        "country": country_code,
        "game_version": game_version.to_string(),
        "transfer_code": transfer_code,
        "confirmation_code": confirmation_code,
        "path": str(out_path),
        "inquiry_code": downloaded_save.inquiry_code,
        "needs_upload": True,
    }


@app.get("/api/transfer/history")
def api_transfer_history():
    """Return transfer history records with storage metadata."""
    try:
        return jsonify(
            {
                "ok": True,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/clear")
def api_transfer_clear():
    """Clear persisted transfer history."""
    try:
        state.transfer_records = []
        persist_transfer_records()
        return jsonify(
            {
                "ok": True,
                "records": [],
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/update")
def api_transfer_update():
    """Patch one transfer-history row."""
    try:
        payload = request.get_json(force=True)
        record_id = str(payload.get("id", "")).strip()
        fallback = payload.get("fallback", {})
        fallback_obj = fallback if isinstance(fallback, dict) else None
        record_id = resolve_transfer_record_id(record_id, fallback_obj)
        patch = payload.get("patch", {})
        if not isinstance(patch, dict):
            raise RuntimeError("Patch must be an object.")
        record = update_transfer_record(record_id, patch)
        return jsonify(
            {
                "ok": True,
                "record": record,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/delete")
def api_transfer_delete():
    """Delete one transfer-history row."""
    try:
        payload = request.get_json(force=True)
        record_id = str(payload.get("id", "")).strip()
        fallback = payload.get("fallback", {})
        fallback_obj = fallback if isinstance(fallback, dict) else None
        record_id = resolve_transfer_record_id(record_id, fallback_obj)
        delete_transfer_record(record_id)
        return jsonify(
            {
                "ok": True,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/transfer/backup")
def api_transfer_backup():
    """Return transfer history backup payload."""
    try:
        stamp = datetime.now(timezone.utc).astimezone().strftime(
            "%Y%m%d_%H%M%S"
        )
        filename = f"transfer_history_backup_{stamp}.json"
        return jsonify(
            {
                "ok": True,
                "filename": filename,
                "backup": build_transfer_backup_payload(),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/download")
def api_transfer_download():
    """Download save from transfer codes and load it in the editor."""
    try:
        payload = request.get_json(force=True)
        transfer_code = str(payload.get("transfer_code", "")).strip()
        confirmation_code = str(payload.get("confirmation_code", "")).strip()
        if not transfer_code or not confirmation_code:
            raise RuntimeError(
                "Transfer code and confirmation code are required."
            )

        country_code, country = _resolve_country_code(payload)
        game_version = _resolve_game_version(payload)
        downloaded_save = _download_transfer_save(
            transfer_code,
            confirmation_code,
            country,
            game_version,
        )
        out_path = _resolve_download_path(transfer_code, country_code)
        downloaded_save.to_file(core.Path(str(out_path)))
        _replace_loaded_save(downloaded_save, out_path)
        record_data = _build_download_record(
            downloaded_save,
            transfer_code,
            confirmation_code,
            country_code,
            game_version,
            out_path,
        )
        record = push_transfer_record(record_data)
        return jsonify(
            {
                "ok": True,
                "summary": summary(downloaded_save),
                "history": history_state(),
                "path": str(out_path),
                "record": record,
                "records": list(state.transfer_records or []),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/transfer/upload")
def api_transfer_upload():
    """Upload current save and return new transfer codes."""
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        upload_managed_items = bool(payload.get("upload_managed_items", True))
        result = core.ServerHandler(sf, print=False).get_codes(
            upload_managed_items=upload_managed_items,
        )
        if result is None:
            raise RuntimeError(
                "Upload failed. Could not get transfer/confirmation codes."
            )
        transfer_code, confirmation_code = result

        record = push_transfer_record(
            {
                "kind": "upload",
                "country": sf.cc.get_code(),
                "game_version": sf.game_version.to_string(),
                "transfer_code": transfer_code,
                "confirmation_code": confirmation_code,
                "path": str(state.loaded_path) if state.loaded_path else "",
                "inquiry_code": sf.inquiry_code,
                "needs_upload": False,
            }
        )
        linked_count = mark_matching_downloads_uploaded(
            sf,
            str(record.get("id", "")),
        )
        return jsonify(
            {
                "ok": True,
                "transfer_code": transfer_code,
                "confirmation_code": confirmation_code,
                "record": record,
                "linked_downloads": linked_count,
                "records": list(state.transfer_records or []),
                "summary": summary(sf),
                "history": history_state(),
                "storage": transfer_storage_info(),
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400
