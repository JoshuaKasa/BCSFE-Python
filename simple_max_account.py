from __future__ import annotations

import argparse
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


Operation = Callable[[core.SaveFile], None]


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
                chapter.chapter_unlock_state = max(
                    1, int(getattr(chapter, "chapter_unlock_state", 0) or 0)
                )
            if hasattr(chapter, "unlock_state"):
                chapter.unlock_state = max(1, int(getattr(chapter, "unlock_state", 0) or 0))
            if hasattr(chapter, "selected_stage"):
                chapter.selected_stage = max(len(stages) - 1, 0)
            if hasattr(chapter, "current_stage"):
                chapter.current_stage = max(len(stages) - 1, 0)


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
                chapter.current_stage = max(len(chapter.stages) - 1, 0)


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


OPERATIONS: dict[str, tuple[str, Operation]] = {
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
    "legit_max_cats": ("Legit-max all cats", legit_max_cats),
    "unlock_all_cats": ("Unlock all cats", unlock_all_cats),
    "clear_story_treasures": ("Clear story + max treasures", clear_story_and_treasures),
    "clear_all_maps": ("Clear all map categories", clear_all_maps),
}

PRESETS: dict[str, list[str]] = {
    # Recommended: avoid explicitly bannable currencies.
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
    "2": [
        "xp",
        "np",
        "leadership",
        "battle_items",
        "catseyes",
        "catamins",
        "labyrinth_medals",
        "treasure_chests",
        "normal_tickets",
        "hundred_million_ticket",
        "platinum_shards",
    ],
    # Risky: includes currencies explicitly warned as bannable in the repo.
    "3": list(OPERATIONS.keys()),
    "4": [
        "catfood",
        "rare_tickets",
        "platinum_tickets",
        "legend_tickets",
    ],
    "5": ["catfood", "xp", "np", "leadership", "battle_items"],
    "7": list(OPERATIONS.keys()),
    "8": [
        "xp",
        "np",
        "leadership",
        "battle_items",
        "normal_tickets",
        "catseyes",
        "catamins",
        "catfruit",
        "base_materials",
        "labyrinth_medals",
        "treasure_chests",
        "legit_max_cats",
        "clear_story_treasures",
        "clear_all_maps",
    ],
    # Alias for clarity: full progression-focused preset without risky currency edits.
    "9": [
        "xp",
        "np",
        "leadership",
        "battle_items",
        "normal_tickets",
        "catseyes",
        "catamins",
        "catfruit",
        "base_materials",
        "labyrinth_medals",
        "treasure_chests",
        "legit_max_cats",
        "clear_story_treasures",
        "clear_all_maps",
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
    print("1) Safer max (recommended)")
    print("2) Broad max (still avoids direct rare/plat/legend ticket edits)")
    print("3) Full hard-cap max (risky)")
    print("4) Risky currencies only (catfood + rare/plat/legend)")
    print("5) Starter boost")
    print("6) Custom selection")
    print("7) Full account (unlock cats + clear maps + all resources) [very risky]")
    print("8) Legit-max progression (cats/forms/materials/maps, non-absurd levels)")
    print("9) Full legit max progression (alias of 8)")
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
