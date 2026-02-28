# Battle Cats Account Data Map and UI Roadmap

## Purpose
This document is a full product/engineering map of account data domains for Battle Cats, with:
- what a complete editor should cover
- current support status in this repo
- a concrete UI architecture and implementation checklist

Status labels used below:
- `WEB`: supported in current `modern_web_ui.py` + `webui/*`
- `CORE/CLI`: supported in repo backend/core or CLI flows, but not exposed in web UI
- `MISSING`: not currently exposed and not clearly implemented in current web surface

---

## A) Identity and Metadata (Account Header)

### Data domain
- Inquiry code
- Region / country code
- Game version
- Save file path / slot context
- User Rank (UR)
- User Rank reward state
- Officer's Club / Gold Pass related data
- Play time / play stats

### Current status
- Inquiry code / country / game version / path: `WEB`
- UR calculation and UR reward systems: `CORE/CLI`
- Officer pass / Nyanko club data and fixes: `CORE/CLI`
- Playtime edit path exists: `CORE/CLI`

---

## B) Currencies and Consumables (Economy)

### Data domain
- XP, NP, Catfood
- Tickets: Normal, Rare, Platinum, Legend
- Leadership
- Battle items: Speed Up, Treasure Radar, Rich Cat, Cat CPU, Cat Jobs, Sniper
- Catamins A/B/C
- Other item buckets used by game systems

### Current status
- XP/NP/Catfood/tickets/leadership quick edit: `WEB`
- Battle items: preset operations only in web flow, direct table editing is `MISSING` in UI
- Catamins: available in operations/presets, direct UI editing is `MISSING`
- Additional item buckets exist in core/CLI feature map: `CORE/CLI`

---

## C) Units (Cats)

### Data domain
- Ownership/unlock
- Base/Plus levels
- Current form + unlocked forms + 4th form flag
- True Form / Ultra Form state and requirement context
- Talents (per talent level/state)
- Talent orbs (orb inventory + equip state/slot state)
- Catseye level-cap progression including Dark Catseye related extensions
- Cat Guide discovered vs owned state

### Current status
- Ownership/base/plus/forms/4th + inline/bulk editing: `WEB`
- True/4th form actions and legit max actions: `WEB`
- Talent max as operation/preset effect: `WEB` via backend operation
- Detailed per-talent UI and cost preview: `MISSING`
- Talent orb editing exists in core/CLI (`talent_orbs`), not in web UI: `CORE/CLI`
- Cat guide claim/unclaim exists in CLI features, not in web UI: `CORE/CLI`
- Ultra requirement-aware UI: `MISSING`

---

## D) Progression State

### Data domain
- Story progression (EoC/ItF/CotC, Aku progression state)
- Story treasures per stage/chapter tier
- Legend/event/collab/gauntlet/zero-legends progression
- Crown difficulty progression where applicable
- Outbreak progression
- Unlock gates for systems (talents/equip/etc.)

### Current status
- Story and many map domains can be edited/cleared through operations/presets: `WEB` (preset/op driven)
- Rich progression editors (trees, crowns, chapter/stage detail): `MISSING` in web UI
- Extensive map editing exists in repo feature handler (`levels.*`): `CORE/CLI`
- Zero Legends crash risk mitigation has been patched for preset clear operations: `WEB`

---

## E) Base and Upgrades

### Data domain
- Base upgrades (worker rate/wallet, research, cannon stats, base defense, etc.)
- Ototo development (cannon development and related progression)

### Current status
- Base/support upgrades max operation exists and is used by preset: `WEB` (via operation key)
- Dedicated editable base-upgrade UI panel: `MISSING`
- Ototo cannon editing exists in core/CLI (`ototo_cat_cannon`): `CORE/CLI`

---

## F) Inventory (Unified)

### Data domain
- Catseyes (all types)
- Catfruit/seeds/Aku fruit
- Behemoth stones/gems
- Ototo/base materials
- Battle items + catamins
- Tickets and other consumable categories

### Current status
- Catseyes and catfruit row editing: `WEB`
- Base materials view-only in web UI: `WEB` (read-only)
- Base materials editing exists in CLI features: `CORE/CLI`
- Behemoth stone/gem dedicated inventory UI: `MISSING`
- Battle items/catamins item-table editing: `MISSING` in web UI

---

## G) Achievements, Collections, Encyclopedias

