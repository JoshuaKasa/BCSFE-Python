// State, constants, and shared utilities
const state = {
  page: "home",
  cats: [],
  catRows: new Map(),
  selectedIds: new Set(),
  selectedCat: null,
  lastSelectedIndex: null,
  previewTab: "stats",
  inventoryTab: "all",
  inventory: { battle_items: [], catamins: [], catseyes: [], catfruit: [], talent_orbs: [], materials: [] },
  trophies: [],
  dashboard: { cards: [] },
  progress: null,
  storyChapters: [],
  baseUpgrades: [],
  baseCannons: [],
  baseSelectedParts: [0, 0, 0],
  transferHistory: [],
  transferStorage: null,
  gamatoto: null,
  catTalents: [],
  playtime: null,
  enemies: [],
  selectedEnemy: null,
  validation: [],
  encyclopedias: null,
  currentPath: null,
  dirty: false,
  safeMode: true,
  history: { can_undo: false, can_redo: false },
  searchTimer: null,
  enemySearchTimer: null,
  collapsedTalentOrbGroups: new Set(),
};

const TRANSFER_FORM_STORAGE_KEY = "bcsfe_transfer_form_v1";

const $ = (id) => document.getElementById(id);
const ITEM_ICON_BASE = "https://battlecats.miraheze.org/wiki/Special:FilePath/";
const ORB_ATTRIBUTE_SPRITE_URL = `${ITEM_ICON_BASE}${encodeURIComponent("Equipment_attribute_14.3.png")}`;
const ORB_EFFECT_SPRITE_URL = `${ITEM_ICON_BASE}${encodeURIComponent("Equipment_effect_15.1.png")}`;
const ORB_GRADE_SPRITE_URL = `${ITEM_ICON_BASE}${encodeURIComponent("Equipment_grade.png")}`;
const ORB_ATTR_INDEX_BY_GROUP = {
  red: 0,
  floating: 1,
  black: 2,
  metal: 3,
  angel: 4,
  all: 5,
  alien: 6,
  zombie: 7,
  relic: 8,
  white: 9,
  traitless: 9,
  aku: 10,
};
const ORB_ATTR_INDEX_BY_TARGET_ID = {
  0: 0,
  1: 1,
  2: 2,
  3: 3,
  4: 4,
  5: 6,
  6: 7,
  7: 8,
  8: 9,
  9: 5,
  10: 10,
  11: 10,
};
const CATEGORY_FALLBACK_ICONS = {
  battle_items: "inventory",
  catamins: "inventory",
  catseyes: "catseye",
  catfruit: "catfruit",
  talent_orbs: "material",
  materials: "material",
  enemies: "chart",
  trophies: "preset",
};
const CATEGORY_ITEM_IDS = {
  battle_items: [0, 1, 2, 3, 4, 5],
  catamins: [55, 56, 57],
  catseyes: [50, 51, 52, 53, 54, 58],
  catfruit: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 160, 161, 164, 167, 168, 169, 170, 171, 179, 180, 181, 182, 183, 184],
  materials: [85, 86, 87, 88, 89, 90, 91, 140, 187, 188, 189, 190, 191, 192, 193, 194],
};
const ITEM_ID_ICON_ALIAS = {
  61: 60,
  35: 30,
  36: 31,
  37: 32,
  38: 33,
  39: 34,
  167: 30,
  168: 31,
  169: 32,
  170: 33,
  171: 34,
  179: 30,
  180: 31,
  181: 32,
  182: 33,
  183: 34,
  184: 40,
};
const CANNON_ICON_FILE_BY_NAME = {
  "cat cannon": "Cannon.png",
  "slow beam": "Slow_Cannon.png",
  "slow beam cannon": "Slow_Cannon.png",
  "iron wall": "Iron_Cannon.png",
  "iron wall cannon": "Iron_Cannon.png",
  thunderbolt: "Thunderbolt_Cannon.png",
  "thunderbolt cannon": "Thunderbolt_Cannon.png",
  waterblast: "Waterblast_Cannon.png",
  "water blast": "Waterblast_Cannon.png",
  "waterblast cannon": "Waterblast_Cannon.png",
  "holy blast": "Holy_Cannon.png",
  "holy blast cannon": "Holy_Cannon.png",
  "breakerblast": "Breakerblast_Cannon.png",
  "breaker blast": "Breakerblast_Cannon.png",
  "breakerblast cannon": "Breakerblast_Cannon.png",
  curseblast: "Curseblast_Cannon.png",
  "curse blast": "Curseblast_Cannon.png",
  "curseblast cannon": "Curseblast_Cannon.png",
};
const NAME_ITEM_ID_FALLBACK = {
  "speed up": 0,
  "treasure radar": 1,
  "rich cat": 2,
  "cat cpu": 3,
  "cat jobs": 4,
  "sniper the cat": 5,
  "catamin [a]": 55,
  "catamin [b]": 56,
  "catamin [c]": 57,
  "catseye [special]": 50,
  "catseye [rare]": 51,
  "catseye [super rare]": 52,
  "catseye [uber rare]": 53,
  "catseye [legend]": 54,
  "catseye [dark]": 58,
  "purple catfruit seed": 30,
  "red catfruit seed": 31,
  "blue catfruit seed": 32,
  "green catfruit seed": 33,
  "yellow catfruit seed": 34,
  "purple catfruit": 30,
  "red catfruit": 31,
  "blue catfruit": 32,
  "green catfruit": 33,
  "yellow catfruit": 34,
  "epic catfruit": 40,
  "elder catfruit seed": 41,
  "elder catfruit": 42,
  "epic catfruit seed": 43,
  "gold catfruit": 44,
  "aku catfruit seed": 160,
  "aku catfruit": 161,
  "gold catfruit seed": 164,
  bricks: 85,
  feathers: 86,
  coal: 87,
  sprockets: 88,
  gold: 89,
  meteorite: 90,
  "beast bones": 91,
  ammonite: 140,
  "brick z": 187,
  "feathers z": 188,
  "coal z": 189,
  "sprockets z": 190,
  "gold z": 191,
  "meteorite z": 192,
  "beast bones z": 193,
  "ammonite z": 194,
};
const TOOL_OPERATIONS = {
  tool_catfood_topup: { key: "catfood_topup", label: "Catfood Top-up (1500)" },
  tool_xp: { key: "xp", label: "Max XP" },
  tool_np: { key: "np", label: "Max NP" },
  tool_battle_items: { key: "battle_items", label: "Max Battle Items" },
  tool_catfruit: { key: "catfruit", label: "Max Catfruit" },
  tool_catseyes: { key: "catseyes", label: "Max Catseyes" },
  tool_catamins: { key: "catamins", label: "Max Catamins" },
  tool_base_materials: { key: "base_materials", label: "Max Base Materials" },
  tool_special_skills_max: { key: "special_skills_max", label: "Max Base Upgrades" },
  tool_cat_base_cannons_max: { key: "cat_base_cannons_max", label: "Max Base Cannons" },
  tool_max_gamatoto: { key: "max_gamatoto", label: "Max Gamatoto" },
  tool_unlock_all_cats: { key: "unlock_all_cats", label: "Unlock All Cats" },
  tool_legit_max_cats: { key: "legit_max_cats", label: "Legit Max Cats" },
  tool_clear_story_only: { key: "clear_story_only", label: "Clear Story Only" },
  tool_clear_story_superior_treasures: {
    key: "clear_story_superior_treasures",
    label: "Clear Story + Superior Treasures",
  },
  tool_clear_all_maps: { key: "clear_all_maps", label: "Clear All Maps" },
};

