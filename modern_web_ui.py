from __future__ import annotations

import json
import re
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from tkinter import filedialog
from flask import Flask, jsonify, request, send_from_directory


REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bcsfe import core  # noqa: E402
from bcsfe.cli.save_management import SaveManagement  # noqa: E402
from simple_max_account import OPERATIONS, PRESETS, resolve_input_path  # noqa: E402


def clean_name(text: str) -> str:
    text = text.replace("_", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text.title() if text.islower() else text


def cat_number(cat: core.Cat) -> str:
    form = max(1, min(cat.current_form + 1, 4))
    return f"{cat.id + 1:03d}-{form}"


@dataclass
class AppState:
    save_file: core.SaveFile | None = None
    loaded_path: Path | None = None
    name_cache: dict[int, str] | None = None
    mygamatoto_index: dict[str, str] | None = None

    def __post_init__(self):
        if self.name_cache is None:
            self.name_cache = {}
        if self.mygamatoto_index is None:
            self.mygamatoto_index = {}


app = Flask(__name__, static_folder="webui", static_url_path="/webui")
state = AppState()

CACHE_DIR = REPO_ROOT / ".cache" / "mygamatoto"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = CACHE_DIR / "allcats_index.json"

# Required for localized save-loading paths and messages used by SaveManagement.
core.core_data.init_data()


def ensure_loaded() -> core.SaveFile:
    if state.save_file is None:
        raise RuntimeError("No save loaded.")
    return state.save_file


def load_mygamatoto_index() -> None:
    if not INDEX_PATH.exists():
        return
    try:
        obj = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            state.mygamatoto_index = {str(k): str(v) for k, v in obj.items()}
    except Exception:
        state.mygamatoto_index = {}


def sync_mygamatoto_index() -> int:
    resp = requests.get("https://onestoppress.com/api/allcats", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    sample = data.get("sampledata", [])
    index: dict[str, str] = {}
    for row in sample:
        number = str(row.get("number", "")).strip()
        name = str(row.get("name", "")).strip()
        if number:
            index[number] = clean_name(name)
    if not index:
        raise RuntimeError("MyGamatoto response had no cat data.")
    state.mygamatoto_index = index
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    state.name_cache = {}
    return len(index)


def get_cat_name(cat: core.Cat) -> str:
    if state.name_cache is None:
        state.name_cache = {}
    cached = state.name_cache.get(cat.id)
    if cached is not None:
        return cached

    number = cat_number(cat)
    if state.mygamatoto_index:
        mg_name = state.mygamatoto_index.get(number)
        if mg_name:
            state.name_cache[cat.id] = clean_name(mg_name)
            return state.name_cache[cat.id]

    sf = ensure_loaded()
    try:
        names = cat.get_names_cls(sf) or []
        name = names[0] if names else f"Cat {cat.id}"
    except Exception:
        name = f"Cat {cat.id}"
    state.name_cache[cat.id] = clean_name(name)
    return state.name_cache[cat.id]


def summary(sf: core.SaveFile) -> dict[str, Any]:
    unlocked = sum(1 for c in sf.cats.cats if c.unlocked)
    trophy_owned = 0
    trophy_total = 0
    try:
        trophy_owned = len(getattr(sf.medals, "medal_data_1", []))
        medal_names = core.core_data.get_medal_names(sf)
        names = getattr(medal_names, "medal_names", None)
        if isinstance(names, list):
            trophy_total = sum(1 for row in names if isinstance(row, list) and len(row) > 0)
        else:
            trophy_total = trophy_owned
    except Exception:
        trophy_total = trophy_owned
    return {
        "path": str(state.loaded_path) if state.loaded_path else "",
        "inquiry_code": sf.inquiry_code,
        "country": str(sf.cc),
        "game_version": sf.game_version.to_string(),
        "cats_unlocked": unlocked,
        "cats_total": len(sf.cats.cats),
        "catfood": sf.catfood,
        "xp": sf.xp,
        "np": sf.np,
        "normal_tickets": sf.normal_tickets,
        "rare_tickets": sf.rare_tickets,
        "platinum_tickets": sf.platinum_tickets,
        "legend_tickets": sf.legend_tickets,
        "leadership": sf.leadership,
        "trophies_owned": trophy_owned,
        "trophies_total": trophy_total,
    }


def get_cat_total_forms(sf: core.SaveFile, cat: core.Cat) -> int:
    try:
        pic_book = sf.cats.read_nyanko_picture_book(sf)
        pb_cat = pic_book.get_cat(cat.id) if pic_book is not None else None
        if pb_cat is not None:
            return max(1, min(4, int(pb_cat.total_forms)))
    except Exception:
        pass
    return 4


def clamp_cat_forms(sf: core.SaveFile, cat: core.Cat) -> None:
    total_forms = get_cat_total_forms(sf, cat)
    max_form_index = max(0, total_forms - 1)

    cat.current_form = max(0, min(int(cat.current_form), max_form_index))
    cat.unlocked_forms = max(0, min(int(cat.unlocked_forms), total_forms))

    # 4th form flag should only exist on 4-form units.
    if total_forms < 4:
        cat.fourth_form = 0
    else:
        cat.fourth_form = max(0, min(int(cat.fourth_form), 2))


def inventory_payload(sf: core.SaveFile) -> dict[str, Any]:
    catseyes: list[dict[str, Any]] = []
    catfruit: list[dict[str, Any]] = []
    materials: list[dict[str, Any]] = []

    try:
        names_o = core.core_data.get_gatya_item_names(sf)
        items = core.core_data.get_gatya_item_buy(sf).get_by_category(5)
        if items is not None:
            for i, item in enumerate(items):
                if i >= len(sf.catseyes):
                    break
                catseyes.append(
                    {
                        "index": i,
                        "name": clean_name(names_o.get_name(item.id) or f"Catseye {item.id}"),
                        "amount": int(sf.catseyes[i]),
                    }
                )
    except Exception:
        pass

    try:
        names = core.Matatabi(sf).get_names() or []
        for i, amount in enumerate(sf.catfruit):
            name = names[i] if i < len(names) and names[i] else f"Catfruit {i}"
            catfruit.append({"index": i, "name": clean_name(name), "amount": int(amount)})
    except Exception:
        pass

    try:
        names_o = core.core_data.get_gatya_item_names(sf)
        items = core.core_data.get_gatya_item_buy(sf).get_by_category(7)
        mats = sf.ototo.base_materials.materials
        if items is not None:
            for i, item in enumerate(items):
                if i >= len(mats):
                    break
                materials.append(
                    {
                        "index": i,
                        "name": clean_name(names_o.get_name(item.id) or f"Material {item.id}"),
                        "amount": int(mats[i].amount),
                    }
                )
    except Exception:
        pass

    return {"ok": True, "catseyes": catseyes, "catfruit": catfruit, "materials": materials}


def trophies_payload(sf: core.SaveFile) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    owned = set(getattr(sf.medals, "medal_data_1", []))
    value_map = getattr(sf.medals, "medal_data_2", {}) or {}

    medal_names_list: list[list[str]] | None = None
    try:
        medal_names = core.core_data.get_medal_names(sf)
        names = getattr(medal_names, "medal_names", None)
        if isinstance(names, list):
            medal_names_list = names
    except Exception:
        medal_names_list = None

    if medal_names_list is not None:
        for medal_id, row in enumerate(medal_names_list):
            if not row:
                continue
            name = clean_name(row[0]) if row[0] else f"Trophy {medal_id}"
            desc = row[1] if len(row) > 1 else ""
            rows.append(
                {
                    "id": int(medal_id),
                    "name": name,
                    "description": str(desc),
                    "owned": medal_id in owned,
                    "value": int(value_map.get(medal_id, 0)),
                }
            )
    else:
        for medal_id in sorted(owned):
            rows.append(
                {
                    "id": int(medal_id),
                    "name": f"Trophy {medal_id}",
                    "description": "",
                    "owned": True,
                    "value": int(value_map.get(medal_id, 0)),
                }
            )

    rows.sort(key=lambda r: (not bool(r["owned"]), int(r["id"])))
    return {"ok": True, "trophies": rows}


@app.get("/")
def index():
    return send_from_directory("webui", "index.html")


@app.get("/api/status")
def api_status():
    loaded = state.save_file is not None
    if not loaded:
        return jsonify({"loaded": False, "summary": None})
    sf = ensure_loaded()
    return jsonify({"loaded": True, "summary": summary(sf)})


@app.post("/api/load")
def api_load():
    try:
        payload = request.get_json(force=True)
        raw_path = Path(payload.get("path", ""))
        file_path = resolve_input_path(raw_path)
        result = SaveManagement.load_save_file_path(core.Path(str(file_path)), None, False)
        if result is None:
            raise RuntimeError("Could not parse save file.")
        save_file, _backup = result
        state.save_file = save_file
        state.loaded_path = file_path
        state.name_cache = {}
        return jsonify({"ok": True, "summary": summary(save_file)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/pick_path")
def api_pick_path():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        initial = Path.home() / "Documents" / "bcsfe" / "saves"
        path = filedialog.askopenfilename(
            title="Select SAVE_DATA file",
            initialdir=str(initial),
        )
        root.destroy()
        if not path:
            return jsonify({"ok": False, "error": "No file selected."}), 400
        return jsonify({"ok": True, "path": path})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/save")
def api_save():
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
    try:
        sf = ensure_loaded()
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        default_name = (state.loaded_path.name + ".edited") if state.loaded_path else "SAVE_DATA.edited"
        path = filedialog.asksaveasfilename(
            title="Save edited save file",
            initialfile=default_name,
            initialdir=str((Path.home() / "Documents" / "bcsfe" / "saves")),
        )
        root.destroy()
        if not path:
            return jsonify({"ok": False, "error": "No output path selected."}), 400
        # keep linter quiet about used sf
        _ = sf
        return jsonify({"ok": True, "path": path})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/sync_mygamatoto")
def api_sync_mygamatoto():
    try:
        count = sync_mygamatoto_index()
        return jsonify({"ok": True, "count": count})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/cats")
def api_cats():
    try:
        sf = ensure_loaded()
        query = request.args.get("query", "").strip().lower()
        mode = request.args.get("filter", "All")

        rows: list[dict[str, Any]] = []
        for cat in sf.cats.cats:
            if mode == "Unlocked" and not cat.unlocked:
                continue
            if mode == "Locked" and cat.unlocked:
                continue

            name = get_cat_name(cat)
            haystack = f"{cat.id} {name}".lower()
            if query and query not in haystack:
                continue

            number = cat_number(cat)
            total_forms = get_cat_total_forms(sf, cat)
            rows.append(
                {
                    "id": cat.id,
                    "number": number,
                    "name": name,
                    "owned": bool(cat.unlocked),
                    "base": int(cat.upgrade.base + 1),
                    "plus": int(cat.upgrade.plus),
                    "form": int(cat.current_form),
                    "unlocked_forms": int(cat.unlocked_forms),
                    "fourth": int(cat.fourth_form),
                    "total_forms": int(total_forms),
                    "image_url": f"https://onestoppress.com/images/{number}_square.png",
                }
            )
        return jsonify({"ok": True, "cats": rows})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/inventory")
def api_inventory():
    try:
        sf = ensure_loaded()
        return jsonify(inventory_payload(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.get("/api/trophies")
def api_trophies():
    try:
        sf = ensure_loaded()
        return jsonify(trophies_payload(sf))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/trophies/update")
def api_trophies_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        medal_id = int(payload.get("id"))
        owned = bool(payload.get("owned"))
        if medal_id < 0:
            raise RuntimeError(f"Invalid trophy id: {medal_id}")

        if owned:
            sf.medals.add_medal(medal_id)
        else:
            sf.medals.remove_medal(medal_id)

        return jsonify(
            {
                "ok": True,
                "summary": summary(sf),
                "trophies": trophies_payload(sf)["trophies"],
            }
        )
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/inventory/update")
def api_inventory_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        category = str(payload.get("category", "")).strip().lower()
        index = int(payload.get("index"))
        amount = max(0, int(payload.get("amount")))

        if category == "catseyes":
            if index < 0 or index >= len(sf.catseyes):
                raise RuntimeError(f"Catseye index out of range: {index}")
            max_value = core.core_data.max_value_manager.get(core.MaxValueType.CATSEYES)
            sf.catseyes[index] = min(amount, int(max_value))
        elif category == "catfruit":
            if index < 0 or index >= len(sf.catfruit):
                raise RuntimeError(f"Catfruit index out of range: {index}")
            if sf.game_version < 110400:
                max_value = core.core_data.max_value_manager.get_old(core.MaxValueType.CATFRUIT)
            else:
                max_value = core.core_data.max_value_manager.get_new(core.MaxValueType.CATFRUIT)
            sf.catfruit[index] = min(amount, int(max_value))
        else:
            raise RuntimeError(f"Unsupported inventory category: {category}")

        return jsonify({"ok": True, "summary": summary(sf), "inventory": inventory_payload(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/resources")
def api_resources():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        for key, value in payload.items():
            if hasattr(sf, key):
                setattr(sf, key, int(value))
        return jsonify({"ok": True, "summary": summary(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/action")
def api_cats_action():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        action = payload.get("action", "")
        ids = [int(x) for x in payload.get("ids", [])]

        cats: list[core.Cat] = []
        for cid in ids:
            cat = sf.cats.get_cat_by_id(cid)
            if cat is not None:
                cats.append(cat)

        if action == "unlock":
            for cat in cats:
                cat.unlock(sf)
        elif action == "true_form":
            sf.cats.true_form_cats(sf, cats, force=False, set_current_forms=True)
        elif action == "fourth_form":
            sf.cats.fourth_form_cats(sf, cats, force=False, set_current_forms=True)
        elif action == "legit_max":
            for cat in cats:
                cat.unlock(sf)
                cat.catguide_collected = True
                power_up = core.PowerUpHelper(cat, sf)
                power_up.max_upgrade()
                cat.upgrade.plus = max(cat.upgrade.plus, power_up.get_max_possible_plus())
        else:
            raise RuntimeError(f"Unknown action: {action}")

        return jsonify({"ok": True, "summary": summary(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/update")
def api_cats_update():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        cat_id = int(payload.get("id"))
        cat = sf.cats.get_cat_by_id(cat_id)
        if cat is None:
            raise RuntimeError(f"Cat not found: {cat_id}")

        if "owned" in payload:
            owned = bool(payload.get("owned"))
            if owned:
                cat.unlock(sf)
            else:
                cat.unlocked = 0

        if "base" in payload:
            base_level = max(1, int(payload.get("base")))
            cat.upgrade.base = base_level - 1

        if "plus" in payload:
            cat.upgrade.plus = max(0, int(payload.get("plus")))

        if "form" in payload:
            cat.current_form = max(0, min(3, int(payload.get("form"))))

        if "unlocked_forms" in payload:
            cat.unlocked_forms = max(0, min(4, int(payload.get("unlocked_forms"))))

        if "fourth" in payload:
            cat.fourth_form = max(0, int(payload.get("fourth")))

        clamp_cat_forms(sf, cat)

        return jsonify({"ok": True, "summary": summary(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/cats/bulk")
def api_cats_bulk():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)

        ids_raw = payload.get("ids")
        cats: list[core.Cat] = []
        if isinstance(ids_raw, list) and ids_raw:
            wanted = {int(x) for x in ids_raw}
            for cat in sf.cats.cats:
                if cat.id in wanted:
                    cats.append(cat)
        else:
            cats = list(sf.cats.cats)

        if bool(payload.get("owned_only", False)):
            cats = [c for c in cats if bool(c.unlocked)]

        if not cats:
            return jsonify({"ok": True, "count": 0, "summary": summary(sf)})

        if bool(payload.get("unlock", False)):
            for cat in cats:
                cat.unlock(sf)

        if bool(payload.get("legit_max", False)):
            for cat in cats:
                cat.unlock(sf)
                cat.catguide_collected = True
                power_up = core.PowerUpHelper(cat, sf)
                power_up.max_upgrade()
                cat.upgrade.plus = max(cat.upgrade.plus, power_up.get_max_possible_plus())

        if "base" in payload:
            base_level = max(1, int(payload.get("base")))
            for cat in cats:
                cat.upgrade.base = base_level - 1

        if "plus" in payload:
            plus = max(0, int(payload.get("plus")))
            for cat in cats:
                cat.upgrade.plus = plus

        if "form" in payload:
            form = max(0, min(3, int(payload.get("form"))))
            for cat in cats:
                cat.current_form = form

        if "unlocked_forms" in payload:
            unlocked_forms = max(0, min(4, int(payload.get("unlocked_forms"))))
            for cat in cats:
                cat.unlocked_forms = unlocked_forms

        if bool(payload.get("true_form", False)):
            sf.cats.true_form_cats(sf, cats, force=False, set_current_forms=True)

        if bool(payload.get("fourth_form", False)):
            sf.cats.fourth_form_cats(sf, cats, force=False, set_current_forms=True)

        for cat in cats:
            clamp_cat_forms(sf, cat)

        return jsonify({"ok": True, "count": len(cats), "summary": summary(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/op")
def api_op():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        key = payload.get("key", "")
        if key not in OPERATIONS:
            raise RuntimeError(f"Unknown operation: {key}")
        _, op = OPERATIONS[key]
        op(sf)
        return jsonify({"ok": True, "summary": summary(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


@app.post("/api/preset")
def api_preset():
    try:
        sf = ensure_loaded()
        payload = request.get_json(force=True)
        preset = str(payload.get("preset", ""))
        keys = PRESETS.get(preset)
        if not keys:
            raise RuntimeError(f"Unknown preset: {preset}")
        failed: list[str] = []
        for key in keys:
            try:
                _, op = OPERATIONS[key]
                op(sf)
            except Exception:
                failed.append(key)
        return jsonify({"ok": True, "failed": failed, "summary": summary(sf)})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


def main():
    core.core_data.init_data()
    load_mygamatoto_index()
    app.run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
