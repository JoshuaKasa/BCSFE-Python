from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bcsfe import core  # noqa: E402
from bcsfe.cli.edits import max_all  # noqa: E402
from bcsfe.cli.save_management import SaveManagement  # noqa: E402
from bcsfe.core.game.gamoto.gamatoto import Helper, Helpers  # noqa: E402
from bcsfe.core.game.gamoto import ototo as ototo_data  # noqa: E402


Operation = Callable[[core.SaveFile], None]


def top_up_catfood(save_file: core.SaveFile, target: int = 1500) -> None:
    """Give a conservative catfood amount for realistic progression presets."""
    if save_file.catfood < target:
        save_file.catfood = target


def safe_max_catamins(save_file: core.SaveFile) -> None:
    max_value = core.core_data.max_value_manager.get(core.MaxValueType.CATAMINS)
    for idx in range(min(len(save_file.catamins), len(save_file.catseyes))):
        save_file.catamins[idx] = max_value


def safe_max_catseyes(save_file: core.SaveFile) -> None:
    max_value = core.core_data.max_value_manager.get(core.MaxValueType.CATSEYES)
    for idx in range(len(save_file.catseyes)):
        save_file.catseyes[idx] = max_value


def safe_max_treasure_chests(save_file: core.SaveFile) -> None:
    max_value = core.core_data.max_value_manager.get(core.MaxValueType.TREASURE_CHESTS)
    for idx in range(len(save_file.treasure_chests)):
        save_file.treasure_chests[idx] = max_value


def safe_max_labyrinth_medals(save_file: core.SaveFile) -> None:
    max_value = core.core_data.max_value_manager.get(core.MaxValueType.LABYRINTH_MEDALS)
    for idx in range(len(save_file.labyrinth_medals)):
        save_file.labyrinth_medals[idx] = max_value


def unlock_all_cats(save_file: core.SaveFile) -> None:
    for cat in save_file.cats.cats:
        cat.unlock(save_file)


def clear_story_and_treasures(save_file: core.SaveFile) -> None:
    clear_amount = max(1, core.core_data.max_value_manager.get(core.MaxValueType.STAGE_CLEAR_COUNT))
    treasure_value = core.core_data.max_value_manager.get(core.MaxValueType.TREASURE_LEVEL)
    timed_score = core.core_data.max_value_manager.get(core.MaxValueType.ITF_TIMED_SCORE)

    for chapter in save_file.story.chapters:
        chapter.progress = max(chapter.progress, 48)
        for idx, stage in enumerate(chapter.stages):
            if idx < 48:
                stage.clear_times = clear_amount
            if idx < 49:
                stage.treasure = treasure_value
            stage.itf_timed_score = timed_score


def clear_story_only(save_file: core.SaveFile) -> None:
    clear_amount = max(
        1, core.core_data.max_value_manager.get(core.MaxValueType.STAGE_CLEAR_COUNT)
    )
    for chapter in save_file.story.chapters:
        chapter.progress = max(chapter.progress, 48)
        for idx, stage in enumerate(chapter.stages):
            if idx < 48:
                stage.clear_times = clear_amount


def clear_story_superior_treasures(save_file: core.SaveFile) -> None:
    """Human-achievable story cap: all clear + all Superior treasures.

    Superior is the top in-game treasure tier (Inferior=1, Normal=2, Superior=3).
    """
    clear_amount = max(
        1, core.core_data.max_value_manager.get(core.MaxValueType.STAGE_CLEAR_COUNT)
    )
    superior_treasure_value = 3
    for chapter in save_file.story.chapters:
        chapter.progress = max(chapter.progress, 48)
        for idx, stage in enumerate(chapter.stages):
            if idx < 48:
                stage.clear_times = clear_amount
            if idx < 49:
                stage.treasure = superior_treasure_value


def max_cat_talents(save_file: core.SaveFile) -> None:
    talent_data = save_file.cats.read_talent_data(save_file)
    if talent_data is None:
        return
    for cat in save_file.cats.cats:
        if cat.talents is None:
            continue
        data = talent_data.get_cat_talents(cat)
        if data is None:
            continue
        _talent_names, max_levels, _current_levels, ids = data
        for i, talent_id in enumerate(ids):
            talent = cat.get_talent_from_id(talent_id)
            if talent is None:
                continue
            talent.level = max_levels[i]


