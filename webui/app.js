const state = {
  page: "home",
  cats: [],
  catRows: new Map(),
  selectedIds: new Set(),
  selectedCat: null,
  lastSelectedIndex: null,
  previewTab: "stats",
  inventoryTab: "all",
  inventory: { battle_items: [], catamins: [], catseyes: [], catfruit: [], materials: [] },
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
};

const TRANSFER_FORM_STORAGE_KEY = "bcsfe_transfer_form_v1";

const $ = (id) => document.getElementById(id);
const ITEM_ICON_BASE = "https://battlecats.miraheze.org/wiki/Special:FilePath/";
const CATEGORY_FALLBACK_ICONS = {
  battle_items: "inventory",
  catamins: "inventory",
  catseyes: "catseye",
  catfruit: "catfruit",
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

function fallbackIconForCategory(category) {
  return `/webui/icons/${CATEGORY_FALLBACK_ICONS[category] || "inventory"}.svg`;
}

function resolveBaseUpgradeIconUrl(row) {
  const byId = wikiItemIconUrl(Number(row?.item_id));
  if (byId) return byId;
  if (row?.icon_url) return row.icon_url;
  return "/webui/icons/material.svg";
}

function resolveInventoryItemId(category, row) {
  const explicit = Number(row?.item_id);
  if (Number.isInteger(explicit) && explicit >= 0) return explicit;
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
  const byId = wikiItemIconUrl(resolveInventoryItemId(category, row));
  if (byId) return byId;
  if (row?.icon_url) return row.icon_url;
  return fallbackIconForCategory(category);
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
    applyResourcesBtn: "Apply the resource values in this panel.",
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
  };
  Object.entries(tooltips).forEach(([id, text]) => {
    const el = $(id);
    if (el) el.title = text;
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

function renderSummary(summary) {
  const root = $("summary");
  if (!root) return;
  root.innerHTML = "";
  if (!summary) return;
  const rows = [
    ["Path", summary.path],
    ["Inquiry", summary.inquiry_code],
    ["Country", summary.country],
    ["Game Version", summary.game_version],
    ["User Rank", summary.user_rank],
    ["Cats", `${summary.cats_unlocked}/${summary.cats_total}`],
    ["Lineups", `${summary.lineups_unlocked ?? 0}/${summary.lineups_total ?? 0}`],
    ["Catfood", summary.catfood],
    ["XP", summary.xp],
    ["NP", summary.np],
    ["Rare", summary.rare_tickets],
    ["Platinum", summary.platinum_tickets],
    ["Legend", summary.legend_tickets],
    ["Trophies", `${summary.trophies_owned ?? 0}/${summary.trophies_total ?? 0}`],
    ["Story", `${summary.story_cleared_stages ?? 0}/${summary.story_total_stages ?? 0}`],
    ["Superior", `${summary.superior_treasures ?? 0}/${summary.total_treasures ?? 0}`],
  ];
  for (const [k, v] of rows) {
    const div = document.createElement("div");
    div.innerHTML = `<span>${k}</span><span>${v ?? "-"}</span>`;
    root.appendChild(div);
  }

  const map = ["catfood", "xp", "np", "normal_tickets", "rare_tickets", "platinum_tickets", "legend_tickets", "leadership"];
  for (const key of map) {
    const el = $(`res_${key}`);
    if (el && summary[key] !== undefined) el.value = summary[key];
  }

  const transferCountry = $("transferCountry");
  const transferGameVersion = $("transferGameVersion");
  if (transferCountry && summary.country) {
    const cc = String(summary.country).toLowerCase();
    if ([...transferCountry.options].some((opt) => opt.value === cc)) transferCountry.value = cc;
  }
  if (transferGameVersion && summary.game_version && !transferGameVersion.value) {
    transferGameVersion.value = String(summary.game_version);
  }
}

function renderDashboard() {
  const root = $("dashboardCards");
  if (!root) return;
  root.innerHTML = "";
  (state.dashboard.cards || []).forEach((card, idx) => {
    const fill = Math.max(0, Math.min(100, Math.round(Number(card.percent || 0) * 100)));
    const div = document.createElement("div");
    div.className = "card";
    withReveal(div, idx);
    div.innerHTML = `
      <div class="card-title">${card.label}</div>
      <div class="card-value">${card.value}</div>
      ${card.subtitle ? `<div class="card-subtitle">${card.subtitle}</div>` : ""}
      ${Number.isFinite(Number(card.percent)) ? `<div class="mini-bar"><div class="mini-fill" style="width:${fill}%"></div></div>` : ""}
    `;
    root.appendChild(div);
  });
}

function renderProgress() {
  const root = $("progressList");
  if (!root) return;
  root.innerHTML = "";
  let rowIndex = 0;
  for (const saga of state.progress?.story?.sagas || []) {
    const row = document.createElement("div");
    row.className = "inv-row";
    withReveal(row, rowIndex++);
    row.innerHTML = `<span>${saga.name}</span><span class="muted">Clears ${saga.cleared}/${saga.clear_total} | Superior ${saga.superior}/${saga.treasure_total}</span>`;
    root.appendChild(row);
  }
  for (const chapter of state.progress?.story?.chapters || []) {
    const row = document.createElement("div");
    row.className = "inv-row";
    withReveal(row, rowIndex++);
    row.innerHTML = `<span>${chapter.name}</span><span class="muted">Clears ${chapter.cleared}/${chapter.clear_total} | Superior ${chapter.superior}/${chapter.treasure_total}</span>`;
    root.appendChild(row);
  }
}

function renderStoryTable() {
  const table = $("storyTable");
  if (!table) return;
  const body = table.querySelector("tbody");
  if (!body) return;
  body.innerHTML = "";
  (state.storyChapters || []).forEach((chapter, idx) => {
    const tr = document.createElement("tr");
    withReveal(tr, idx);
    tr.innerHTML = `
      <td>${chapter.name}</td>
      <td><input class="inv-input story-clear" type="number" min="0" max="${chapter.clear_total}" value="${chapter.cleared}" /></td>
      <td><input class="inv-input story-superior" type="number" min="0" max="${chapter.treasure_total}" value="${chapter.superior}" /></td>
      <td><button class="inv-save-btn">Apply</button></td>
    `;
    tr.querySelector(".inv-save-btn").onclick = () => {
      const clearInput = tr.querySelector(".story-clear");
      const superiorInput = tr.querySelector(".story-superior");
      applyStoryChapterEdit(
        Number(chapter.index),
        Number(clearInput?.value || 0),
        Number(superiorInput?.value || 0),
      );
    };
    body.appendChild(tr);
  });
}

function renderGamatoto() {
  const g = state.gamatoto;
  if (!g) return;
  if ($("gamatoto_level")) $("gamatoto_level").value = g.current_level ?? 1;
  if ($("gamatoto_xp")) $("gamatoto_xp").value = g.xp ?? 0;
  if ($("gamatoto_remaining_seconds")) $("gamatoto_remaining_seconds").value = Math.round(Number(g.remaining_seconds || 0));
  if ($("gamatoto_dest_id")) $("gamatoto_dest_id").value = g.dest_id ?? 0;
  if ($("gamatoto_recon_length")) $("gamatoto_recon_length").value = g.recon_length ?? 0;
  if ($("gamatoto_skin")) $("gamatoto_skin").value = g.skin ?? 0;
  if ($("gamatoto_return_flag")) $("gamatoto_return_flag").checked = Boolean(g.return_flag);
  if ($("gamatoto_is_ad_present")) $("gamatoto_is_ad_present").checked = Boolean(g.is_ad_present);
  if ($("gamatotoMeta")) $("gamatotoMeta").textContent = `Max Level: ${g.max_level ?? "-"} | Max Helpers: ${g.max_helpers ?? "-"}`;

  const table = $("gamatotoHelpersTable");
  if (!table) return;
  const body = table.querySelector("tbody");
  if (!body) return;
  body.innerHTML = "";
  (g.helpers || []).forEach((helper, idx) => {
    const tr = document.createElement("tr");
    withReveal(tr, idx);
    tr.innerHTML = `
      <td>${helper.slot}</td>
      <td><input class="inv-input gamatoto-helper-id" type="number" min="-1" value="${helper.id}" /></td>
      <td>${helper.name || "Empty"}</td>
      <td>${helper.rarity ?? 0}</td>
      <td>${helper.bonus ?? 0}</td>
      <td><button class="inv-save-btn">Apply</button></td>
    `;
    tr.querySelector(".inv-save-btn").onclick = () => {
      const input = tr.querySelector(".gamatoto-helper-id");
      applyGamatotoHelperEdit(Number(helper.slot), Number(input?.value ?? -1));
    };
    body.appendChild(tr);
  });
}

function renderBaseUpgrades() {
  const root = $("baseUpgradeList");
  if (!root) return;
  root.innerHTML = "";
  (state.baseUpgrades || []).forEach((row, idx) => {
    const div = document.createElement("div");
    div.className = "inv-row";
    withReveal(div, idx);
    const iconUrl = resolveBaseUpgradeIconUrl(row);
    div.innerHTML = `
      <span class="inv-left"><img class="item-icon" src="${iconUrl}" alt="" loading="lazy" referrerpolicy="no-referrer" /> ${row.name}</span>
      <span class="inv-edit">
        <input class="inv-input" type="number" min="1" max="${row.max_base}" value="${row.base}" />
        <input class="inv-input" type="number" min="0" max="${row.max_plus}" value="${row.plus}" />
        <button class="inv-save-btn">Apply</button>
      </span>
    `;
    applyItemIconFallback(div.querySelector(".item-icon"), "materials");
    const inputs = div.querySelectorAll(".inv-input");
    div.querySelector(".inv-save-btn").onclick = () => applyBaseUpgradeEdit(row.id, Number(inputs[0].value || 1), Number(inputs[1].value || 0));
    root.appendChild(div);
  });
}

function renderBaseCannons() {
  const root = $("baseCannonsList");
  if (!root) return;
  root.innerHTML = "";

  if (!state.baseCannons.length) {
    root.innerHTML = `<div class="inv-row"><span class="muted">No cat base cannons found in this save.</span></div>`;
    return;
  }

  const selected = Array.isArray(state.baseSelectedParts) ? state.baseSelectedParts : [0, 0, 0];
  const selectedRow = document.createElement("div");
  selectedRow.className = "inv-row";
  selectedRow.innerHTML = `
    <span class="inv-left"><strong>Selected Parts Set</strong><span class="muted">Current global part IDs</span></span>
    <span class="inv-edit">
      <input class="inv-input selected-part-input" type="number" min="0" value="${Number(selected[0] || 0)}" />
      <input class="inv-input selected-part-input" type="number" min="0" value="${Number(selected[1] || 0)}" />
      <input class="inv-input selected-part-input" type="number" min="0" value="${Number(selected[2] || 0)}" />
      <button class="inv-save-btn">Apply</button>
    </span>
  `;
  selectedRow.querySelector(".inv-save-btn").onclick = () => {
    const inputs = selectedRow.querySelectorAll(".selected-part-input");
    applyBaseSelectedPartsEdit(
      Number(inputs[0]?.value || 0),
      Number(inputs[1]?.value || 0),
      Number(inputs[2]?.value || 0),
    );
  };
  root.appendChild(selectedRow);

  (state.baseCannons || []).forEach((cannon, idx) => {
    const parts = Array.isArray(cannon.parts) ? cannon.parts : [];
    const div = document.createElement("div");
    div.className = "inv-row cannon-row";
    withReveal(div, idx);
    div.innerHTML = `
      <span class="inv-left">
        <strong>${cannon.name}</strong>
        <span class="muted">#${cannon.cannon_id} | Dev 0-${cannon.max_development ?? 3}</span>
      </span>
      <span class="inv-edit cannon-edit">
        <label class="cannon-field">Dev
          <input class="inv-input cannon-dev-input" type="number" min="0" max="${cannon.max_development ?? 3}" value="${cannon.development ?? 0}" />
        </label>
        ${parts.map((part, partIdx) => `
          <label class="cannon-field">${part.name}
            <input class="inv-input cannon-part-input" data-part-index="${partIdx}" type="number" min="0" max="${part.max_level ?? 0}" value="${part.level ?? 0}" />
          </label>
        `).join("")}
        <button class="inv-save-btn">Apply</button>
      </span>
    `;
    div.querySelector(".inv-save-btn").onclick = () => {
      const devInput = div.querySelector(".cannon-dev-input");
      const levelInputs = [...div.querySelectorAll(".cannon-part-input")];
      const levels = [0, 0, 0];
      levelInputs.forEach((input) => {
        const partIndex = Number(input.dataset.partIndex || 0);
        if (partIndex >= 0 && partIndex < 3) levels[partIndex] = Number(input.value || 0);
      });
      applyBaseCannonEdit(
        Number(cannon.cannon_id),
        Number(devInput?.value || 0),
        levels,
      );
    };
    root.appendChild(div);
  });
}

function renderValidation() {
  const root = $("validationList");
  if (!root) return;
  root.innerHTML = "";
  (state.validation || []).forEach((row, idx) => {
    const div = document.createElement("div");
    div.className = "inv-row";
    withReveal(div, idx);
    const sev = String(row.severity || "ok").toLowerCase();
    div.innerHTML = `<span class="inv-left"><span class="badge ${sev === "risk" ? "risk" : sev === "warning" ? "warn" : "on"}">${sev.toUpperCase()}</span><strong>${row.domain}</strong></span><span class="${sev === "warning" ? "muted" : ""}">${row.message}</span>`;
    root.appendChild(div);
  });
}

function renderEncyclopedias() {
  const root = $("encyclopediasList");
  if (!root) return;
  root.innerHTML = "";
  const rows = [
    ["Enemy Guide", `${state.encyclopedias?.enemy_guide?.unlocked ?? 0}/${state.encyclopedias?.enemy_guide?.total ?? 0}`],
    ["Cat Guide Claimed", `${state.encyclopedias?.cat_guide?.claimed ?? 0}/${state.encyclopedias?.cat_guide?.total ?? 0}`],
  ];
  rows.forEach(([name, value], idx) => {
    const div = document.createElement("div");
    div.className = "inv-row";
    withReveal(div, idx);
    div.innerHTML = `<span>${name}</span><span>${value}</span>`;
    root.appendChild(div);
  });
}

function renderTransferStorageInfo() {
  const el = $("transferStorageInfo");
  if (!el) return;
  const storage = state.transferStorage || {};
  const historyPath = storage.history_path || "";
  const downloadsDir = storage.downloads_dir || "";
  if (!historyPath && !downloadsDir) {
    el.textContent = "";
    return;
  }
  el.textContent = `History file: ${historyPath || "-"} | Downloaded saves: ${downloadsDir || "-"}`;
}

function renderTransferHistory() {
  const root = $("transferHistoryList");
  if (!root) return;
  root.innerHTML = "";
  renderTransferStorageInfo();
  const rows = state.transferHistory || [];
  if (!rows.length) {
    root.innerHTML = `<div class="inv-row"><span class="muted">No saved transfer codes yet.</span></div>`;
    return;
  }

  rows.forEach((row, idx) => {
    const div = document.createElement("div");
    div.className = "inv-row transfer-row";
    withReveal(div, idx);

    const rowId = String(row.id || "");
    const kind = row.kind === "upload" ? "upload" : "download";
    const kindLabel = kind === "upload" ? "Upload" : "Download";
    const cc = row.country || "";
    const version = row.game_version || "";
    const when = row.timestamp || "-";
    const transferCode = row.transfer_code || "";
    const confirmationCode = row.confirmation_code || "";
    const inquiry = row.inquiry_code || "-";
    const pathValue = row.path || "";
    const needsUpload = Boolean(row.needs_upload);
    const note = row.note || "";
    const statusClass = needsUpload ? "warn" : "on";
    const statusText = needsUpload ? "Needs Upload" : "Uploaded";

    div.innerHTML = `
      <span class="inv-left transfer-left">
        <strong>${kindLabel}</strong>
        <span class="muted">${esc(when)} | ${esc(cc || "-")} | v${esc(version || "-")}</span>
        <span class="muted">IQ: ${esc(inquiry)}</span>
        <span class="muted">Path: ${esc(pathValue || "-")}</span>
        <span class="badge ${statusClass}">${statusText}</span>
      </span>
      <span class="inv-edit transfer-history-actions">
        <div class="transfer-input-grid">
          <label>Kind
            <select class="transfer-kind-input">
              <option value="download"${kind === "download" ? " selected" : ""}>Download</option>
              <option value="upload"${kind === "upload" ? " selected" : ""}>Upload</option>
            </select>
          </label>
          <label>Country
            <input class="inv-input transfer-country-input" type="text" value="${esc(cc)}" />
          </label>
          <label>Version
            <input class="inv-input transfer-version-input" type="text" value="${esc(version)}" />
          </label>
          <label>Transfer Code
            <input class="inv-input transfer-transfer-code-input" type="text" value="${esc(transferCode)}" />
          </label>
          <label>Confirmation Code
            <input class="inv-input transfer-confirmation-code-input" type="text" value="${esc(confirmationCode)}" />
          </label>
          <label>Inquiry
            <input class="inv-input transfer-inquiry-input" type="text" value="${esc(inquiry === "-" ? "" : inquiry)}" />
          </label>
          <label>Path
            <input class="inv-input transfer-path-input" type="text" value="${esc(pathValue)}" />
          </label>
          <label>Note
            <input class="inv-input transfer-note-input" type="text" value="${esc(note)}" placeholder="Optional note" />
          </label>
          <label class="check-inline transfer-status-toggle"><input class="transfer-needs-upload-input" type="checkbox"${needsUpload ? " checked" : ""} /> Needs upload</label>
        </div>
        <div class="row-actions transfer-row-actions">
          <button class="inv-save-btn transfer-use-btn">Use</button>
          <button class="inv-save-btn transfer-save-btn">Save</button>
          <button class="inv-save-btn transfer-delete-btn">Delete</button>
        </div>
      </span>
    `;

    const useBtn = div.querySelector(".transfer-use-btn");
    const saveBtn = div.querySelector(".transfer-save-btn");
    const deleteBtn = div.querySelector(".transfer-delete-btn");

    useBtn.onclick = () => {
      const liveCode = (div.querySelector(".transfer-transfer-code-input")?.value || transferCode || "").trim();
      const livePin = (div.querySelector(".transfer-confirmation-code-input")?.value || confirmationCode || "").trim();
      const liveCountry = (div.querySelector(".transfer-country-input")?.value || cc || "").trim().toLowerCase();
      const liveVersion = (div.querySelector(".transfer-version-input")?.value || version || "").trim();
      if ($("transferCodeInput")) $("transferCodeInput").value = liveCode;
      if ($("transferPinInput")) $("transferPinInput").value = livePin;
      if ($("transferCountry") && liveCountry) $("transferCountry").value = liveCountry;
      if ($("transferGameVersion") && liveVersion) $("transferGameVersion").value = liveVersion;
      persistTransferFormState();
      setStatus("Transfer codes loaded into download fields.");
    };

    saveBtn.onclick = withErr(async () => {
      const patch = {
        kind: div.querySelector(".transfer-kind-input")?.value || kind,
        country: (div.querySelector(".transfer-country-input")?.value || "").trim().toLowerCase(),
        game_version: (div.querySelector(".transfer-version-input")?.value || "").trim(),
        transfer_code: (div.querySelector(".transfer-transfer-code-input")?.value || "").trim(),
        confirmation_code: (div.querySelector(".transfer-confirmation-code-input")?.value || "").trim(),
        inquiry_code: (div.querySelector(".transfer-inquiry-input")?.value || "").trim(),
        path: (div.querySelector(".transfer-path-input")?.value || "").trim(),
        note: (div.querySelector(".transfer-note-input")?.value || "").trim(),
        needs_upload: Boolean(div.querySelector(".transfer-needs-upload-input")?.checked),
      };
      const fallback = { timestamp: when, transfer_code: transferCode, confirmation_code: confirmationCode, kind, country: cc, game_version: version, path: pathValue, inquiry_code: inquiry === "-" ? "" : inquiry };
      const out = await api("/api/transfer/update", "POST", { id: rowId, fallback, patch });
      state.transferHistory = out.records || [];
      state.transferStorage = out.storage || state.transferStorage;
      renderTransferHistory();
      setStatus("Transfer history entry updated.");
    }, "Transfer history error");

    deleteBtn.onclick = withErr(async () => {
      if (!window.confirm("Delete this transfer history entry?")) return;
      const fallback = { timestamp: when, transfer_code: transferCode, confirmation_code: confirmationCode, kind, country: cc, game_version: version, path: pathValue, inquiry_code: inquiry === "-" ? "" : inquiry };
      const out = await api("/api/transfer/delete", "POST", { id: rowId, fallback });
      state.transferHistory = out.records || [];
      state.transferStorage = out.storage || state.transferStorage;
      renderTransferHistory();
      setStatus("Transfer history entry deleted.");
    }, "Transfer history error");

    root.appendChild(div);
  });
}

function renderEnemyGuide() {
  const table = $("enemyTable");
  if (!table) return;
  const body = table.querySelector("tbody");
  if (!body) return;
  body.innerHTML = "";

  (state.enemies || []).forEach((enemy, idx) => {
    const tr = document.createElement("tr");
    tr.className = enemy.unlocked ? "owned" : "missing";
    if (state.selectedEnemy && Number(state.selectedEnemy.id) === Number(enemy.id)) tr.classList.add("selected");
    withReveal(tr, idx);
    tr.onclick = () => {
      state.selectedEnemy = enemy;
      renderEnemyGuide();
      renderEnemyPreview();
    };
    const validTag = enemy.valid ? "" : ` <span class="muted">(invalid)</span>`;
    const canEdit = enemy.editable !== false;
    const actionLabel = canEdit ? (enemy.unlocked ? "Clear" : "Unlock") : "N/A";
    tr.innerHTML = `
      <td><img class="enemy-icon" src="${enemy.image_url || "/webui/icons/chart.svg"}" alt="" loading="lazy" referrerpolicy="no-referrer" /></td>
      <td>${enemy.id}</td>
      <td>${enemy.name}${validTag}</td>
      <td><span class="badge ${enemy.unlocked ? "on" : "off"}">${enemy.unlocked ? "Unlocked" : "Missing"}</span></td>
      <td><button class="inv-save-btn"${canEdit ? "" : " disabled"}>${actionLabel}</button></td>
    `;
    applyItemIconFallback(tr.querySelector(".enemy-icon"), "enemies");
    if (canEdit) {
      tr.querySelector(".inv-save-btn").onclick = (event) => {
        event.stopPropagation();
        applyEnemyGuideEdit(enemy.id, !enemy.unlocked);
      };
    }
    body.appendChild(tr);
  });
  renderEnemyPreview();
}

function renderEnemyPreview() {
  const root = $("enemyPreview");
  const btn = $("enemyToggleSelectedBtn");
  if (!root) return;
  const enemy = state.selectedEnemy;
  if (!enemy) {
    root.textContent = "Select an enemy to view details.";
    if (btn) btn.disabled = true;
    return;
  }
  if (btn) btn.disabled = enemy.editable === false;
  root.innerHTML = `
    <div class="enemy-preview-card">
      <div class="enemy-preview-hero">
        <img class="enemy-preview-image" src="${enemy.image_url || "/webui/icons/chart.svg"}" alt="${enemy.name}" loading="lazy" referrerpolicy="no-referrer" />
      </div>
      <div class="enemy-preview-meta">
        <div><strong>ID</strong> <span>${enemy.id}</span></div>
        <div><strong>Name</strong> <span>${enemy.name}</span></div>
        <div><strong>Status</strong> <span class="badge ${enemy.unlocked ? "on" : "off"}">${enemy.unlocked ? "Unlocked" : "Missing"}</span></div>
        <div><strong>Validity</strong> <span>${enemy.valid ? "Valid" : "Invalid"}</span></div>
        <div><strong>Editable</strong> <span>${enemy.editable !== false ? "Yes" : "No"}</span></div>
      </div>
    </div>
  `;
  const previewImage = root.querySelector(".enemy-preview-image");
  if (previewImage) applyItemIconFallback(previewImage, "enemies");
}

function renderCats() {
  const body = $("catsTable").querySelector("tbody");
  body.innerHTML = "";
  state.catRows = new Map();
  state.cats.forEach((c, idx) => {
    const tr = document.createElement("tr");
    tr.dataset.catId = String(c.id);
    tr.className = c.owned ? "owned" : "missing";
    withReveal(tr, idx);
    if (state.selectedIds.has(c.id)) tr.classList.add("selected");
    tr.onclick = (ev) => {
      if (ev.shiftKey && state.lastSelectedIndex !== null) {
        const a = Math.min(state.lastSelectedIndex, idx);
        const b = Math.max(state.lastSelectedIndex, idx);
        if (!(ev.ctrlKey || ev.metaKey)) state.selectedIds = new Set();
        state.cats.slice(a, b + 1).forEach((x) => state.selectedIds.add(x.id));
      } else if (ev.ctrlKey || ev.metaKey) {
        if (state.selectedIds.has(c.id)) state.selectedIds.delete(c.id);
        else state.selectedIds.add(c.id);
      } else {
        state.selectedIds = new Set([c.id]);
      }
      state.lastSelectedIndex = idx;
      if (!state.selectedIds.size) {
        state.selectedCat = null;
      } else if (state.selectedIds.has(c.id)) {
        state.selectedCat = c;
      } else {
        const first = [...state.selectedIds][0];
        state.selectedCat = state.cats.find((x) => x.id === first) || null;
      }
      updateSelectedRows();
      renderPreview();
      renderSelectionBadge();
      refreshSelectedCatTalents().catch(() => {});
    };
    tr.innerHTML = `
      <td><img class="cat-img" src="${c.image_url}" alt="${c.name}" loading="lazy" /></td>
      <td>${c.id}</td><td>${c.name}</td><td>${c.owned ? "Yes" : "No"}</td>
      <td>${c.base}</td><td>${c.plus}</td><td>${c.form}</td><td>${c.unlocked_forms}</td><td>${c.fourth}</td>
    `;
    body.appendChild(tr);
    state.catRows.set(c.id, tr);
  });
  attachInlineEditors();
}

function updateSelectedRows() {
  if (!state.catRows || !state.catRows.size) return;
  state.catRows.forEach((row, catId) => {
    row.classList.toggle("selected", state.selectedIds.has(Number(catId)));
  });
}

function renderSelectionBadge() {
  if ($("selectionBadge")) $("selectionBadge").textContent = `${state.selectedIds.size} selected`;
}

function renderPreview() {
  const c = state.selectedCat;
  const root = $("catPreviewStats");
  if (!c) {
    root.textContent = "Select a cat to view details.";
    const spriteForm = $("catPreviewForm");
    if (spriteForm) spriteForm.value = "0";
    updateCatSpritePreview();
    return;
  }
  const rows = [
    ["ID", c.id],
    ["Number", c.number],
    ["Name", c.name],
    ["Owned", c.owned ? "Yes" : "No"],
    ["Base", c.base],
    ["Plus", c.plus],
    ["Current Form", c.form],
    ["Unlocked Forms", c.unlocked_forms],
    ["Fourth Form", c.fourth],
    ["Talents", c.talent_count ?? 0],
  ];
  root.innerHTML = `<div class="kv-list">${rows.map(([label, value]) => `<div><strong>${label}</strong><span>${value}</span></div>`).join("")}</div>`;
  $("cat_id").value = c.id;
  $("cat_owned").value = c.owned ? "1" : "0";
  $("cat_base").value = c.base;
  $("cat_plus").value = c.plus;
  $("cat_form").value = c.form;
  $("cat_unlocked_forms").value = c.unlocked_forms;
  $("cat_fourth").value = c.fourth;
  const spriteForm = $("catPreviewForm");
  if (spriteForm) spriteForm.value = String(Math.max(0, Math.min(3, Number(c.form) || 0)));
  updateCatSpritePreview();
}

function renderCatTalents() {
  const root = $("catTalentsList");
  if (!root) return;
  root.innerHTML = "";
  if (!state.selectedCat) {
    root.innerHTML = `<div class="inv-row"><span class="muted">Select a cat to view talents.</span></div>`;
    return;
  }
  if (!state.catTalents.length) {
    root.innerHTML = `<div class="inv-row"><span class="muted">No editable talents found for this cat.</span></div>`;
    return;
  }
  state.catTalents.forEach((talent, idx) => {
    const div = document.createElement("div");
    div.className = "inv-row";
    withReveal(div, idx);
    div.innerHTML = `
      <span class="inv-left"><strong>${talent.name}</strong><span class="muted">#${talent.id}</span></span>
      <span class="inv-edit">
        <input class="inv-input" type="number" min="0" max="${talent.max_level}" value="${talent.level}" />
        <span class="muted">/ ${talent.max_level}</span>
        <button class="inv-save-btn">Apply</button>
      </span>
    `;
    const input = div.querySelector(".inv-input");
    const apply = () => applyCatTalentEdit(Number(talent.id), Number(input.value || 0));
    div.querySelector(".inv-save-btn").onclick = apply;
    input.onkeydown = (e) => {
      if (e.key === "Enter") apply();
    };
    root.appendChild(div);
  });
}

function renderInventory() {
  const root = $("inventoryList");
  root.innerHTML = "";
  const categories = ["battle_items", "catamins", "catseyes", "catfruit", "materials"];
  const labels = {
    battle_items: "Battle Items",
    catamins: "Catamins",
    catseyes: "Catseyes",
    catfruit: "Catfruit",
    materials: "Base Mats",
  };
  const selected = state.inventoryTab === "all" ? categories : [state.inventoryTab];
  let rowIndex = 0;
  for (const category of selected) {
    if (state.inventoryTab === "all") {
      const header = document.createElement("div");
      header.className = "inv-row inv-header";
      withReveal(header, rowIndex++);
      header.innerHTML = `<span class="inv-left"><img class="item-icon section-icon" src="${fallbackIconForCategory(category)}" alt="" /> <strong>${labels[category]}</strong></span><span class="muted">${(state.inventory[category] || []).length} items</span>`;
      root.appendChild(header);
    }
    for (const row of state.inventory[category] || []) {
      const div = document.createElement("div");
      div.className = "inv-row";
      withReveal(div, rowIndex++);
      const iconUrl = resolveInventoryIconUrl(category, row);
      div.innerHTML = `
        <span class="inv-left"><img class="item-icon" src="${iconUrl}" alt="" loading="lazy" referrerpolicy="no-referrer" /> ${row.name}</span>
        <span class="inv-edit"><input class="inv-input" type="number" min="0" value="${row.amount}" /><button class="inv-save-btn">Apply</button></span>
      `;
      applyItemIconFallback(div.querySelector(".item-icon"), category);
      const input = div.querySelector(".inv-input");
      const apply = () => applyInventoryEdit(category, Number(row.index), Number(input.value || 0));
      div.querySelector(".inv-save-btn").onclick = apply;
      input.onkeydown = (e) => { if (e.key === "Enter") apply(); };
      root.appendChild(div);
    }
  }
}

function renderTrophies() {
  const root = $("trophiesList");
  root.innerHTML = "";
  (state.trophies || []).forEach((row, idx) => {
    const div = document.createElement("div");
    div.className = "inv-row trophy-row";
    withReveal(div, idx);
    const icon = row.icon_url || "/webui/icons/preset.svg";
    div.innerHTML = `
      <span class="inv-left trophy-left">
        <img class="item-icon trophy-icon" src="${icon}" alt="" loading="lazy" referrerpolicy="no-referrer" />
        <span class="trophy-copy">
          <strong>${row.name}</strong>
          <span class="muted">#${row.id}${row.description ? ` - ${row.description}` : ""}</span>
        </span>
      </span>
      <span class="inv-edit">
        <span class="badge ${row.owned ? "on" : "off"}">${row.owned ? "Collected" : "Missing"}</span>
        <button class="inv-save-btn">${row.owned ? "Remove" : "Grant"}</button>
      </span>
    `;
    applyItemIconFallback(div.querySelector(".trophy-icon"), "trophies");
    div.querySelector(".inv-save-btn").onclick = () => applyTrophyEdit(row.id, !row.owned);
    root.appendChild(div);
  });
}

function activateInventoryTab(tab) {
  state.inventoryTab = tab;
  document.querySelectorAll(".inventory-tab").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  renderInventory();
}

async function refreshStatus() {
  const out = await api("/api/status");
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.currentPath = out.summary?.path || null;
  $("pathLabel").textContent = state.currentPath || "No file selected";
}

async function refreshCats() {
  const q = encodeURIComponent($("searchInput").value.trim());
  const f = encodeURIComponent($("filterSelect").value);
  const out = await api(`/api/cats?query=${q}&filter=${f}`);
  state.cats = out.cats || [];
  const ids = new Set(state.cats.map((x) => x.id));
  for (const id of [...state.selectedIds]) if (!ids.has(id)) state.selectedIds.delete(id);
  const first = [...state.selectedIds][0];
  state.selectedCat = state.cats.find((x) => x.id === first) || null;
  renderCats();
  renderPreview();
  renderSelectionBadge();
  await refreshSelectedCatTalents();
}

async function refreshInventory() {
  const out = await api("/api/inventory");
  state.inventory = {
    battle_items: out.battle_items || [],
    catamins: out.catamins || [],
    catseyes: out.catseyes || [],
    catfruit: out.catfruit || [],
    materials: out.materials || [],
  };
  renderInventory();
}

async function refreshTrophies() {
  const out = await api("/api/trophies");
  state.trophies = out.trophies || [];
  renderTrophies();
}

async function refreshSelectedCatTalents() {
  if (!state.selectedCat) {
    state.catTalents = [];
    renderCatTalents();
    return;
  }
  const out = await api(`/api/cats/talents?cat_id=${encodeURIComponent(state.selectedCat.id)}`);
  state.catTalents = out.talents || [];
  renderCatTalents();
}

async function refreshEnemyGuide() {
  const q = encodeURIComponent(($("enemySearchInput")?.value || "").trim());
  const f = encodeURIComponent($("enemyFilterSelect")?.value || "All");
  const out = await api(`/api/enemies?query=${q}&filter=${f}`);
  state.enemies = out.enemies || [];
  const selectedId = state.selectedEnemy ? Number(state.selectedEnemy.id) : null;
  state.selectedEnemy = state.enemies.find((enemy) => Number(enemy.id) === selectedId) || state.enemies[0] || null;
  if (out.enemy_guide || out.summary) {
    state.encyclopedias = {
      ...(state.encyclopedias || {}),
      enemy_guide: out.enemy_guide || state.encyclopedias?.enemy_guide,
      summary: out.summary || state.encyclopedias?.summary,
    };
  }
  renderEnemyGuide();
  renderEncyclopedias();
}

async function refreshStoryEditor() {
  const out = await api("/api/story/editor");
  state.storyChapters = out.chapters || [];
  renderStoryTable();
}

async function refreshGamatoto() {
  state.gamatoto = await api("/api/gamatoto");
  renderGamatoto();
}

async function refreshDashboard() { state.dashboard = await api("/api/dashboard"); renderDashboard(); }
async function refreshProgress() { state.progress = await api("/api/progress/story"); renderProgress(); }
async function refreshBase() {
  const [upgradesOut, cannonsOut] = await Promise.all([
    api("/api/base/upgrades"),
    api("/api/base/cannons"),
  ]);
  state.baseUpgrades = upgradesOut.upgrades || [];
  state.baseCannons = cannonsOut.cannons || [];
  state.baseSelectedParts = cannonsOut.selected_parts || [0, 0, 0];
  renderBaseUpgrades();
  renderBaseCannons();
}
async function refreshValidation() { const out = await api("/api/validation"); state.validation = out.checks || []; renderValidation(); }
async function refreshEncyclopedias() { state.encyclopedias = await api("/api/encyclopedias"); renderEncyclopedias(); }
async function refreshTransferHistory() {
  const out = await api("/api/transfer/history");
  state.transferHistory = out.records || [];
  state.transferStorage = out.storage || null;
  renderTransferHistory();
}

async function refreshAllLoaded() {
  if (!state.currentPath) return;
  const jobs = [
    refreshCats,
    refreshInventory,
    refreshTrophies,
    refreshDashboard,
    refreshProgress,
    refreshStoryEditor,
    refreshBase,
    refreshGamatoto,
    refreshValidation,
    refreshEncyclopedias,
    refreshEnemyGuide,
  ];
  const settled = await Promise.allSettled(jobs.map((job) => job()));
  const failures = settled.filter((row) => row.status === "rejected");
  if (failures.length) {
    const first = failures[0].reason?.message || "Unknown refresh error";
    showToast(`Some sections failed to refresh (${failures.length}): ${first}`, "error");
    setStatus(`Partial refresh completed with ${failures.length} errors.`);
  }
}

function withErr(fn, context) {
  return async (...args) => {
    try { await fn(...args); } catch (e) { setStatus(`${context}: ${e.message}`); showToast(`${context}: ${e.message}`, "error"); }
  };
}

async function applyInventoryEdit(category, index, amount) {
  const out = await api("/api/inventory/update", "POST", { category, index, amount });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.inventory = {
    battle_items: out.inventory?.battle_items || [],
    catamins: out.inventory?.catamins || [],
    catseyes: out.inventory?.catseyes || [],
    catfruit: out.inventory?.catfruit || [],
    materials: out.inventory?.materials || [],
  };
  renderInventory();
  await refreshValidation();
  markDirty(true);
}

async function applyTrophyEdit(id, owned) {
  const out = await api("/api/trophies/update", "POST", { id, owned });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.trophies = out.trophies || [];
  renderTrophies();
  await refreshDashboard();
  await refreshValidation();
  markDirty(true);
}

async function applyCatTalentEdit(talentId, level) {
  if (!state.selectedCat) throw new Error("Select a cat first.");
  const out = await api("/api/cats/talents/update", "POST", {
    cat_id: Number(state.selectedCat.id),
    talent_id: Number(talentId),
    level: Number(level),
  });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.catTalents = out.talents || [];
  renderCatTalents();
  await refreshValidation();
  markDirty(true);
}

async function applyStoryChapterEdit(chapter, cleared, superior) {
  const out = await api("/api/story/update", "POST", { chapter, cleared, superior });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.storyChapters = out.story || [];
  renderStoryTable();
  await refreshProgress();
  await refreshValidation();
  markDirty(true);
}

async function applyStoryBulk(action) {
  const labels = {
    set_all_superior: "set all story treasures to Superior",
    set_all_cleared: "set all story chapters to cleared",
    reset_all: "reset all story progress",
  };
  if (!window.confirm(`Confirm: ${labels[action] || action}?`)) return;
  const out = await api("/api/story/bulk", "POST", { action });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.storyChapters = out.story || [];
  renderStoryTable();
  await refreshProgress();
  await refreshValidation();
  markDirty(true);
}

async function applyGamatotoEdit() {
  const requestedLevel = Number($("gamatoto_level")?.value || 1);
  const requestedXp = Number($("gamatoto_xp")?.value || 0);
  const body = {
    remaining_seconds: Number($("gamatoto_remaining_seconds")?.value || 0),
    dest_id: Number($("gamatoto_dest_id")?.value || 0),
    recon_length: Number($("gamatoto_recon_length")?.value || 0),
    skin: Number($("gamatoto_skin")?.value || 0),
    return_flag: Boolean($("gamatoto_return_flag")?.checked),
    is_ad_present: Boolean($("gamatoto_is_ad_present")?.checked),
  };
  const baselineLevel = Number(state.gamatoto?.current_level ?? requestedLevel);
  const baselineXp = Number(state.gamatoto?.xp ?? requestedXp);
  if (requestedLevel !== baselineLevel) {
    body.level = requestedLevel;
  } else if (requestedXp !== baselineXp) {
    body.xp = requestedXp;
  }
  const out = await api("/api/gamatoto/update", "POST", body);
  state.gamatoto = out;
  renderSummary(out.summary);
  setHistory(out.history || {});
  renderGamatoto();
  await refreshValidation();
  markDirty(true);
}

async function applyGamatotoHelperEdit(slot, id) {
  const out = await api("/api/gamatoto/helper", "POST", { slot, id });
  state.gamatoto = out;
  renderSummary(out.summary);
  setHistory(out.history || {});
  renderGamatoto();
  await refreshValidation();
  markDirty(true);
}

async function applyEnemyGuideEdit(id, unlocked) {
  const out = await api("/api/enemies/update", "POST", { id, unlocked });
  renderSummary(out.summary);
  setHistory(out.history || {});
  if (state.encyclopedias) state.encyclopedias.enemy_guide = out.enemy_guide || state.encyclopedias.enemy_guide;
  await refreshEnemyGuide();
  await refreshDashboard();
  await refreshValidation();
  markDirty(true);
}

async function applyEnemyGuideBulk(action) {
  const query = ($("enemySearchInput")?.value || "").trim();
  const filter = $("enemyFilterSelect")?.value || "All";
  const scopeLabel = action.includes("filtered")
    ? `visible enemies (filter: ${filter}${query ? `, query: "${query}"` : ""})`
    : "all enemies";
  if (!window.confirm(`Apply "${action}" to ${scopeLabel}?`)) return;
  const out = await api("/api/enemies/bulk", "POST", { action, query, filter });
  renderSummary(out.summary);
  setHistory(out.history || {});
  if (state.encyclopedias) state.encyclopedias.enemy_guide = out.enemy_guide || state.encyclopedias.enemy_guide;
  await refreshEnemyGuide();
  await refreshDashboard();
  await refreshValidation();
  markDirty(true);
}

async function runBulk(payload, label) {
  const ids = $("bulkScope")?.value === "all" ? [] : state.cats.map((c) => c.id);
  const body = { ...payload, ids, owned_only: Boolean($("bulkOwnedOnly")?.checked) };
  const preview = await api("/api/cats/bulk/preview", "POST", body);
  if (!confirmWithDiff(`Bulk action: ${label}`, preview.diff)) return;
  const out = await api("/api/cats/bulk", "POST", body);
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshCats();
  await refreshDashboard();
  await refreshValidation();
  markDirty(true);
}

async function applyOperation(key, label) {
  const preview = await api("/api/op/preview", "POST", { key });
  if (!confirmWithDiff(label, preview.diff)) return;
  const out = await api("/api/op", "POST", { key, allow_risky: !state.safeMode });
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshAllLoaded();
  markDirty(true);
}

async function applyBaseUpgradeEdit(id, base, plus) {
  const out = await api("/api/base/update", "POST", { id, base, plus });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.baseUpgrades = out.base || [];
  renderBaseUpgrades();
  await refreshValidation();
  markDirty(true);
}

async function applyBaseSelectedPartsEdit(part0, part1, part2) {
  const out = await api("/api/base/cannons/update", "POST", {
    selected_parts: [part0, part1, part2],
  });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.baseCannons = out.cannons || [];
  state.baseSelectedParts = out.selected_parts || [0, 0, 0];
  renderBaseCannons();
  await refreshValidation();
  markDirty(true);
}

async function applyBaseCannonEdit(cannonId, development, levels) {
  const out = await api("/api/base/cannons/update", "POST", {
    cannon_id: Number(cannonId),
    development: Number(development),
    levels: Array.isArray(levels) ? levels.slice(0, 3).map((value) => Number(value || 0)) : [0, 0, 0],
  });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.baseCannons = out.cannons || [];
  state.baseSelectedParts = out.selected_parts || [0, 0, 0];
  renderBaseCannons();
  await refreshValidation();
  markDirty(true);
}

async function applyTransferDownload() {
  const body = {
    country: ($("transferCountry")?.value || "en").trim().toLowerCase(),
    game_version: $("transferGameVersion")?.value?.trim() || "",
    transfer_code: $("transferCodeInput")?.value?.trim() || "",
    confirmation_code: $("transferPinInput")?.value?.trim() || "",
  };
  if (!body.transfer_code || !body.confirmation_code) {
    throw new Error("Enter transfer and confirmation codes first.");
  }
  const out = await api("/api/transfer/download", "POST", body);
  state.currentPath = out.path || null;
  $("pathLabel").textContent = state.currentPath || "No file selected";
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.transferHistory = out.records || [];
  state.transferStorage = out.storage || state.transferStorage;
  renderTransferHistory();
  if ($("transferDownloadMeta")) {
    $("transferDownloadMeta").textContent = `Downloaded and loaded: ${out.path || "-"}`;
  }
  persistTransferFormState();
  await refreshAllLoaded();
  markDirty(false);
  setStatus("Transfer download complete. Save loaded.");
}

async function applyTransferUpload() {
  const body = {
    upload_managed_items: Boolean($("transferUploadManagedItems")?.checked),
  };
  const out = await api("/api/transfer/upload", "POST", body);
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.transferHistory = out.records || [];
  state.transferStorage = out.storage || state.transferStorage;
  renderTransferHistory();
  if ($("transferOutCode")) $("transferOutCode").value = out.transfer_code || "";
  if ($("transferOutPin")) $("transferOutPin").value = out.confirmation_code || "";
  persistTransferFormState();
  const linked = Number(out.linked_downloads || 0);
  setStatus(linked > 0 ? `Upload complete. Linked ${linked} downloaded account(s) as uploaded.` : "Upload complete. New transfer codes generated.");
}

async function clearTransferHistory() {
  const out = await api("/api/transfer/clear", "POST", {});
  state.transferHistory = out.records || [];
  state.transferStorage = out.storage || state.transferStorage;
  renderTransferHistory();
  setStatus("Saved transfer code history cleared.");
}

async function downloadTransferHistoryBackup() {
  const out = await api("/api/transfer/backup");
  const backup = out.backup || { records: [] };
  const filename = out.filename || `transfer_history_backup_${Date.now()}.json`;
  const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
  const url = window.URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    window.URL.revokeObjectURL(url);
  }
  state.transferStorage = out.storage || state.transferStorage;
  renderTransferStorageInfo();
  setStatus(`Transfer history backup downloaded (${(backup.records || []).length} records).`);
}

async function copyTransferField(fieldId, label) {
  const value = ($(fieldId)?.value || "").trim();
  if (!value) throw new Error(`No ${label.toLowerCase()} to copy.`);
  await navigator.clipboard.writeText(value);
  setStatus(`${label} copied.`);
}

function bindEvents() {
  document.querySelectorAll(".page-btn").forEach((btn) => {
    btn.onclick = () => switchPage(btn.dataset.page);
  });

  $("loadBtn").onclick = withErr(loadSave, "Load error");
  $("saveBtn").onclick = withErr(saveAs, "Save error");
  $("saveBarSaveBtn").onclick = withErr(saveAs, "Save error");
  $("refreshBtn").onclick = withErr(async () => { await refreshStatus(); await refreshAllLoaded(); setStatus("Refreshed."); }, "Refresh error");
  $("revertBtn").onclick = withErr(revertCurrent, "Revert error");
  $("undoBtn").onclick = withErr(undo, "Undo error");
  $("redoBtn").onclick = withErr(redo, "Redo error");
  $("syncBtn").onclick = withErr(syncMyGamatoto, "Sync error");
  $("applyResourcesBtn").onclick = withErr(applyResourceEdits, "Resources error");
  $("maxGamatotoBtn").onclick = withErr(() => applyOperation("max_gamatoto", "Max Gamatoto"), "Operation error");
  $("maxBaseBtn").onclick = withErr(() => applyOperation("special_skills_max", "Max Base Upgrades"), "Operation error");
  $("refreshValidationBtn").onclick = withErr(refreshValidation, "Validation error");
  $("applyCatEditBtn").onclick = withErr(applySelectedCatEdit, "Cat edit error");
  $("bulkUnlockBtn").onclick = withErr(() => runBulk({ unlock: true }, "Unlock"), "Bulk error");
  $("bulkTrueFormBtn").onclick = withErr(() => runBulk({ true_form: true }, "True Forms"), "Bulk error");
  $("bulkFourthFormBtn").onclick = withErr(() => runBulk({ fourth_form: true }, "4th Forms"), "Bulk error");
  $("bulkLegitMaxBtn").onclick = withErr(() => runBulk({ legit_max: true }, "Legit Max"), "Bulk error");
  $("bulkApplyLevelsBtn").onclick = withErr(applyBulkLevelsForms, "Bulk error");
  if ($("storySetAllSuperiorBtn")) $("storySetAllSuperiorBtn").onclick = withErr(() => applyStoryBulk("set_all_superior"), "Story error");
  if ($("storySetAllClearedBtn")) $("storySetAllClearedBtn").onclick = withErr(() => applyStoryBulk("set_all_cleared"), "Story error");
  if ($("storyResetAllBtn")) $("storyResetAllBtn").onclick = withErr(() => applyStoryBulk("reset_all"), "Story error");
  if ($("applyGamatotoBtn")) $("applyGamatotoBtn").onclick = withErr(applyGamatotoEdit, "Gamatoto error");
  if ($("refreshGamatotoBtn")) $("refreshGamatotoBtn").onclick = withErr(refreshGamatoto, "Gamatoto error");
  if ($("enemyUnlockVisibleBtn")) $("enemyUnlockVisibleBtn").onclick = withErr(() => applyEnemyGuideBulk("unlock_filtered"), "Enemy guide error");
  if ($("enemyClearVisibleBtn")) $("enemyClearVisibleBtn").onclick = withErr(() => applyEnemyGuideBulk("clear_filtered"), "Enemy guide error");
  if ($("enemyUnlockAllBtn")) $("enemyUnlockAllBtn").onclick = withErr(() => applyEnemyGuideBulk("unlock_all"), "Enemy guide error");
  if ($("enemyClearAllBtn")) $("enemyClearAllBtn").onclick = withErr(() => applyEnemyGuideBulk("clear_all"), "Enemy guide error");
  if ($("enemyToggleSelectedBtn")) $("enemyToggleSelectedBtn").onclick = withErr(async () => {
    if (!state.selectedEnemy) throw new Error("Select an enemy first.");
    if (state.selectedEnemy.editable === false) throw new Error("Selected enemy cannot be edited.");
    await applyEnemyGuideEdit(state.selectedEnemy.id, !state.selectedEnemy.unlocked);
  }, "Enemy guide error");
  if ($("transferDownloadBtn")) $("transferDownloadBtn").onclick = withErr(applyTransferDownload, "Transfer download error");
  if ($("transferUploadBtn")) $("transferUploadBtn").onclick = withErr(applyTransferUpload, "Transfer upload error");
  if ($("transferCopyCodeBtn")) $("transferCopyCodeBtn").onclick = withErr(() => copyTransferField("transferOutCode", "Transfer code"), "Copy error");
  if ($("transferCopyPinBtn")) $("transferCopyPinBtn").onclick = withErr(() => copyTransferField("transferOutPin", "Confirmation code"), "Copy error");
  if ($("transferUseOutputBtn")) $("transferUseOutputBtn").onclick = withErr(async () => {
    const code = ($("transferOutCode")?.value || "").trim();
    const pin = ($("transferOutPin")?.value || "").trim();
    if (!code || !pin) throw new Error("Upload first to generate codes.");
    if ($("transferCodeInput")) $("transferCodeInput").value = code;
    if ($("transferPinInput")) $("transferPinInput").value = pin;
    persistTransferFormState();
    setStatus("Upload codes copied into download fields.");
  }, "Transfer error");
  if ($("transferBackupBtn")) $("transferBackupBtn").onclick = withErr(downloadTransferHistoryBackup, "Transfer backup error");
  if ($("transferClearHistoryBtn")) $("transferClearHistoryBtn").onclick = withErr(async () => {
    if (!window.confirm("Clear all saved transfer codes history?")) return;
    await clearTransferHistory();
    persistTransferFormState();
  }, "Transfer error");
  $("safeModeToggle").onchange = withErr(async (e) => {
    const out = await api("/api/safe_mode", "POST", { enabled: Boolean(e.target.checked) });
    setHistory(out.history || {});
  }, "Safe mode error");

  document.querySelectorAll("[data-action]").forEach((btn) => btn.onclick = withErr(() => doCatAction(btn.dataset.action), "Cat action error"));
  document.querySelectorAll(".inventory-tab").forEach((btn) => btn.onclick = () => activateInventoryTab(btn.dataset.tab));

  $("searchInput").oninput = () => {
    if (state.searchTimer) clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => refreshCats().catch(() => {}), 250);
  };
  $("filterSelect").onchange = () => refreshCats().catch(() => {});
  if ($("catPreviewForm")) $("catPreviewForm").onchange = () => updateCatSpritePreview();
  document.querySelectorAll(".preview-tab").forEach((btn) => {
    btn.onclick = () => switchPreviewTab(btn.dataset.tab);
  });
  if ($("enemySearchInput")) {
    $("enemySearchInput").oninput = () => {
      if (state.enemySearchTimer) clearTimeout(state.enemySearchTimer);
      state.enemySearchTimer = setTimeout(() => refreshEnemyGuide().catch(() => {}), 250);
    };
  }
  if ($("enemyFilterSelect")) $("enemyFilterSelect").onchange = () => refreshEnemyGuide().catch(() => {});
  ["transferCountry", "transferGameVersion", "transferCodeInput", "transferPinInput", "transferOutCode", "transferOutPin", "transferUploadManagedItems"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    const isSelect = String(el.tagName || "").toLowerCase() === "select";
    const eventName = el.type === "checkbox" || isSelect ? "change" : "input";
    el.addEventListener(eventName, () => persistTransferFormState());
  });

  window.addEventListener("beforeunload", (e) => {
    if (state.dirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
  window.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.key.toLowerCase() === "s") {
      e.preventDefault();
      saveAs().catch(() => {});
    } else if (e.ctrlKey && e.key.toLowerCase() === "k") {
      e.preventDefault();
      switchPage("cats");
      $("searchInput").focus();
      $("searchInput").select();
    } else if (!e.ctrlKey && !e.metaKey && e.key === "/") {
      e.preventDefault();
      switchPage("cats");
      $("searchInput").focus();
      $("searchInput").select();
    } else if (e.key === "Escape") {
      state.selectedIds = new Set();
      state.selectedCat = null;
      updateSelectedRows();
      renderPreview();
      renderCatTalents();
      renderSelectionBadge();
    }
  });
}

