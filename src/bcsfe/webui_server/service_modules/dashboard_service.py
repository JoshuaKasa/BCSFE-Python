from __future__ import annotations

from ..core import core
from ..core import safe_int
from .story_stats_service import cat_guide_stats
from .story_stats_service import enemy_guide_stats
from .story_stats_service import lineup_stats
from .story_stats_service import story_progress_stats

CardRow = dict[str, object]


def _calculate_ratio(done: int, total: int) -> float:
    """Return completion ratio for a done/total pair."""
    if total <= 0:
        return 0.0
    return float(done) / float(total)


def _build_user_rank_card(user_rank: int) -> CardRow:
    """Build User Rank card row."""
    return {
        "id": "user_rank",
        "label": "User Rank",
        "value": user_rank,
        "subtitle": "Calculated from units + base upgrades",
    }


def _build_lineups_card(lineups: tuple[int, int]) -> CardRow:
    """Build lineups completion card row."""
    unlocked, total = lineups
    return {
        "id": "lineups",
        "label": "Lineups",
        "value": f"{unlocked}/{total}",
        "percent": _calculate_ratio(unlocked, total),
    }


def _build_story_clear_card(story_stats: dict[str, object]) -> CardRow:
    """Build story clear completion card row."""
    clear_done = safe_int(story_stats.get("clear_done"), 0)
    clear_total = safe_int(story_stats.get("clear_total"), 0)
    return {
        "id": "story_clear",
        "label": "Story Clears",
        "value": f"{clear_done}/{clear_total}",
        "percent": _calculate_ratio(clear_done, clear_total),
    }


def _build_superior_treasure_card(story_stats: dict[str, object]) -> CardRow:
    """Build superior treasure completion card row."""
    superior_done = safe_int(story_stats.get("superior_done"), 0)
    treasure_total = safe_int(story_stats.get("treasure_total"), 0)
    return {
        "id": "superior_treasures",
        "label": "Superior Treasures",
        "value": f"{superior_done}/{treasure_total}",
        "percent": _calculate_ratio(superior_done, treasure_total),
    }


def _build_medals_card(trophy_owned: int) -> CardRow:
    """Build medal count card row."""
    return {
        "id": "medals",
        "label": "Meow Medals",
        "value": trophy_owned,
        "subtitle": "Affects lineup unlock thresholds",
    }


def _build_enemy_guide_card(enemy_guide: tuple[int, int]) -> CardRow:
    """Build enemy guide completion card row."""
    unlocked, total = enemy_guide
    return {
        "id": "enemy_guide",
        "label": "Enemy Guide",
        "value": f"{unlocked}/{total}",
        "percent": _calculate_ratio(unlocked, total),
    }


def _build_cat_guide_card(cat_guide: tuple[int, int]) -> CardRow:
    """Build cat guide completion card row."""
    claimed, total = cat_guide
    return {
        "id": "cat_guide",
        "label": "Cat Guide Claimed",
        "value": f"{claimed}/{total}",
        "percent": _calculate_ratio(claimed, total),
    }


def _build_dashboard_cards(
    story_stats: dict[str, object],
    lineups: tuple[int, int],
    enemy_guide: tuple[int, int],
    cat_guide: tuple[int, int],
    user_rank: int,
    trophy_owned: int,
) -> list[CardRow]:
    """Build card rows for the dashboard response."""
    return [
        _build_user_rank_card(user_rank),
        _build_lineups_card(lineups),
        _build_story_clear_card(story_stats),
        _build_superior_treasure_card(story_stats),
        _build_medals_card(trophy_owned),
        _build_enemy_guide_card(enemy_guide),
        _build_cat_guide_card(cat_guide),
    ]


def dashboard_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build dashboard payload for the web UI."""
    story_stats = story_progress_stats(save_file)
    lineups = lineup_stats(save_file)
    enemy_guide = enemy_guide_stats(save_file)
    cat_guide = cat_guide_stats(save_file)
    user_rank = safe_int(save_file.calculate_user_rank())
    trophy_owned = len(getattr(save_file.medals, "medal_data_1", ()) or ())
    cards = _build_dashboard_cards(
        story_stats,
        lineups,
        enemy_guide,
        cat_guide,
        user_rank,
        trophy_owned,
    )
    return {
        "ok": True,
        "cards": cards,
        "story_sagas": story_stats["sagas"],
        "story_chapters": story_stats["chapters"],
    }


def playtime_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build playtime payload for the web UI."""
    raw_play_time = safe_int(getattr(save_file.officer_pass, "play_time", 0), 0)
    play_time = core.PlayTime(raw_play_time)
    return {
        "ok": True,
        "hours": max(0, safe_int(play_time.hours, 0)),
        "minutes": max(0, safe_int(play_time.just_minutes, 0)),
        "seconds": max(0, safe_int(play_time.just_seconds, 0)),
        "frames": max(0, safe_int(play_time.frames, 0)),
    }