### Data domain
- Meow medals (trophies)
- Lineup unlock relation to medal counts (threshold visibility)
- Enemy guide completion state
- Cat guide discovered/claimed state

### Current status
- Trophy list and add/remove actions: `WEB`
- Lineup unlock threshold display tied to medals: `MISSING` in web UI
- Enemy guide edit flows exist in CLI features: `CORE/CLI`
- Cat guide claim/unclaim exists in CLI features: `CORE/CLI`

---

## H) Side Modes and Specialized State

### Data domain
- Gamatoto expedition state (xp, helpers, return status)
- Catclaw Dojo / ranking scores
- Underground Labyrinth results/medals
- Cat Shrine state

### Current status
- Gamatoto sync + max operation: `WEB`
- Dojo score editing exists in CLI features: `CORE/CLI`
- Labyrinth medals appear in operations/presets, detailed UI is `MISSING`
- Cat Shrine editing exists in CLI features: `CORE/CLI`

---

## Recommended UI Information Architecture

Keep the current 3-column layout, but promote domain navigation and reduce mixing.

## Left rail (navigation + account snapshot)
- Dashboard
- Units
- Progress
- Base
- Inventory
- Achievements
- Encyclopedias
- Tools

## Center workspace
- Domain-specific main editor (tables, trees, grids, diff previews)

## Right inspector
- Selected entity details
- Validation warnings
- Apply controls

---

## Domain-by-Domain UI Additions

## 1) Dashboard
- Show UR prominently and reward context
- Progress cards (treasures by saga, crowns summary, medals summary)
- Integrity checks panel:
  - out-of-range values
  - impossible combos
  - unsupported edit categories

## 2) Units
- Column sorting and saved filters
- Debounced search with local post-fetch filtering
- Keyboard selection improvements (shift range, arrows)
- Right inspector additions:
  - per-talent editing with NP cost preview
  - orb equipment/inventory controls
  - ultra requirement widget
  - material requirement display
- Replace blind bulk actions with diff-first planner + confirm

## 3) Progress
- Treasures editor grid (tier-safe values only)
- Story/chapter/stage tree view
- Crown matrix where applicable
- High-risk warnings and optional "enable risky editing" gate

## 4) Base
- Base Upgrades tab (worker/wallet/research/cannon/etc., with caps)
- Ototo tab (cannon data + development links)

## 5) Inventory
- Sidebar categories:
  - tickets
  - battle items
  - catamins
  - catseyes
  - catfruit/seeds/Aku fruit
  - behemoth stones/gems
  - ototo materials
- Per-category batch apply with clamp and cap hints

## 6) Achievements
- Medal filtering by source
- Lineup unlock threshold tracker
- hard-confirm bulk grant actions

## 7) Encyclopedias
- Enemy Guide view/filter
- Cat Guide discovered vs owned indicators

## 8) Tools
- Preset diff preview before apply
- In-session mutation log
- Patch export/import (JSON delta)
- Validation report
- Safe mode toggle

---

## Quality and Safety Priorities

## P0 (must-have safety)
1. Clamp all mutable numeric endpoints (especially `/api/resources`).
2. Confirmation modals for presets and global bulk edits.
3. Diff-first workflow for high-impact operations.
4. Undo stack (minimum 20 steps).
5. Editable parity for base materials if shown in inventory.

## P1 (speed and clarity)
1. Loading indicators and action disabling during async operations.
2. Debounced search.
3. Active use of toast notifications (not only status bar text).
4. Table virtualization and sort controls.

## P2 (power workflows)
1. Global command/search (`Ctrl+K`).
2. Keyboard shortcuts (`Ctrl+S`, `/`, `Esc`).
3. Saved views (filters/sort/column presets).

## P3 (accessibility and maintainability)
1. ARIA live region for status updates.
2. Non-color state indicators.
3. Split `webui/app.js` into modules.
4. API schema validation.

---

## Implementation Notes for This Repo

- A large portion of missing web features already exists in backend/core or CLI paths (`feature_handler`), so many additions are exposure + validation work rather than raw reverse engineering.
- Existing operations/presets in `simple_max_account.py` already cover:
  - support/base upgrades max
  - full map clear categories with safer pointer behavior
  - legit cat max and talent max
  - story clear variants and Gamatoto max
- Current web UI already has a solid base for:
  - cats table editing
  - resources form
  - inventory partial editor
  - trophies editor
  - operation/preset wiring

This roadmap is designed to extend that foundation without replacing the current architecture in one risky step.
