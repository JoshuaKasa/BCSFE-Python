from __future__ import annotations

from ..core import core
from ..core import safe_int
from .cats_service import get_cat_total_forms
from .story_stats_service import cat_guide_stats
from .story_stats_service import enemy_guide_stats
from .story_stats_service import story_progress_stats

CheckRecord = dict[str, object]


def _append_check(
    checks: list[CheckRecord],
    severity: str,
    domain: str,
    message: str,
) -> None:
    """Add a normalized validation check entry."""
    checks.append(
        {
            "severity": severity,
            "domain": domain,
            "message": message,
        }
    )


def _collect_resource_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> int:
    """Collect hard-cap checks for key resources."""
    max_manager = core.core_data.max_value_manager
    resource_caps: tuple[tuple[str, core.MaxValueType], ...] = (
        ("catfood", core.MaxValueType.CATFOOD),
        ("xp", core.MaxValueType.XP),
        ("np", core.MaxValueType.NP),
        ("normal_tickets", core.MaxValueType.NORMAL_TICKETS),
        ("rare_tickets", core.MaxValueType.RARE_TICKETS),
        ("platinum_tickets", core.MaxValueType.PLATINUM_TICKETS),
        ("legend_tickets", core.MaxValueType.LEGEND_TICKETS),
        ("leadership", core.MaxValueType.LEADERSHIP),
    )
    near_cap_count = 0
    for field_name, cap_key in resource_caps:
        value = safe_int(getattr(save_file, field_name, 0))
        cap_value = max(0, safe_int(max_manager.get(cap_key)))
        if value < 0 or value > cap_value:
            _append_check(
                checks,
                "warning",
                "resources",
                f"{field_name} is out of range ({value}, cap {cap_value}).",
            )
        if cap_value > 0 and value >= int(cap_value * 0.95):
            near_cap_count += 1
            _append_check(
                checks,
                "risk",
                "ban_risk",
                f"{field_name} is near hard cap ({value}/{cap_value}).",
            )
        if cap_value > 0 and value >= cap_value:
            _append_check(
                checks,
                "risk",
                "ban_risk",
                f"{field_name} is exactly at hard cap ({value}/{cap_value}).",
            )
    return near_cap_count


def _collect_cat_form_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect checks for invalid cat forms and fourth-form flags."""
    invalid_form_count = 0
    invalid_fourth_form_count = 0
    for cat in save_file.cats.cats:
        total_forms = get_cat_total_forms(save_file, cat)
        if safe_int(cat.current_form) >= total_forms:
            invalid_form_count += 1
        if total_forms < 4 and safe_int(cat.fourth_form) > 0:
            invalid_fourth_form_count += 1
    if invalid_form_count > 0:
        _append_check(
            checks,
            "warning",
            "cats",
            (
                f"{invalid_form_count} cats have a current form index above "
                "their form count."
            ),
        )
    if invalid_fourth_form_count > 0:
        _append_check(
            checks,
            "warning",
            "cats",
            (
                f"{invalid_fourth_form_count} cats have 4th-form flags but "
                "no 4-form support."
            ),
        )


def _collect_locked_cat_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect checks for locked cats with progression edits."""
    locked_modified_count = 0
    for cat in save_file.cats.cats:
        if bool(cat.unlocked):
            continue
        has_progress = (
            safe_int(cat.upgrade.base) > 0
            or safe_int(cat.upgrade.plus) > 0
            or safe_int(cat.current_form) > 0
            or safe_int(cat.unlocked_forms) > 0
            or safe_int(cat.fourth_form) > 0
        )
        if has_progress:
            locked_modified_count += 1
    if locked_modified_count > 0:
        _append_check(
            checks,
            "warning",
            "cats",
            f"{locked_modified_count} locked cats have modified levels/forms.",
        )


def _collect_cat_level_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect checks for base/plus level overflow against legal limits."""
    base_overflow_count = 0
    plus_overflow_count = 0
    for cat in save_file.cats.cats:
        if not bool(cat.unlocked):
            continue
        try:
            power_helper = core.PowerUpHelper(cat, save_file)
            max_base = max(0, safe_int(power_helper.get_max_possible_base()))
            max_plus = max(0, safe_int(power_helper.get_max_possible_plus()))
        except Exception:
            continue
        if safe_int(cat.upgrade.base) > max_base:
            base_overflow_count += 1
        if safe_int(cat.upgrade.plus) > max_plus:
            plus_overflow_count += 1
    if base_overflow_count > 0:
        _append_check(
            checks,
            "risk",
            "ban_risk",
            f"{base_overflow_count} cats exceed maximum base level limits.",
        )
    if plus_overflow_count > 0:
        _append_check(
            checks,
            "risk",
            "ban_risk",
            f"{plus_overflow_count} cats exceed maximum plus level limits.",
        )


def _collect_talent_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect checks for talent level overflow."""
    talent_overflow_count = 0
    try:
        talent_data = save_file.cats.read_talent_data(save_file)
        if talent_data is None:
            return
        for cat in save_file.cats.cats:
            talents = tuple(getattr(cat, "talents", ()) or ())
            for talent in talents:
                skill_id = safe_int(getattr(talent, "id", -1))
                skill = talent_data.get_skill_from_cat(cat.id, skill_id)
                if skill is None:
                    continue
                max_level = max(1, safe_int(getattr(skill, "max_lv", 1), 1))
                current_level = safe_int(getattr(talent, "level", 0))
                if current_level > max_level:
                    talent_overflow_count += 1
    except Exception:
        return
    if talent_overflow_count > 0:
        _append_check(
            checks,
            "risk",
            "ban_risk",
            f"{talent_overflow_count} talents exceed their legal max level.",
        )