def max_special_skills(save_file: core.SaveFile) -> None:
    """Max support/base upgrades (worker, wallet, research, cannon stats, etc.)."""
    ability_data = core.core_data.get_ability_data(save_file)
    if ability_data.ability_data is None:
        return

    for skill_id in range(len(save_file.special_skills.get_valid_skills())):
        ability = ability_data.get_ability_data_item(skill_id)
        if ability is None:
            continue

        max_base = max(0, int(ability.max_base_level) - 1)
        max_plus = max(0, int(ability.max_plus_level))
        save_file.special_skills.set_upgrade(
            skill_id,
            core.Upgrade(max_base, max_plus),
            max_base=max_base,
            max_plus=max_plus,
        )


def _clear_chapters_like(chapters_obj: object) -> None:
    chapters = getattr(chapters_obj, "chapters", None)
    if not isinstance(chapters, list):
        return

    for chapter_stars in chapters:
        stars = getattr(chapter_stars, "chapters", None)
        if not isinstance(stars, list):
            continue

        for chapter in stars:
            stages = getattr(chapter, "stages", None)
            if not isinstance(stages, list):
                continue

            for stage in stages:
                if hasattr(stage, "clear_times"):
                    stage.clear_times = max(1, int(getattr(stage, "clear_times", 0) or 0))
                if hasattr(stage, "tries"):
                    stage.tries = max(1, int(getattr(stage, "tries", 0) or 0))

            if hasattr(chapter, "clear_progress"):
                chapter.clear_progress = len(stages)
            if hasattr(chapter, "chapter_unlock_state"):
                chapter.chapter_unlock_state = 3 if stages else 0
            if hasattr(chapter, "unlock_state"):
                chapter.unlock_state = 3 if stages else 0
            # Reset chapter selection pointers to a safe visible index. For some map types
            # (notably Zero Legends), forcing these to the last raw stage can point at
            # hidden/internal entries and crash when loading a stage.
            if hasattr(chapter, "selected_stage"):
                chapter.selected_stage = 0 if stages else 0
            if hasattr(chapter, "current_stage"):
                chapter.current_stage = 0 if stages else 0


def clear_all_maps(save_file: core.SaveFile) -> None:
    if hasattr(save_file, "event_stages"):
        try:
            event_chapters = save_file.event_stages.chapters
            for map_type in range(len(event_chapters)):
                save_file.event_stages.clear_group(map_type)
        except Exception:
            pass

    if hasattr(save_file, "outbreaks"):
        for chapter in save_file.outbreaks.chapters.values():
            for outbreak in chapter.outbreaks.values():
                outbreak.cleared = True

    # Chapters-like structures
    if hasattr(save_file, "gauntlets"):
        _clear_chapters_like(save_file.gauntlets)
    if hasattr(save_file, "collab_gauntlets"):
        _clear_chapters_like(save_file.collab_gauntlets)
    if hasattr(save_file, "behemoth_culling"):
        _clear_chapters_like(save_file.behemoth_culling)
    if hasattr(save_file, "enigma_clears"):
        _clear_chapters_like(save_file.enigma_clears)
    if hasattr(save_file, "uncanny"):
        _clear_chapters_like(save_file.uncanny.chapters)
    if hasattr(save_file, "catamin_stages"):
        _clear_chapters_like(save_file.catamin_stages.chapters)
    if hasattr(save_file, "tower"):
        _clear_chapters_like(save_file.tower.chapters)
        if hasattr(save_file.tower, "item_obtain_states"):
            for i, row in enumerate(save_file.tower.item_obtain_states):
                save_file.tower.item_obtain_states[i] = [True] * len(row)
    if hasattr(save_file, "legend_quest"):
        _clear_chapters_like(save_file.legend_quest)
    if hasattr(save_file, "zero_legends"):
        _clear_chapters_like(save_file.zero_legends)
    if hasattr(save_file, "dojo_chapters"):
        _clear_chapters_like(save_file.dojo_chapters)

    if hasattr(save_file, "aku"):
        for chapter_stars in save_file.aku.chapters:
            for chapter in chapter_stars.chapters:
                for stage in chapter.stages:
                    stage.clear_times = max(1, int(getattr(stage, "clear_times", 0) or 0))
                chapter.current_stage = 0 if chapter.stages else 0