function normalizeName(value) {
  return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function wikiItemIconUrl(itemId) {
  const id = Number(itemId);
  if (!Number.isInteger(id) || id < 0) return null;
  const resolved = ITEM_ID_ICON_ALIAS[id] ?? id;
  const padded = resolved < 10 ? `0${resolved}` : String(resolved);
  return `${ITEM_ICON_BASE}${encodeURIComponent(`GatyaitemD_${padded}_f.png`)}`;
}

function wikiFileIconUrl(fileName) {
  if (!fileName) return null;
  return `${ITEM_ICON_BASE}${encodeURIComponent(String(fileName))}`;
}

function fallbackIconForCategory(category) {
  return `/webui/icons/${CATEGORY_FALLBACK_ICONS[category] || "inventory"}.svg`;
}

function resolveBaseUpgradeIconUrl(row) {
  const byId = wikiItemIconUrl(Number(row?.item_id));
  if (byId) return byId;
  if (row?.icon_url) return row.icon_url;
  return "/webui/icons/material.svg";
}

function resolveCannonIconUrl(cannon) {
  const rawName = String(cannon?.name || "");
  const normalized = normalizeName(rawName);
  const direct = CANNON_ICON_FILE_BY_NAME[normalized];
  if (direct) return wikiFileIconUrl(direct);
  return wikiFileIconUrl("Cannon_Icon.png");
}

function resolveInventoryItemId(category, row) {
  if (category === "talent_orbs") return null;
  const rawItemId = row?.item_id;
  if (rawItemId !== null && rawItemId !== undefined && rawItemId !== "") {
    const explicit = Number(rawItemId);
    if (Number.isInteger(explicit) && explicit >= 0) return explicit;
  }
  const byIndex = CATEGORY_ITEM_IDS[category];
  if (Array.isArray(byIndex) && Number.isInteger(Number(row?.index))) {
    const mapped = byIndex[Number(row.index)];
    if (Number.isInteger(mapped)) return mapped;
  }
  const byName = NAME_ITEM_ID_FALLBACK[normalizeName(row?.name)];
  if (Number.isInteger(byName)) return byName;
  return null;
}

function resolveInventoryIconUrl(category, row) {
  // Talent orbs should always prefer explicit orb icon URL, not gatyaitem mapping.
  if (category === "talent_orbs" && row?.icon_url) return row.icon_url;
  const byId = wikiItemIconUrl(resolveInventoryItemId(category, row));
  if (byId) return byId;
  if (row?.icon_url) return row.icon_url;
  return fallbackIconForCategory(category);
}

function orbCellStyle(spriteUrl, col, row, cols, rows) {
  const size = 18;
  const x = Math.max(0, Number(col) || 0);
  const y = Math.max(0, Number(row) || 0);
  return `background-image:url('${spriteUrl}');background-size:${cols * size}px ${rows * size}px;background-position:-${x * size}px -${y * size}px;`;
}

function resolveTalentOrbAttrIndex(row) {
  const groupKey = normalizeName(row?.group);
  if (groupKey && Number.isInteger(ORB_ATTR_INDEX_BY_GROUP[groupKey])) return ORB_ATTR_INDEX_BY_GROUP[groupKey];
  if (groupKey.includes("all")) return ORB_ATTR_INDEX_BY_GROUP.all;
  if (groupKey.includes("traitless") || groupKey.includes("white")) return ORB_ATTR_INDEX_BY_GROUP.traitless;
  if (groupKey.includes("floating")) return ORB_ATTR_INDEX_BY_GROUP.floating;
  if (groupKey.includes("alien")) return ORB_ATTR_INDEX_BY_GROUP.alien;
  if (groupKey.includes("zombie")) return ORB_ATTR_INDEX_BY_GROUP.zombie;
  if (groupKey.includes("relic")) return ORB_ATTR_INDEX_BY_GROUP.relic;
  if (groupKey.includes("angel")) return ORB_ATTR_INDEX_BY_GROUP.angel;
  if (groupKey.includes("metal")) return ORB_ATTR_INDEX_BY_GROUP.metal;
  if (groupKey.includes("black")) return ORB_ATTR_INDEX_BY_GROUP.black;
  if (groupKey.includes("red")) return ORB_ATTR_INDEX_BY_GROUP.red;
  if (groupKey.includes("aku")) return ORB_ATTR_INDEX_BY_GROUP.aku;
  const targetId = Number(row?.target_id);
  if (Number.isInteger(targetId) && Number.isInteger(ORB_ATTR_INDEX_BY_TARGET_ID[targetId])) {
    return ORB_ATTR_INDEX_BY_TARGET_ID[targetId];
  }
  return ORB_ATTR_INDEX_BY_GROUP.all;
}

function renderTalentOrbIcon(row) {
  const effectIdRaw = Number(row?.effect_id);
  const rankIdRaw = Number(row?.rank_id);
  const effectId = Number.isInteger(effectIdRaw) ? effectIdRaw : 0;
  const rankId = Number.isInteger(rankIdRaw) ? rankIdRaw : 0;
  const targetIndex = resolveTalentOrbAttrIndex(row);
  const effectIndex = effectId >= 0 && effectId <= 29 ? effectId : 0;
  const gradeIndex = rankId >= 0 && rankId <= 4 ? rankId : 0;
  const attrCol = targetIndex % 6;
  const attrRow = Math.floor(targetIndex / 6);
  const effectCol = effectIndex % 5;
  const effectRow = Math.floor(effectIndex / 5);
  const gradeCol = gradeIndex % 3;
  const gradeRow = Math.floor(gradeIndex / 3);
  const attrStyle = orbCellStyle(ORB_ATTRIBUTE_SPRITE_URL, attrCol, attrRow, 6, 2);
  const effectStyle = orbCellStyle(ORB_EFFECT_SPRITE_URL, effectCol, effectRow, 5, 6);
  const gradeStyle = orbCellStyle(ORB_GRADE_SPRITE_URL, gradeCol, gradeRow, 3, 2);
  return `<span class="orb-icon-composite" aria-hidden="true"><span class="orb-layer orb-attr" style="${attrStyle}"></span><span class="orb-layer orb-effect" style="${effectStyle}"></span><span class="orb-layer orb-grade" style="${gradeStyle}"></span></span>`;
}

function applyItemIconFallback(img, category) {
  if (!img) return;
  const fallback = fallbackIconForCategory(category);
  img.onerror = () => {
    if (img.dataset.fallbackApplied === "1") return;
    img.dataset.fallbackApplied = "1";
    img.referrerPolicy = "";
    img.src = fallback;
  };
}

function withReveal(el, index = 0) {
  if (!el) return;
  el.classList.add("reveal");
  el.style.setProperty("--stagger", String(index));
}

function bindStaticIconFallbacks() {
  document.querySelectorAll(".item-icon").forEach((img) => {
    img.onerror = () => {
      img.onerror = null;
      img.referrerPolicy = "";
      img.src = "/webui/icons/inventory.svg";
    };
  });
}

function setButtonTooltips() {
  const tooltips = {
    loadBtn: "Pick and load a save file from disk.",
    saveBtn: "Save the current edited save to a new file path.",
    saveBarSaveBtn: "Save the current edited save to a new file path.",
    refreshBtn: "Reload summary and all editor sections from current in-memory save.",
    revertBtn: "Discard unsaved changes and reload from current file path.",
    undoBtn: "Undo the last applied edit.",
    redoBtn: "Redo the last undone edit.",
    syncBtn: "Refresh cat names using MyGamatoto naming data.",
    applyResourcesBtn: "Apply the resource values in this panel.",
    applyPlaytimeBtn: "Apply the playtime values in this panel.",
    add24hBtn: "Add 24 hours to current playtime.",
    maxGamatotoBtn: "Apply max legal Gamatoto preset operation.",
    applyCatEditBtn: "Save the selected cat edits.",
    bulkUnlockBtn: "Unlock every cat in current bulk scope.",
    bulkTrueFormBtn: "Unlock true forms in current bulk scope.",
    bulkFourthFormBtn: "Unlock fourth forms in current bulk scope.",
    bulkLegitMaxBtn: "Set legal max base/plus/forms in current bulk scope.",
    bulkApplyLevelsBtn: "Apply entered level/form values to current bulk scope.",
    maxBaseBtn: "Set all base upgrades to legal max.",
    refreshValidationBtn: "Run integrity and ban-risk checks again.",
    storySetAllSuperiorBtn: "Set all story treasures to Superior and clear stages.",
    storySetAllClearedBtn: "Clear all story stages without setting treasure.",
    storyResetAllBtn: "Reset all story clears and treasures to zero.",
    applyGamatotoBtn: "Apply edited Gamatoto values.",
    refreshGamatotoBtn: "Reload Gamatoto data from backend.",
    enemyUnlockVisibleBtn: "Unlock all enemies in current filtered enemy list.",
    enemyClearVisibleBtn: "Clear enemy unlocks in current filtered enemy list.",
    enemyUnlockAllBtn: "Unlock all enemy guide entries.",
    enemyClearAllBtn: "Clear all enemy guide entries.",
    enemyToggleSelectedBtn: "Toggle unlock state for the selected enemy.",
    transferDownloadBtn: "Download save data from transfer/confirmation codes and load it.",
    transferUploadBtn: "Upload loaded save to server and generate new transfer/confirmation codes.",
    transferCopyCodeBtn: "Copy the generated transfer code.",
    transferCopyPinBtn: "Copy the generated confirmation code.",
    transferUseOutputBtn: "Fill the download inputs with the generated upload codes.",
    transferBackupBtn: "Download a JSON backup of transfer history records.",
    transferClearHistoryBtn: "Clear stored transfer code history.",
    tool_catfood_topup: "Top up Catfood to 1500 only if it is lower.",
    tool_xp: "Set XP to max value.",
    tool_np: "Set NP to max value.",
    tool_battle_items: "Set battle items to max values.",
    tool_catfruit: "Set catfruit/evolution fruits to max values.",
    tool_catseyes: "Set all catseyes to max values.",
    tool_catamins: "Set all catamins to max values.",
    tool_base_materials: "Set all cat base materials to max values.",
    tool_special_skills_max: "Max all support/base upgrades.",
    tool_cat_base_cannons_max: "Max cannon development and parts.",
    tool_max_gamatoto: "Max Gamatoto values and helper setup.",
    tool_unlock_all_cats: "Unlock all cats without changing levels.",
    tool_legit_max_cats: "Apply legal max progression to all obtainable cats.",
    tool_clear_story_only: "Clear all story stages; keeps current treasures (risky).",
    tool_clear_story_superior_treasures: "Clear story and set treasures to Superior (risky).",
    tool_clear_all_maps: "Mark many map categories as cleared (risky).",
  };
  const controlTooltips = {
    safeModeToggle: "When enabled, risky operations require confirmation and can be blocked.",
    bulkOwnedOnly: "If checked, bulk cat edits only affect currently owned cats.",
    transferUploadManagedItems: "Include managed server items when uploading save data.",
    gamatoto_return_flag: "Marks expedition as returned/ready state in save data.",
    gamatoto_is_ad_present: "Controls the Gamatoto ad-present state flag in save data.",
    transferCountry: "Country code used for transfer code endpoints (en/jp/kr/tw).",
    transferGameVersion: "Optional game version override when downloading via transfer codes.",
    transferCodeInput: "Transfer code used for server download.",
    transferPinInput: "Confirmation code (PIN) paired with transfer code.",
    transferOutCode: "Generated transfer code from last successful upload.",
    transferOutPin: "Generated confirmation code from last successful upload.",
    searchInput: "Filter cats by ID or name.",
    filterSelect: "Filter cat list by owned status.",
    enemySearchInput: "Filter enemies by ID or name.",
    enemyFilterSelect: "Filter enemy guide list by state.",
  };
  Object.entries(tooltips).forEach(([id, text]) => {
    const el = $(id);
    if (el) el.title = text;
  });
  Object.entries(controlTooltips).forEach(([id, text]) => {
    const el = $(id);
    if (!el) return;
    el.title = text;
    const label = el.closest("label");
    if (label && !label.title) label.title = text;
  });
  document.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    if (checkbox.title) return;
    const label = checkbox.closest("label");
    const labelText = label ? String(label.textContent || "").replace(/\s+/g, " ").trim() : "";
    const tip = labelText ? `Toggle: ${labelText}` : "Toggle this option.";
    checkbox.title = tip;
    if (label && !label.title) label.title = tip;
  });
  document.querySelectorAll("[data-action]").forEach((btn) => {
    if (!btn.title) btn.title = btn.textContent.trim();
  });
  document.querySelectorAll(".page-btn").forEach((btn) => {
    if (!btn.title) btn.title = `Open ${btn.textContent.trim()} page`;
  });
  document.querySelectorAll(".inventory-tab").forEach((btn) => {
    if (!btn.title) btn.title = `Show ${btn.textContent.trim()} inventory`;
  });
  document.querySelectorAll(".preview-tab").forEach((btn) => {
    if (!btn.title) btn.title = `View cat ${btn.textContent.trim().toLowerCase()}`;
  });
  document.querySelectorAll("button").forEach((btn) => {
    if (!btn.title) btn.title = btn.textContent.trim();
  });
}