def _collect_story_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect checks for impossible story treasure states."""
    over_treasure_count = 0
    treasure_without_clear_count = 0
    for chapter in getattr(save_file.story, "chapters", ()) or ():
        stages = tuple(getattr(chapter, "stages", ()) or ())[:49]
        for index, stage in enumerate(stages):
            treasure = safe_int(getattr(stage, "treasure", 0))
            clear_times = safe_int(getattr(stage, "clear_times", 0))
            if treasure > 3:
                over_treasure_count += 1
            if index < 48 and treasure > 0 and clear_times <= 0:
                treasure_without_clear_count += 1
    if over_treasure_count > 0:
        _append_check(
            checks,
            "warning",
            "progress",
            (
                f"{over_treasure_count} story treasure entries exceed "
                "Superior tier (3)."
            ),
        )
    if treasure_without_clear_count > 0:
        _append_check(
            checks,
            "warning",
            "progress",
            (
                f"{treasure_without_clear_count} stages have treasures "
                "without stage clear progress."
            ),
        )


def _collect_progress_alignment_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect progression consistency checks between guides and story."""
    progress_stats = story_progress_stats(save_file)
    clear_done = safe_int(progress_stats.get("clear_done", 0))

    enemy_unlocked, enemy_total = enemy_guide_stats(save_file)
    if enemy_total > 0 and enemy_unlocked >= int(enemy_total * 0.95):
        if clear_done < 40:
            _append_check(
                checks,
                "risk",
                "ban_risk",
                (
                    "Enemy guide is nearly fully unlocked while story "
                    "progress is very low."
                ),
            )

    cat_claimed, cat_total = cat_guide_stats(save_file)
    if cat_total > 0 and cat_claimed >= int(cat_total * 0.9):
        if clear_done < 40:
            _append_check(
                checks,
                "risk",
                "ban_risk",
                (
                    "Cat guide is nearly fully claimed while story "
                    "progress is very low."
                ),
            )

    try:
        trophy_owned = len(getattr(save_file.medals, "medal_data_1", ()) or ())
    except Exception:
        trophy_owned = 0
    if trophy_owned >= 250 and clear_done < 60:
        _append_check(
            checks,
            "risk",
            "ban_risk",
            "Meow medal count is very high compared to story progression.",
        )


def _collect_base_upgrade_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect checks for suspiciously maxed base upgrades."""
    progress_stats = story_progress_stats(save_file)
    clear_done = safe_int(progress_stats.get("clear_done", 0))
    try:
        ability_data = core.core_data.get_ability_data(save_file)
        skills = tuple(save_file.special_skills.get_valid_skills() or ())
    except Exception:
        return
    if ability_data is None or not skills:
        return

    maxed_count = 0
    for index, skill in enumerate(skills):
        ability = ability_data.get_ability_data_item(index)
        if ability is None:
            continue
        max_base = max(0, safe_int(getattr(ability, "max_base_level", 1)) - 1)
        max_plus = max(0, safe_int(getattr(ability, "max_plus_level", 0)))
        current_base = safe_int(skill.upgrade.base)
        current_plus = safe_int(skill.upgrade.plus)
        if current_base >= max_base and current_plus >= max_plus:
            maxed_count += 1

    if maxed_count >= int(len(skills) * 0.9) and clear_done < 30:
        _append_check(
            checks,
            "risk",
            "ban_risk",
            "Base upgrades are almost fully maxed while story progress is low.",
        )


def _collect_gamatoto_checks(
    save_file: core.SaveFile,
    checks: list[CheckRecord],
) -> None:
    """Collect checks for Gamatoto helper and level limits."""
    try:
        levels = core.core_data.get_gamatoto_levels(save_file)
        if levels is None:
            return
        max_helpers = safe_int(levels.get_total_helpers(), 0)
        max_level = safe_int(levels.get_max_level(), 0)
        helper_count = len(
            getattr(save_file.gamatoto.helpers, "helpers", ()) or ()
        )
        current_level_obj = levels.get_level_from_xp(
            safe_int(save_file.gamatoto.xp)
        )
        current_level = safe_int(getattr(current_level_obj, "level", 0), 0)
    except Exception:
        return

    if max_helpers > 0 and helper_count > max_helpers:
        _append_check(
            checks,
            "warning",
            "gamatoto",
            (
                f"Gamatoto helper slots exceed limit ({helper_count}/"
                f"{max_helpers})."
            ),
        )
    if max_level > 0 and current_level > max_level:
        _append_check(
            checks,
            "risk",
            "ban_risk",
            f"Gamatoto level exceeds max ({current_level}/{max_level}).",
        )


def validation_payload(save_file: core.SaveFile) -> dict[str, object]:
    """Build integrity and ban-risk checks for the loaded save file."""
    checks: list[CheckRecord] = []
    near_cap_count = _collect_resource_checks(save_file, checks)
    user_rank = safe_int(save_file.calculate_user_rank())
    if near_cap_count >= 4 and user_rank < 1500:
        _append_check(
            checks,
            "risk",
            "ban_risk",
            "Many core resources are near cap while User Rank is still low.",
        )

    _collect_cat_form_checks(save_file, checks)
    _collect_locked_cat_checks(save_file, checks)
    _collect_cat_level_checks(save_file, checks)
    _collect_talent_checks(save_file, checks)
    _collect_story_checks(save_file, checks)
    _collect_progress_alignment_checks(save_file, checks)
    _collect_base_upgrade_checks(save_file, checks)
    _collect_gamatoto_checks(save_file, checks)

    if not checks:
        _append_check(checks, "ok", "integrity", "No issues detected.")

    return {"ok": True, "checks": checks}