def max_gamatoto(save_file: core.SaveFile) -> None:
    gamatoto_levels = core.core_data.get_gamatoto_levels(save_file)
    max_level = gamatoto_levels.get_max_level()
    if max_level is not None:
        xp = gamatoto_levels.get_xp_from_level(max_level)
        if xp is None:
            level_data = gamatoto_levels.get_level(max_level)
            if level_data is not None and level_data.xp_needed != -1:
                xp = level_data.xp_needed
            else:
                xp = 0
        save_file.gamatoto.xp = max(0, int(xp))

    total_helpers = gamatoto_levels.get_total_helpers()
    members_name = core.core_data.get_gamatoto_members_name(save_file)
    members = members_name.members or []
    if total_helpers is not None and members:
        members_sorted = sorted(
            members,
            key=lambda m: (m.rarity, m.bonus, m.member_id),
            reverse=True,
        )
        helper_ids = [member.member_id for member in members_sorted[: total_helpers]]
        save_file.gamatoto.helpers = Helpers([Helper(helper_id) for helper_id in helper_ids])

    save_file.gamatoto.remaining_seconds = 0.0
    save_file.gamatoto.return_flag = True
    save_file.ototo.engineers = core.Ototo.get_max_engineers(save_file)


def max_catfruit(save_file: core.SaveFile) -> None:
    if save_file.game_version < 110400:
        max_value = core.core_data.max_value_manager.get_old(core.MaxValueType.CATFRUIT)
    else:
        max_value = core.core_data.max_value_manager.get_new(core.MaxValueType.CATFRUIT)
    for idx in range(len(save_file.catfruit)):
        save_file.catfruit[idx] = max_value


def max_base_materials(save_file: core.SaveFile) -> None:
    if not hasattr(save_file, "ototo") or not hasattr(save_file.ototo, "base_materials"):
        return
    max_value = core.core_data.max_value_manager.get(core.MaxValueType.BASE_MATERIALS)
    for material in save_file.ototo.base_materials.materials:
        material.amount = max_value


def set_gold_tickets_200(save_file: core.SaveFile) -> None:
    """Set Rare (gold) tickets to a moderate high value."""
    save_file.rare_tickets = 200


def max_cat_base_cannons(save_file: core.SaveFile) -> None:
    """Max cannon development + part levels using in-game recipe limits."""
    if getattr(save_file.ototo, "cannons", None) is None:
        save_file.ototo.cannons = ototo_data.Cannons.init(save_file.game_version)
    cannons = save_file.ototo.cannons
    if cannons is None:
        return

    recipe = ototo_data.CastleRecipeUnlock(save_file)
    recipe_rows = list(getattr(recipe, "level_part_recipe_unlocks", []) or [])
    cannon_ids = sorted(
        {
            int(getattr(row, "cannon_id", 0))
            for row in recipe_rows
            if int(getattr(row, "cannon_id", 0)) >= 0
        }
    )

    for cannon_id in cannon_ids:
        cannon = cannons.cannons.get(cannon_id)
        if cannon is None:
            cannon = ototo_data.Cannon.init()
            cannons.cannons[cannon_id] = cannon
        cannon.development = 3
        while len(cannon.levels) < 3:
            cannon.levels.append(0)
        for part_id in range(3):
            max_level = recipe.get_max_level(cannon_id, part_id)
            if max_level is None:
                max_level = recipe.get_max_part_level(part_id)
            cannon.levels[part_id] = max(0, int(max_level or 0))

    if not cannons.selected_parts:
        cannons.selected_parts = [[0, 0, 0]]


