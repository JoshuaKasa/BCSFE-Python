from __future__ import annotations

from bcsfe import core

from .bootstrap import state
from .helpers import ensure_loaded


def history_state() -> dict[str, object]:
    """Build undo/redo state metadata for the current session."""
    size = len(state.history or [])
    index = state.history_index
    can_undo = bool(size > 0 and index > 0)
    can_redo = bool(size > 0 and index < size - 1)
    return {
        "size": size,
        "index": index,
        "can_undo": can_undo,
        "can_redo": can_redo,
        "safe_mode": bool(state.safe_mode),
    }


def snapshot_save(sf: core.SaveFile) -> dict[str, object]:
    """Serialize a save snapshot for undo/redo storage."""
    return sf.to_dict()


def restore_snapshot(snapshot: dict[str, object]) -> core.SaveFile:
    """Restore a snapshot and set it as current loaded save."""
    restored = core.SaveFile.from_dict(snapshot, warn=False)
    state.save_file = restored
    state.name_cache = {}
    return restored


def reset_history(sf: core.SaveFile, reason: str = "load") -> None:
    """Replace history stack with one snapshot and reason."""
    snap = snapshot_save(sf)
    state.history = [snap]
    state.history_reasons = [reason]
    state.history_index = 0


def push_history(reason: str) -> None:
    """Append current save snapshot to history with rolling limit."""
    sf = ensure_loaded()
    snap = snapshot_save(sf)
    history = state.history or []
    reasons = state.history_reasons or []
    index = state.history_index

    if index < len(history) - 1:
        history = history[: index + 1]
        reasons = reasons[: index + 1]

    history.append(snap)
    reasons.append(reason)

    if len(history) > state.history_limit:
        overflow = len(history) - state.history_limit
        history = history[overflow:]
        reasons = reasons[overflow:]

    state.history = history
    state.history_reasons = reasons
    state.history_index = len(history) - 1
