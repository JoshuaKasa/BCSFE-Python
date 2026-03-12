from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from uuid import uuid4

from bcsfe import core

from ..constants import TRANSFER_BACKUP_VERSION
from ..constants import TRANSFER_HISTORY_LIMIT
from .bootstrap import TRANSFER_CODES_PATH
from .bootstrap import state

TransferRow = dict[str, object]


def transfer_storage_info() -> dict[str, str]:
    """Return transfer-history and download storage locations."""
    downloads_dir = (
        Path.home() / "Documents" / "bcsfe" / "saves" / "transfer_downloads"
    )
    return {
        "history_path": str(TRANSFER_CODES_PATH),
        "downloads_dir": str(downloads_dir),
    }


def _new_transfer_record_id() -> str:
    """Create a sortable unique id for transfer-history rows."""
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d%H%M%S")
    return f"{stamp}_{uuid4().hex[:10]}"


def _to_bool(value: object, default: bool = False) -> bool:
    """Normalize mixed bool-like values used in old transfer entries."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "pending"}:
        return True
    if text in {"0", "false", "no", "n", "off", "done", "uploaded"}:
        return False
    return default


def _normalize_kind(raw: TransferRow) -> str:
    """Normalize transfer record kind to upload/download."""
    kind_value = str(raw.get("kind", "")).strip().lower()
    if kind_value == "upload":
        return "upload"
    return "download"


def _normalize_timestamp(raw: TransferRow, default_ts: str) -> str:
    """Normalize record timestamp."""
    return str(raw.get("timestamp") or default_ts)


def _normalize_str_field(raw: TransferRow, key: str) -> str:
    """Normalize one string field from a raw transfer record."""
    return str(raw.get(key, "")).strip()


def normalize_transfer_record(raw: TransferRow) -> TransferRow:
    """Normalize transfer record shape and value types."""
    kind = _normalize_kind(raw)
    default_needs_upload = kind == "download"
    now_ts = datetime.now(timezone.utc).astimezone().isoformat(
        timespec="seconds",
    )
    normalized: TransferRow = {
        "id": str(raw.get("id") or _new_transfer_record_id()),
        "timestamp": _normalize_timestamp(raw, now_ts),
        "kind": kind,
        "country": _normalize_str_field(raw, "country").lower(),
        "game_version": _normalize_str_field(raw, "game_version"),
        "transfer_code": _normalize_str_field(raw, "transfer_code"),
        "confirmation_code": _normalize_str_field(raw, "confirmation_code"),
        "path": _normalize_str_field(raw, "path"),
        "inquiry_code": _normalize_str_field(raw, "inquiry_code"),
        "note": _normalize_str_field(raw, "note"),
        "needs_upload": _to_bool(
            raw.get("needs_upload"),
            default=default_needs_upload,
        ),
        "uploaded_at": _normalize_str_field(raw, "uploaded_at"),
        "uploaded_by": _normalize_str_field(raw, "uploaded_by"),
    }
    return normalized


def _normalize_record_list(records: list[TransferRow]) -> list[TransferRow]:
    """Normalize a transfer record list with history-limit cap."""
    cleaned = [normalize_transfer_record(row) for row in records]
    return cleaned[:TRANSFER_HISTORY_LIMIT]


def load_transfer_records() -> None:
    """Load transfer-history file into runtime state."""
    if not TRANSFER_CODES_PATH.exists():
        state.transfer_records = []
        return
    try:
        records = json.loads(TRANSFER_CODES_PATH.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            state.transfer_records = []
            return
        raw_rows = [row for row in records if isinstance(row, dict)]
        state.transfer_records = _normalize_record_list(raw_rows)
        persist_transfer_records()
    except Exception:
        state.transfer_records = []


def persist_transfer_records() -> None:
    """Persist in-memory transfer records to disk."""
    rows = list(state.transfer_records or [])
    state.transfer_records = _normalize_record_list(rows)
    payload = json.dumps(
        state.transfer_records,
        ensure_ascii=False,
        indent=2,
    )
    TRANSFER_CODES_PATH.write_text(payload, encoding="utf-8")


def push_transfer_record(record: TransferRow) -> TransferRow:
    """Insert transfer record at top of history and persist."""
    records = list(state.transfer_records or [])
    created_at = datetime.now(timezone.utc).astimezone().isoformat(
        timespec="seconds",
    )
    entry = normalize_transfer_record(
        {
            "id": _new_transfer_record_id(),
            "timestamp": created_at,
            **record,
        }
    )
    records.insert(0, entry)
    state.transfer_records = _normalize_record_list(records)
    persist_transfer_records()
    return entry


def _transfer_record_matches_fallback(
    row: TransferRow,
    fallback: TransferRow,
) -> bool:
    """Return whether one row matches a fallback record identity."""
    checks = 0
    comparable_fields: tuple[str, ...] = (
        "timestamp",
        "transfer_code",
        "confirmation_code",
        "kind",
        "country",
        "game_version",
        "path",
        "inquiry_code",
    )
    for field in comparable_fields:
        expected = str(fallback.get(field, "") or "").strip()
        if not expected:
            continue
        checks += 1
        actual = str(row.get(field, "") or "").strip()
        if field in {"kind", "country"}:
            if actual.lower() != expected.lower():
                return False
        elif actual != expected:
            return False
    return checks > 0


def _resolve_existing_record_id(
    records: list[TransferRow],
    record_id: str,
) -> str | None:
    """Find and return an existing record id."""
    for row in records:
        current_id = str(row.get("id", "")).strip()
        if current_id == record_id:
            return record_id
    return None


def _resolve_fallback_record_id(
    records: list[TransferRow],
    fallback: TransferRow,
) -> str | None:
    """Resolve or create id for a fallback-identified row."""
    for idx, row in enumerate(records):
        if not _transfer_record_matches_fallback(row, fallback):
            continue
        existing = str(row.get("id", "")).strip()
        if existing:
            return existing
        row["id"] = _new_transfer_record_id()
        state.transfer_records = _normalize_record_list(records)
        persist_transfer_records()
        refreshed = state.transfer_records[idx]
        return str(refreshed.get("id", "")).strip()
    return None


def resolve_transfer_record_id(
    record_id: str,
    fallback: dict[str, object] | None = None,
) -> str:
    """Resolve transfer record id by id or fallback row data."""
    rid = str(record_id or "").strip()
    records = list(state.transfer_records or [])
    if rid:
        resolved = _resolve_existing_record_id(records, rid)
        if resolved is not None:
            return resolved
        raise RuntimeError("Transfer history record not found.")
    if isinstance(fallback, dict):
        resolved = _resolve_fallback_record_id(records, fallback)
        if resolved is not None:
            return resolved
    raise RuntimeError("Transfer history record id is required.")


def update_transfer_record(
    record_id: str,
    patch: dict[str, object],
) -> TransferRow:
    """Patch editable fields for one transfer-history row."""
    rid = str(record_id or "").strip()
    if not rid:
        raise RuntimeError("Transfer history record id is required.")
    records = list(state.transfer_records or [])
    editable_fields: tuple[str, ...] = (
        "kind",
        "country",
        "game_version",
        "transfer_code",
        "confirmation_code",
        "path",
        "inquiry_code",
        "note",
        "needs_upload",
        "uploaded_at",
        "uploaded_by",
    )
    for idx, current in enumerate(records):
        if str(current.get("id", "")) != rid:
            continue
        next_record = dict(current)
        for key in editable_fields:
            if key in patch:
                next_record[key] = patch.get(key)
        next_record["id"] = str(current.get("id", rid))
        next_record["timestamp"] = str(current.get("timestamp", ""))
        normalized = normalize_transfer_record(next_record)
        records[idx] = normalized
        state.transfer_records = _normalize_record_list(records)
        persist_transfer_records()
        return normalized
    raise RuntimeError("Transfer history record not found.")


def delete_transfer_record(record_id: str) -> None:
    """Delete one transfer-history row by id."""
    rid = str(record_id or "").strip()
    if not rid:
        raise RuntimeError("Transfer history record id is required.")
    records = list(state.transfer_records or [])
    filtered = [row for row in records if str(row.get("id", "")) != rid]
    if len(filtered) == len(records):
        raise RuntimeError("Transfer history record not found.")
    state.transfer_records = _normalize_record_list(filtered)
    persist_transfer_records()


def _is_matching_download(
    row: TransferRow,
    inquiry_code: str,
    loaded_path: str,
) -> bool:
    """Return whether download row matches current save identity."""
    if row.get("kind") != "download":
        return False
    if not bool(row.get("needs_upload", False)):
        return False
    row_inquiry = str(row.get("inquiry_code", "")).strip()
    row_path = str(row.get("path", "")).strip()
    same_inquiry = bool(inquiry_code and row_inquiry == inquiry_code)
    same_path = bool(loaded_path and row_path == loaded_path)
    return same_inquiry or same_path


def mark_matching_downloads_uploaded(
    sf: core.SaveFile,
    upload_record_id: str,
) -> int:
    """Mark matching download records as uploaded by a new upload row."""
    records = list(state.transfer_records or [])
    inquiry_code = str(getattr(sf, "inquiry_code", "") or "").strip()
    loaded_path = str(state.loaded_path or "").strip()
    uploaded_at = datetime.now(timezone.utc).astimezone().isoformat(
        timespec="seconds",
    )
    changed = 0
    for row in records:
        if str(row.get("id", "")) == str(upload_record_id):
            continue
        if not _is_matching_download(row, inquiry_code, loaded_path):
            continue
        row["needs_upload"] = False
        row["uploaded_at"] = uploaded_at
        row["uploaded_by"] = str(upload_record_id)
        changed += 1
    if changed:
        state.transfer_records = _normalize_record_list(records)
        persist_transfer_records()
    return changed


def build_transfer_backup_payload() -> dict[str, object]:
    """Build export payload for transfer-history backup download."""
    exported_at = datetime.now(timezone.utc).astimezone().isoformat(
        timespec="seconds",
    )
    return {
        "version": TRANSFER_BACKUP_VERSION,
        "exported_at": exported_at,
        "records": list(state.transfer_records or []),
    }