function attachInlineEditors() {
  $("catsTable").querySelectorAll("tbody tr").forEach((row) => {
    const cells = row.querySelectorAll("td");
    const id = Number(cells[1].textContent);
    [["base", 4], ["plus", 5], ["form", 6]].forEach(([key, idx]) => {
      cells[idx].ondblclick = async () => {
        if (cells[idx].querySelector("input")) return;
        const input = document.createElement("input");
        input.type = "number";
        input.value = cells[idx].textContent;
        cells[idx].textContent = "";
        cells[idx].appendChild(input);
        input.focus();
        let committed = false;
        const commit = async () => {
          if (committed) return;
          committed = true;
          const payload = { id };
          payload[key] = Number(input.value || 0);
          const out = await api("/api/cats/update", "POST", payload);
          renderSummary(out.summary);
          setHistory(out.history || {});
          await refreshCats();
          await refreshDashboard();
          await refreshValidation();
          markDirty(true);
        };
        input.onkeydown = (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit().catch(() => {});
          }
        };
        input.onblur = () => commit().catch(() => {});
      };
    });
  });
}

async function loadSave() {
  if (state.dirty && !window.confirm("Discard unsaved changes and load another save?")) return;
  const picked = await api("/api/pick_path");
  const out = await api("/api/load", "POST", { path: picked.path });
  state.currentPath = picked.path;
  $("pathLabel").textContent = picked.path;
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshAllLoaded();
  markDirty(false);
  setStatus("Save loaded.");
}

