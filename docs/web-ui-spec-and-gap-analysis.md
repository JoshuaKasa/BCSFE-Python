# Battle Cats Web UI: Visual + Functional Documentation

Related planning document:
- `docs/account-data-map-and-ui-roadmap.md` (full account-domain map + implementation roadmap)

## 1) Scope
This document describes the current web UI in this repository and audits missing pieces.

Source of truth:
- `webui/index.html`
- `webui/styles.css`
- `webui/app.js`
- `modern_web_ui.py`
- `simple_max_account.py` (preset and operation behavior shown in UI)

---

## 2) Visual Design System

### 2.1 Color Tokens
Defined in `webui/styles.css`:

| Token | Value | Purpose |
|---|---|---|
| `--bg` | `#050505` | App background base |
| `--panel` | `#111111` | Main panel top gradient color |
| `--panel-2` | `#0b0b0b` | Main panel bottom gradient color |
| `--text` | `#f1f1f1` | Primary text |
| `--muted` | `#b7b7b7` | Secondary labels/helper text |
| `--accent` | `#4ec9ff` | Active tab/border hover emphasis |
| `--ok` | `#38d39f` | Success semantic token (currently not heavily used) |
| `--warn` | `#ffd479` | Warning semantic token (currently not heavily used) |

Additional hard-coded surfaces:
- Top bar: `#0c0c0c`
- Inputs/buttons: `#141414`
- Table header: `#181818`
- Selected row: `#243349`
- Owned row tint: `#131a24`
- Missing row tint: `#24171f`

### 2.2 Typography and Iconography
- Font stack: `"Segoe UI", "Noto Sans", sans-serif`
- Brand line uses heavier weight and slightly larger size.
- Icons are 14px defaults, 16px in brand.
- Most sections use icon + heading for quick scanning.

### 2.3 Layout and Spatial System
- Full-screen app shell with 4 rows:
1. Sticky top bar
2. Main 3-column workspace
3. Unsaved-changes save bar (hidden until dirty)
4. Status bar

- Main workspace grid:
1. Left panel: `300px`
2. Center panel: `minmax(650px, 1fr)`
3. Right panel: `360px`

- Responsive breakpoints:
- `<1300px`: columns shrink (`260 / fluid / 320`)
- `<980px`: layout stacks vertically, sticky behaviors disabled, table height capped

Visual direction: high-contrast dark editor UI with blue accent emphasis.

---

## 3) Information Architecture

## 3.1 Top Bar
Purpose: file/session lifecycle + advanced utility.

Controls:
- `Load`: pick and load save
- `Save As`: write edited save to chosen path
- `Refresh`: re-query current state from backend
- Path label: current loaded file path
- `Advanced > Sync MyGamatoto`: refresh cat name index from external API

## 3.2 Left Panel (Context + Global Actions)
Tabbed sections:
- `Summary`
- `Resources`
- `Presets`

### Summary
Purpose: account-level snapshot.

Shows:
- Path, inquiry code, country, game version
- Cats unlocked/total
- Core resources (catfood/xp/np/tickets)
- Trophies owned/total

### Resources
Purpose: quick numeric editing of economy values.

Editable fields:
- Catfood, XP, NP
- Normal/Rare/Platinum/Legend tickets
- Leadership

Actions:
- `Apply Resource Edits`
- `Max Gamatoto` (operation call)

### Presets
Purpose: one-click multi-operation account transforms.

Shown presets:
- `10` Human-max progression (recommended)
- `9` Full legit max (keep current treasures)
- `1` Safer max resources
- `5` Starter boost

## 3.3 Center Panel (Cats Workspace)
Purpose: high-volume unit management and batch edits.

Sections:
- Sticky toolbar with filters and search
- Quick actions card (selected cats only)
- Bulk actions card (visible/all scope + owned-only option)
- Editable cats table

Table columns:
- Image, ID, Name, Owned, Base, Plus, Form, Forms, 4th

Interactions:
- Single click selects row
- Ctrl/Cmd click multi-select
- Double-click inline editing for `Base`, `Plus`, `Form`
- Search filters by cat ID or name
- Filter modes: All / Unlocked / Locked

## 3.4 Right Panel (Detail + Item Editors)
Tabbed sections:
- `Preview`
- `Edit Cat`
- `Inventory`
- `Trophies`

### Preview
Purpose: read-only cat detail card for current selection.

### Edit Cat
Purpose: explicit single-cat form editor.

Fields:
- ID (locked), Owned, Base, Plus, Form, Unlocked Forms, Fourth
- `Apply Cat Edit`

### Inventory
Purpose: item-level editing for progression materials.

Subtabs:
- Catseyes (editable)
- Catfruit (editable)
- Base Mats (read-only in current UI behavior)

### Trophies
Purpose: medal/trophy ownership management.

Per-row actions:
- Add (if missing)
- Remove (if owned)

---

## 4) Interaction and State Model

