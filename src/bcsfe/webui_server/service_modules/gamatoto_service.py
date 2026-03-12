from __future__ import annotations

from ..core import clean_name
from ..core import core
from ..core import safe_int
from .diff_summary_service import summary


def _build_helper_name(member: object, member_id: int) -> str:
    """Resolve helper display name with safe fallbacks."""
    if member is not None:
        return clean_name(member.name)
    if member_id < 0:
        return "Empty"
    return f"Member {member_id}"


def _build_helper_rows(
    gam: core.Gamatoto,
    members: core.GamatotoMembersNames | None,
    max_helpers: int,
) -> list[dict[str, object]]:
    """Build helper rows for Gamatoto editor table."""
    helper_rows: list[dict[str, object]] = []
    helper_ids = [
        safe_int(helper.id, -1)
        for helper in list(getattr(gam.helpers, "helpers", []) or [])
    ]
    target_len = max(len(helper_ids), max_helpers)
    for slot in range(target_len):
        member_id = helper_ids[slot] if slot < len(helper_ids) else -1
        member = None
        if members is not None and member_id >= 0:
            member = members.get_member(member_id)
        helper_rows.append(
            {
                "slot": slot,
                "id": member_id,
                "name": _build_helper_name(member, member_id),
                "rarity": safe_int(getattr(member, "rarity", 0)),
                "bonus": safe_int(getattr(member, "bonus", 0)),
            }
        )
    return helper_rows


def gamatoto_payload(sf: core.SaveFile) -> dict[str, object]:
    """Build Gamatoto payload for the web UI."""
    gam = sf.gamatoto
    levels = core.core_data.get_gamatoto_levels(sf)
    members = core.core_data.get_gamatoto_members_name(sf)
    current_level = None
    max_level = None
    max_helpers = 0
    if levels is not None:
        current_level = levels.get_level_from_xp(safe_int(gam.xp))
        max_level = levels.get_max_level()
        max_helpers = safe_int(levels.get_total_helpers(), 0)
    helper_rows = _build_helper_rows(gam, members, max_helpers)
    return {
        "ok": True,
        "summary": summary(sf),
        "current_level": safe_int(getattr(current_level, "level", 1), 1),
        "max_level": safe_int(max_level, 1),
        "max_helpers": safe_int(max_helpers, max(0, len(helper_rows))),
        "xp": safe_int(gam.xp),
        "remaining_seconds": float(getattr(gam, "remaining_seconds", 0.0)),
        "return_flag": bool(getattr(gam, "return_flag", False)),
        "dest_id": safe_int(getattr(gam, "dest_id", 0)),
        "recon_length": safe_int(getattr(gam, "recon_length", 0)),
        "skin": safe_int(getattr(gam, "skin", 0)),
        "is_ad_present": bool(getattr(gam, "is_ad_present", False)),
        "helpers": helper_rows,
    }


def set_gamatoto_level(sf: core.SaveFile, level: int) -> int:
    """Convert target level into legal Gamatoto XP value."""
    levels = core.core_data.get_gamatoto_levels(sf)
    if levels is None:
        return max(0, level)
    max_level = safe_int(levels.get_max_level(), 1)
    target = max(1, min(level, max_level))
    xp = levels.get_xp_from_level(target)
    if xp is None:
        return safe_int(sf.gamatoto.xp)
    return safe_int(xp)