async function saveAs() {
  const picked = await api("/api/pick_save_path");
  const out = await api("/api/save", "POST", { path: picked.path });
  state.currentPath = out.path;
  $("pathLabel").textContent = out.path;
  markDirty(false);
  setStatus(`Saved: ${out.path}`);
}

async function revertCurrent() {
  if (!state.currentPath) throw new Error("No loaded path to revert.");
  if (!window.confirm("Revert all unsaved changes by reloading current save?")) return;
  const out = await api("/api/load", "POST", { path: state.currentPath });
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshAllLoaded();
  markDirty(false);
}

async function undo() {
  const out = await api("/api/undo", "POST", {});
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshAllLoaded();
  markDirty(true);
}

async function redo() {
  const out = await api("/api/redo", "POST", {});
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshAllLoaded();
  markDirty(true);
}

async function syncMyGamatoto() {
  const out = await api("/api/sync_mygamatoto", "POST", {});
  await refreshCats();
  setStatus(`Synced MyGamatoto: ${out.count} cats.`);
}

async function applyResourceEdits() {
  const out = await api("/api/resources", "POST", {
    catfood: Number($("res_catfood").value || 0),
    xp: Number($("res_xp").value || 0),
    np: Number($("res_np").value || 0),
    normal_tickets: Number($("res_normal_tickets").value || 0),
    rare_tickets: Number($("res_rare_tickets").value || 0),
    platinum_tickets: Number($("res_platinum_tickets").value || 0),
    legend_tickets: Number($("res_legend_tickets").value || 0),
    leadership: Number($("res_leadership").value || 0),
  });
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshDashboard();
  await refreshValidation();
  markDirty(true);
}