def legit_max_cats(save_file: core.SaveFile) -> None:
    all_cats = list(save_file.cats.cats)
    for cat in all_cats:
        cat.unlock(save_file)
        cat.catguide_collected = True

        # Use in-game unit limits from game data (no absurd +999 values).
        power_up = core.PowerUpHelper(cat, save_file)
        power_up.max_upgrade()
        cat.upgrade.plus = max(cat.upgrade.plus, power_up.get_max_possible_plus())

    save_file.cats.true_form_cats(save_file, all_cats, force=False, set_current_forms=True)
    save_file.cats.fourth_form_cats(save_file, all_cats, force=False, set_current_forms=True)
    max_cat_talents(save_file)


def humanize_uber_legend_plus(save_file: core.SaveFile) -> None:
    """Human-max tweak: keep max base, set Uber/Legend plus to weighted 1..20."""
    unit_buy = save_file.cats.read_unitbuy(save_file)
    if unit_buy is None:
        return

    # Battle Cats rarity ids: 4=Uber Rare, 5=Legend Rare.
    target_rarities = {4, 5}

    for cat in save_file.cats.cats:
        if unit_buy.get_cat_rarity(cat.id) not in target_rarities:
            continue

        power_up = core.PowerUpHelper(cat, save_file)
        power_up.max_upgrade()

        # Bias toward smaller values while staying in the requested 1..20 range.
        plus_roll = 1 + int((random.random() ** 2.2) * 19)
        max_plus = max(0, int(power_up.get_max_possible_plus()))
        cat.upgrade.plus = min(plus_roll, max_plus)


OPERATIONS: dict[str, tuple[str, Operation]] = {
    "catfood_topup": ("Catfood top-up (1500)", top_up_catfood),
    "catfood": ("Catfood", max_all.max_catfood),
    "xp": ("XP", max_all.max_xp),
    "normal_tickets": ("Normal tickets", max_all.max_normal_tickets),
    "rare_tickets": ("Rare tickets", max_all.max_rare_tickets),
    "platinum_tickets": ("Platinum tickets", max_all.max_plat_tickets),
    "legend_tickets": ("Legend tickets", max_all.max_legend_tickets),
    "platinum_shards": ("Platinum shards", max_all.max_plat_shards),
    "np": ("NP", max_all.max_np),
    "leadership": ("Leadership", max_all.max_leadership),
    "battle_items": ("Battle items", max_all.max_battle_items),
    "catseyes": ("Catseyes", safe_max_catseyes),
    "catamins": ("Catamins", safe_max_catamins),
    "labyrinth_medals": ("Labyrinth medals", safe_max_labyrinth_medals),
    "hundred_million_ticket": ("100 million tickets", max_all.max_100_million_ticket),
    "treasure_chests": ("Treasure chests", safe_max_treasure_chests),
    "catfruit": ("Catfruit / evolution fruits", max_catfruit),
    "base_materials": ("Base materials", max_base_materials),
    "gold_tickets_200": ("Set gold (rare) tickets to 200", set_gold_tickets_200),
    "special_skills_max": ("Max support/base upgrades", max_special_skills),
    "cat_base_cannons_max": ("Max cat base cannons + parts", max_cat_base_cannons),
    "legit_max_cats": ("Legit-max all cats", legit_max_cats),
    "humanize_uber_legend_plus": (
        "Human max: Uber/Legend + levels randomized (1..20, low-biased)",
        humanize_uber_legend_plus,
    ),
    "unlock_all_cats": ("Unlock all cats", unlock_all_cats),
    "clear_story_only": ("Clear story (keep current treasures)", clear_story_only),
    "clear_story_superior_treasures": (
        "Clear story + Superior treasures (human max)",
        clear_story_superior_treasures,
    ),
    "clear_story_treasures": ("Clear story + max treasures", clear_story_and_treasures),
    "max_gamatoto": ("Max Gamatoto (xp/helpers/return/engineers)", max_gamatoto),
    "clear_all_maps": ("Clear all map categories", clear_all_maps),
}