function switchPreviewTab(tab) {
  state.previewTab = tab;
  document.querySelectorAll(".preview-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  const stats = $("catPreviewStats");
  const sprite = $("catPreviewSprite");
  if (stats) stats.classList.toggle("hidden", tab !== "stats");
  if (sprite) sprite.classList.toggle("hidden", tab !== "sprite");
}

function getCatNumber(catId, formIndex = 0) {
  const form = Math.max(0, Math.min(3, Number(formIndex) || 0)) + 1;
  return `${String(Number(catId) + 1).padStart(3, "0")}-${form}`;
}

function updateCatSpritePreview() {
  const image = $("catSpriteImage");
  const selector = $("catPreviewForm");
  if (!image || !selector) return;
  const cat = state.selectedCat;
  if (!cat) {
    image.src = "";
    image.alt = "No cat selected";
    return;
  }
  const formIndex = Math.max(0, Math.min(3, Number(selector.value || 0)));
  const number = getCatNumber(cat.id, formIndex);
  const spriteUrl = `https://onestoppress.com/images/${number}.png`;
  const fallbackUrl = `https://onestoppress.com/images/${number}_square.png`;
  image.alt = `${cat.name} form ${formIndex + 1}`;
  image.onerror = () => {
    if (image.dataset.fallbackApplied === "1") return;
    image.dataset.fallbackApplied = "1";
    image.src = fallbackUrl;
  };
  image.dataset.fallbackApplied = "0";
  image.src = spriteUrl;
}

function setStatus(text) {
  const bar = $("statusBar");
  if (bar) bar.textContent = text;
}

function showToast(message, type = "") {
  const root = $("toastContainer");
  if (!root) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`.trim();
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function markDirty(isDirty = true) {
  state.dirty = isDirty;
  const bar = $("saveBar");
  const label = $("dirtyState");
  if (!bar || !label) return;
  bar.classList.toggle("show", isDirty);
  label.textContent = isDirty ? "Unsaved changes" : "No unsaved changes";
}

function setHistory(history = {}) {
  state.history = {
    can_undo: Boolean(history.can_undo),
    can_redo: Boolean(history.can_redo),
  };
  state.safeMode = Boolean(history.safe_mode ?? state.safeMode);
  if ($("undoBtn")) $("undoBtn").disabled = !state.history.can_undo;
  if ($("redoBtn")) $("redoBtn").disabled = !state.history.can_redo;
  if ($("safeModeToggle")) $("safeModeToggle").checked = state.safeMode;
}

function persistTransferFormState() {
  try {
    const payload = {
      country: $("transferCountry")?.value || "",
      game_version: $("transferGameVersion")?.value || "",
      transfer_code: $("transferCodeInput")?.value || "",
      confirmation_code: $("transferPinInput")?.value || "",
      out_transfer_code: $("transferOutCode")?.value || "",
      out_confirmation_code: $("transferOutPin")?.value || "",
      upload_managed_items: Boolean($("transferUploadManagedItems")?.checked),
    };
    localStorage.setItem(TRANSFER_FORM_STORAGE_KEY, JSON.stringify(payload));
  } catch (_) {}
}

function hydrateTransferFormState() {
  try {
    const raw = localStorage.getItem(TRANSFER_FORM_STORAGE_KEY);
    if (!raw) return;
    const payload = JSON.parse(raw);
    if (!payload || typeof payload !== "object") return;
    if ($("transferCountry") && payload.country) $("transferCountry").value = payload.country;
    if ($("transferGameVersion") && payload.game_version) $("transferGameVersion").value = payload.game_version;
    if ($("transferCodeInput") && payload.transfer_code) $("transferCodeInput").value = payload.transfer_code;
    if ($("transferPinInput") && payload.confirmation_code) $("transferPinInput").value = payload.confirmation_code;
    if ($("transferOutCode") && payload.out_transfer_code) $("transferOutCode").value = payload.out_transfer_code;
    if ($("transferOutPin") && payload.out_confirmation_code) $("transferOutPin").value = payload.out_confirmation_code;
    if ($("transferUploadManagedItems")) $("transferUploadManagedItems").checked = Boolean(payload.upload_managed_items ?? true);
  } catch (_) {}
}

function switchPage(page) {
  const prevPage = state.page;
  state.page = page;
  document.querySelectorAll(".page-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === page);
  });
  document.querySelectorAll(".page").forEach((el) => {
    const isActive = el.id === `page_${page}`;
    el.classList.toggle("active", isActive);
    if (isActive && prevPage !== page) {
      el.classList.remove("page-enter");
      // Force reflow so animation re-triggers when changing pages.
      void el.offsetWidth;
      el.classList.add("page-enter");
    }
  });
}

async function api(path, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const raw = await res.text();
  let data = null;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch (_) {
    const prefix = raw.slice(0, 80).replace(/\s+/g, " ").trim();
    const restartHint = `Backend returned non-JSON (${res.status}). This usually means the server needs a restart after updates.`;
    throw new Error(prefix ? `${restartHint} Response starts with: ${prefix}` : restartHint);
  }
  if (!res.ok || data.ok === false) throw new Error(data.error || `Request failed (${res.status}): ${path}`);
  return data;
}

function diffText(diff) {
  if (!diff) return "No visible changes.";
  const lines = [];
  for (const row of diff.summary_changes || []) lines.push(`${row.label}: ${row.before} -> ${row.after}`);
  if (diff.cats) lines.push(`Cats changed: ${diff.cats.changed}`);
  if (diff.story) {
    if (Number(diff.story.clear_changed)) lines.push(`Story clears delta: ${diff.story.clear_changed}`);
    if (Number(diff.story.superior_changed)) lines.push(`Superior treasures delta: ${diff.story.superior_changed}`);
  }
  return lines.length ? lines.join("\n") : "No visible changes.";
}

function confirmWithDiff(title, diff) {
  return window.confirm(`${title}\n\n${diffText(diff)}\n\nApply changes?`);
}