async function applySelectedCatEdit() {
  if (!$("cat_id").value) throw new Error("Select a cat first.");
  const out = await api("/api/cats/update", "POST", {
    id: Number($("cat_id").value),
    owned: $("cat_owned").value === "1",
    base: Number($("cat_base").value || 1),
    plus: Number($("cat_plus").value || 0),
    form: Number($("cat_form").value || 0),
    unlocked_forms: Number($("cat_unlocked_forms").value || 0),
    fourth: Number($("cat_fourth").value || 0),
  });
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshCats();
  await refreshDashboard();
  await refreshValidation();
  markDirty(true);
}

async function doCatAction(action) {
  if (!state.selectedIds.size) throw new Error("Select cats first.");
  const out = await api("/api/cats/action", "POST", { action, ids: [...state.selectedIds] });
  renderSummary(out.summary);
  setHistory(out.history || {});
  await refreshCats();
  await refreshDashboard();
  await refreshValidation();
  markDirty(true);
}

async function applyBulkLevelsForms() {
  const payload = {};
  const base = $("bulkBase").value.trim();
  const plus = $("bulkPlus").value.trim();
  const form = $("bulkForm").value.trim();
  const unlocked = $("bulkUnlockedForms").value.trim();
  if (base !== "") payload.base = Number(base);
  if (plus !== "") payload.plus = Number(plus);
  if (form !== "") payload.form = Number(form);
  if (unlocked !== "") payload.unlocked_forms = Number(unlocked);
  if (!Object.keys(payload).length) throw new Error("Enter at least one bulk value.");
  await runBulk(payload, "Levels/Forms update");
}