`webui/app.js` maintains a single mutable `state` object:
- cats list
- selected IDs
- selected cat
- inventory tab and data
- trophies list
- current tabs
- current loaded path
- dirty flag

Dirty-state UX:
- `markDirty(true)` shows a save bar with `Revert` and `Save As`
- Browser unload warning appears when unsaved changes exist

Feedback model:
- Bottom status bar updates for all operations
- No dedicated spinner/progress UI
- Toast container exists in HTML but is currently unused by JS

---

## 5) Backend API Mapping (UI -> Flask)

| UI Action | Endpoint | Notes |
|---|---|---|
| Initial status | `GET /api/status` | Determines loaded state |
| File picker (load) | `GET /api/pick_path` | Tkinter native dialog |
| Load save | `POST /api/load` | Parses save file |
| File picker (save) | `GET /api/pick_save_path` | Tkinter native dialog |
| Save edited file | `POST /api/save` | Writes current save |
| Refresh cat list | `GET /api/cats` | Query + filter |
| Apply cat action | `POST /api/cats/action` | unlock/true_form/fourth_form/legit_max |
| Update one cat | `POST /api/cats/update` | Single-cat field edits |
| Bulk cat update | `POST /api/cats/bulk` | Optional scope and owned-only |
| Read inventory | `GET /api/inventory` | Catseyes/catfruit/materials |
| Update inventory | `POST /api/inventory/update` | Only catseyes/catfruit supported |
| Read trophies | `GET /api/trophies` | Owned + metadata |
| Update trophy | `POST /api/trophies/update` | Add/remove medal |
| Resources form submit | `POST /api/resources` | Direct numeric assignment |
| Run operation | `POST /api/op` | Single op key |
| Run preset | `POST /api/preset` | Sequential operation set |
| Sync names | `POST /api/sync_mygamatoto` | External API call + cache write |

---

## 6) What Is Missing (Current Gaps)

## 6.1 Safety/Correctness Gaps
1. Resource edit values are not clamped in `/api/resources`.
- Current behavior assigns numeric fields directly if attribute exists.
- Risk: out-of-range values can become unrealistic or unstable.

2. No confirmation guard for large-impact actions.
- Presets and bulk all-cat operations execute immediately.
- Risk: accidental irreversible edits before manual save.

3. Inventory editor is asymmetric.
- Base materials are visible but not editable.
- Backend rejects non-catseye/catfruit categories.

4. Error handling lacks structured recovery guidance.
- Status bar shows text errors but no inline remediation.

## 6.2 UX Gaps
1. No loading indicators for long operations.
- Preset application and full cat refresh can feel frozen.

2. Search has no debounce.
- Triggers network call on every keystroke.

3. No sort controls in cat table.
- Large saves become harder to navigate.

4. No diff/preview before applying preset.
- User cannot see exactly what will change in advance.

5. No session history or undo stack.
- Only full-file revert to last loaded state.

## 6.3 Accessibility Gaps
1. Limited keyboard-first workflow for table selection/edit flows.
2. Minimal ARIA semantics for dynamic sections beyond basic tablist roles.
3. Color-only state signaling in some areas (owned/missing row tint).

## 6.4 Architecture/Maintainability Gaps
1. Frontend logic is in one large `app.js` file.
- Harder to test and maintain as features grow.

2. No frontend tests for key flows.
- Regressions likely in tab switching, state sync, and edit flows.

3. No explicit API contract/schema validation layer.
- Client and server rely on implicit shape agreement.

4. UI theme is not configurable.
- Design tokens exist but no user-facing theme settings.

---

## 7) Recommended Next Steps (Priority Order)

## P0 (Do first)
1. Clamp all `/api/resources` fields to known max/min bounds via `max_value_manager`.
2. Add confirmation modal for:
- Preset apply
- Bulk action with scope = all
- Trophy mass operations (if added)
3. Add editable Base Materials support end-to-end (`/api/inventory/update` + UI row editor).

## P1
1. Add debounce (`200-300ms`) to search input.
2. Add lightweight loading state (button disabled + spinner text).
3. Add table sorting (ID, owned, base, plus).

## P2
1. Add keyboard shortcuts for common actions (`Ctrl+S`, `/` for search).
2. Improve ARIA labels/live regions for status updates.
3. Add explicit non-color badges for owned/missing rows.

## P3
1. Split `app.js` into modules (`api`, `state`, `cats`, `inventory`, `trophies`, `ui`).
2. Add smoke tests for major flows (Playwright or Cypress).
3. Add schema validation for API payloads.

---

## 8) Current UI Quality Summary

Strengths:
- Clear three-column workflow with practical editing surfaces.
- Good balance between quick actions, bulk edits, and detailed single-cat editing.
- Preset and operation integration is straightforward.
- Trophies integration is present and functional.

Main limitations:
- Missing guardrails and clamping on some high-impact edits.
- Missing editing parity for some visible data (Base Materials).
- Needs stronger UX feedback and accessibility polish for scale.