PRESETS: dict[str, list[str]] = {
    # Human-max progression preset.
    "10": [
        "catfood_topup",
        "xp",
        "normal_tickets",
        "gold_tickets_200",
        "np",
        "leadership",
        "battle_items",
        "catfruit",
        "base_materials",
        "catseyes",
        "catamins",
        "labyrinth_medals",
        "treasure_chests",
        "special_skills_max",
        "cat_base_cannons_max",
        "legit_max_cats",
        "humanize_uber_legend_plus",
        "clear_story_superior_treasures",
        "max_gamatoto",
        "clear_all_maps",
    ],
    # Strong but keeps current story treasures.
    "9": [
        "catfood_topup",
        "xp",
        "normal_tickets",
        "gold_tickets_200",
        "np",
        "leadership",
        "battle_items",
        "catseyes",
        "catamins",
        "catfruit",
        "base_materials",
        "labyrinth_medals",
        "treasure_chests",
        "special_skills_max",
        "cat_base_cannons_max",
        "legit_max_cats",
        "max_gamatoto",
        "clear_story_only",
        "clear_all_maps",
    ],
    # Simpler non-risky max items/resources.
    "1": [
        "xp",
        "normal_tickets",
        "np",
        "leadership",
        "battle_items",
        "catseyes",
        "catamins",
        "labyrinth_medals",
        "treasure_chests",
    ],
    # Starter boost.
    "5": [
        "catfood",
        "xp",
        "np",
        "leadership",
        "battle_items",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple max-account preset runner for BCSFE saves."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Path to input SAVE_DATA file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Path to output file (default: <input>.maxed)",
    )
    return parser.parse_args()


def prompt_preset() -> list[str]:
    print()
    print("Choose account preset:")
    print("10) Human-max progression (recommended)")
    print("9) Full legit max progression (keeps current story treasures)")
    print("1) Safer max resources")
    print("5) Starter boost")
    print("6) Custom selection")
    choice = input("> ").strip()
    if choice in PRESETS:
        return PRESETS[choice]
    if choice == "6":
        return prompt_custom()
    raise ValueError("Invalid preset option.")


def prompt_custom() -> list[str]:
    print()
    print("Custom options (comma-separated numbers):")
    ordered_keys = list(OPERATIONS.keys())
    for idx, key in enumerate(ordered_keys, start=1):
        print(f"{idx}) {OPERATIONS[key][0]}")
    raw = input("> ").strip().lower()
    if raw == "all":
        return ordered_keys

    selected: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit():
            raise ValueError(f"Invalid token: {token}")
        idx = int(token)
        if idx < 1 or idx > len(ordered_keys):
            raise ValueError(f"Index out of range: {idx}")
        key = ordered_keys[idx - 1]
        if key not in selected:
            selected.append(key)
    if not selected:
        raise ValueError("No custom options selected.")
    return selected


def load_save(save_path: Path) -> core.SaveFile:
    result = SaveManagement.load_save_file_path(core.Path(str(save_path)), None, False)
    if result is None:
        raise RuntimeError("Failed to load save. Check path and file validity.")
    save_file, _backup_path = result
    return save_file


def apply_operations(save_file: core.SaveFile, operation_keys: list[str]) -> None:
    for key in operation_keys:
        name, op = OPERATIONS[key]
        try:
            op(save_file)
        except Exception as error:
            raise RuntimeError(f"Operation failed: {name} ({key}) -> {error}") from error


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.name}.maxed")


def resolve_input_path(raw_path: Path) -> Path:
    if raw_path.is_file():
        return raw_path
    if raw_path.is_dir():
        default_file = raw_path / "SAVE_DATA"
        if default_file.is_file():
            return default_file
        raise FileNotFoundError(
            f"Folder given but SAVE_DATA not found inside: {raw_path}"
        )
    raise FileNotFoundError(f"Input path not found: {raw_path}")


def main() -> int:
    args = parse_args()
    core.core_data.init_data()

    raw_input_path = (
        Path(args.input) if args.input else Path(input("Input save path: ").strip())
    )
    try:
        input_path = resolve_input_path(raw_input_path)
    except FileNotFoundError as error:
        print(error)
        return 1

    try:
        selected = prompt_preset()
    except ValueError as error:
        print(error)
        return 1

    output_path = Path(args.output) if args.output else default_output_path(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        save_file = load_save(input_path)
        apply_operations(save_file, selected)
        save_file.to_file(core.Path(str(output_path)))
    except Exception as error:
        print(f"Failed: {error}")
        return 1

    print()
    print("Done.")
    print(f"Applied {len(selected)} max options.")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