const PRESET_HELP = {
  human_max: {
    summary: "Human-max progression. Aims for strong but plausible progression with Superior story treasures.",
    operations: [
      "catfood_topup: Raises Catfood to 1500 only if it is below 1500.",
      "xp / normal_tickets / np / leadership / battle_items: Sets these to their max values.",
      "gold_tickets_200: Sets Rare (gold) tickets to 200.",
      "catfruit / base_materials / catseyes / catamins / labyrinth_medals / treasure_chests: Sets each category to max values.",
      "special_skills_max + cat_base_cannons_max: Maxes all base upgrades, cannon development, and cannon part levels.",
      "legit_max_cats: Unlocks all cats, applies legal max base/plus, unlocks true+4th forms where valid, maxes talents.",
      "clear_story_superior_treasures: Clears story and sets treasures to Superior tier (3).",
      "max_gamatoto: Maxes Gamatoto XP/helpers, sets return flag, sets Ototo engineers max.",
      "clear_all_maps: Marks many map categories and related progress as cleared.",
    ],
    notes: [
      "This preset includes map/story progression edits and can be considered high-impact.",
    ],
  },
  full_legit_max: {
    summary: "Full legit max progression while keeping your current treasure levels.",
    operations: [
      "catfood_topup / xp / normal_tickets / np / leadership / battle_items: Applies progression/resource max operations.",
      "gold_tickets_200: Sets Rare (gold) tickets to 200.",
      "catseyes / catamins / catfruit / base_materials / labyrinth_medals / treasure_chests: Maxes these item categories.",
      "special_skills_max + cat_base_cannons_max + legit_max_cats + max_gamatoto: Applies max progression on units/base/gamatoto.",
      "clear_story_only: Clears story stages without forcing treasure values.",
      "clear_all_maps: Applies broad map clear-state updates.",
    ],
    notes: [
      "Compared to Human Max, this keeps existing story treasure tier values unchanged.",
    ],
  },
  safe_resources: {
    summary: "Safer resource-focused max preset with no broad story/map clear operation.",
    operations: [
      "xp / normal_tickets / np / leadership / battle_items: Maxes core economy items.",
      "catseyes / catamins / labyrinth_medals / treasure_chests: Maxes these inventories.",
    ],
    notes: [
      "This preset intentionally avoids all-cat max, map-clear, and story-clear operations.",
    ],
  },
  starter_boost: {
    summary: "Starter boost for fast early progression.",
    operations: [
      "catfood: Sets Catfood to max value.",
      "xp: Sets XP to max value.",
      "np: Sets NP to max value.",
      "leadership: Sets Leadership to max value.",
      "battle_items: Maxes battle item counts.",
    ],
    notes: [
      "This is compact and fast, but Catfood/XP/NP values are still large edits.",
    ],
  },
};

function showPresetHelp(presetId, label) {
  const info = PRESET_HELP[presetId];
  if (!info) {
    window.alert(`No detailed help is available for preset "${label}".`);
    return;
  }
  const parts = [
    `${label}`,
    "",
    info.summary,
    "",
    "What it applies:",
    ...info.operations.map((line, idx) => `${idx + 1}. ${line}`),
  ];
  if (info.notes?.length) {
    parts.push("", "Notes:", ...info.notes.map((line, idx) => `${idx + 1}. ${line}`));
  }
  window.alert(parts.join("\n"));
}

function presetButtons() {
  const root = $("presets");
  root.innerHTML = "";
  const presets = [
    ["human_max", "Human Max (Recommended)"],
    ["full_legit_max", "Full Legit Max"],
    ["safe_resources", "Safe Resources Max"],
    ["starter_boost", "Starter Boost"],
  ];
  presets.forEach(([id, label]) => {
    const row = document.createElement("div");
    row.className = "preset-row";
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.onclick = withErr(async () => {
      const preview = await api("/api/preset/preview", "POST", { preset: id });
      if (!confirmWithDiff(`Preset: ${label}`, preview.diff)) return;
      const out = await api("/api/preset", "POST", { preset: id, allow_risky: !state.safeMode });
      renderSummary(out.summary);
      setHistory(out.history || {});
      await refreshAllLoaded();
      markDirty(true);
      showToast(`${label} applied`, out.failed?.length ? "error" : "ok");
    }, "Preset error");
    const helpBtn = document.createElement("button");
    helpBtn.className = "preset-help-btn";
    helpBtn.textContent = "?";
    helpBtn.title = `Show detailed explanation for ${label}`;
    helpBtn.onclick = () => showPresetHelp(id, label);
    row.appendChild(btn);
    row.appendChild(helpBtn);
    root.appendChild(row);
  });
}

async function init() {
  bindEvents();
  bindStaticIconFallbacks();
  setButtonTooltips();
  hydrateTransferFormState();
  presetButtons();
  switchPage(state.page);
  switchPreviewTab(state.previewTab);
  $("pathLabel").textContent = "No file selected";
  activateInventoryTab(state.inventoryTab);
  renderCatTalents();
  renderTransferHistory();
  markDirty(false);
  await refreshStatus();
  await refreshTransferHistory();
  await refreshAllLoaded();
}

init().catch((e) => {
  setStatus(`Init error: ${e.message}`);
  showToast(`Init error: ${e.message}`, "error");
});
