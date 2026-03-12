// Event wiring and UI bootstrap helpers
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
  if ($("applyPlaytimeBtn")) $("applyPlaytimeBtn").onclick = withErr(applyPlaytimeEdit, "Playtime error");
  if ($("add24hBtn")) $("add24hBtn").onclick = withErr(() => addPlaytimeHours(24), "Playtime error");
  $("maxGamatotoBtn").onclick = withErr(() => applyOperation("max_gamatoto", "Max Gamatoto"), "Operation error");
  $("maxBaseBtn").onclick = withErr(() => applyOperation("special_skills_max", "Max Base Upgrades"), "Operation error");
  $("refreshValidationBtn").onclick = withErr(refreshValidation, "Validation error");
  Object.entries(TOOL_OPERATIONS).forEach(([id, config]) => {
    const btn = $(id);
    if (!btn) return;
    btn.onclick = withErr(() => applyOperation(config.key, config.label), "Tool error");
  });
  $("applyCatEditBtn").onclick = withErr(applySelectedCatEdit, "Cat edit error");
  [
    "cat_owned",
    "cat_base",
    "cat_plus",
    "cat_form",
    "cat_unlocked_forms",
    "cat_fourth",
  ].forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      applySelectedCatEdit().catch(() => {});
    });
  });
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
  if ($("useLatestTransferVersionBtn")) $("useLatestTransferVersionBtn").onclick = withErr(useLatestTransferVersion, "Version error");
  if ($("updateSaveVersionBtn")) $("updateSaveVersionBtn").onclick = withErr(updateLoadedSaveVersionToLatest, "Version error");
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
  ["playtime_hours", "playtime_minutes", "playtime_seconds"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        applyPlaytimeEdit().catch(() => {});
      }
    });
  });
  ["transferCountry", "transferGameVersion", "transferCodeInput", "transferPinInput", "transferOutCode", "transferOutPin", "transferUploadManagedItems"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    const isSelect = String(el.tagName || "").toLowerCase() === "select";
    const eventName = el.type === "checkbox" || isSelect ? "change" : "input";
    el.addEventListener(eventName, () => {
      persistTransferFormState();
      if (id === "transferCountry") {
        refreshGameVersionStatus().catch(() => {});
      }
    });
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
  state.gameVersionWarningKey = null;
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

async function applyPlaytimeEdit() {
  if ($("applyPlaytimeBtn")?.disabled) {
    throw new Error("Playtime endpoint unavailable. Restart backend first.");
  }
  try {
    const out = await api("/api/playtime/update", "POST", {
      hours: Number($("playtime_hours")?.value || 0),
      minutes: Number($("playtime_minutes")?.value || 0),
      seconds: Number($("playtime_seconds")?.value || 0),
    });
    renderSummary(out.summary);
    setHistory(out.history || {});
    state.playtime = {
      hours: Number(out.hours || 0),
      minutes: Number(out.minutes || 0),
      seconds: Number(out.seconds || 0),
      frames: Number(out.frames || 0),
    };
    renderPlaytime();
    setStatus("Playtime updated.");
    markDirty(true);
  } catch (error) {
    const message = String(error?.message || error || "");
    const missingEndpoint = message.includes("404") && (message.includes("/api/playtime") || message.includes("Not Found"));
    if (missingEndpoint) {
      if ($("playtimeMeta")) $("playtimeMeta").textContent = "Playtime editor unavailable on current backend. Restart backend to enable.";
      if ($("applyPlaytimeBtn")) $("applyPlaytimeBtn").disabled = true;
      if ($("add24hBtn")) $("add24hBtn").disabled = true;
      throw new Error("Playtime endpoint unavailable. Restart backend first.");
    }
    throw error;
  }
}

async function addPlaytimeHours(deltaHours) {
  const baseHours = Number(state.playtime?.hours ?? $("playtime_hours")?.value ?? 0);
  const nextHours = Math.max(0, baseHours + Number(deltaHours || 0));
  if ($("playtime_hours")) $("playtime_hours").value = String(nextHours);
  await applyPlaytimeEdit();
}

function getSelectedCatIdForEditor() {
  const inputId = Number($("cat_id")?.value || NaN);
  if (Number.isFinite(inputId)) return inputId;
  if (!state.selectedCat) return NaN;
  return Number(state.selectedCat.id);
}


function getCatEditorValues() {
  return {
    owned: $("cat_owned").value === "1",
    base: Number($("cat_base").value || 1),
    plus: Number($("cat_plus").value || 0),
    form: Number($("cat_form").value || 0),
    unlocked_forms: Number($("cat_unlocked_forms").value || 0),
    fourth: Number($("cat_fourth").value || 0),
  };
}


function isSelectedCatEditorDirty() {
  const cat = state.selectedCat;
  if (!cat) return false;
  const editorId = getSelectedCatIdForEditor();
  if (!Number.isFinite(editorId)) return false;
  if (editorId !== Number(cat.id)) return false;
  const editorValues = getCatEditorValues();
  return (
    Boolean(cat.owned) !== editorValues.owned
    || Number(cat.base) !== editorValues.base
    || Number(cat.plus) !== editorValues.plus
    || Number(cat.form) !== editorValues.form
    || Number(cat.unlocked_forms) !== editorValues.unlocked_forms
    || Number(cat.fourth) !== editorValues.fourth
  );
}


async function maybeApplyCatPreviewEditsBeforeSelection(nextCatId) {
  const currentId = getSelectedCatIdForEditor();
  const targetId = Number(nextCatId);
  if (!Number.isFinite(currentId) || !Number.isFinite(targetId)) return true;
  if (currentId === targetId) return true;
  if (!isSelectedCatEditorDirty()) return true;
  const shouldApply = window.confirm(
    "Apply current cat edits before switching to another cat?",
  );
  if (!shouldApply) {
    return window.confirm(
      "Discard current cat edits and switch selection?",
    );
  }
  try {
    await applySelectedCatEdit();
    return true;
  } catch (error) {
    const message = String(error?.message || error || "Cat edit failed.");
    setStatus(`Cat edit error: ${message}`);
    showToast(`Cat edit error: ${message}`, "error");
    return false;
  }
}


async function applySelectedCatEdit() {
  const selectedId = getSelectedCatIdForEditor();
  if (!Number.isFinite(selectedId)) throw new Error("Selected cat id is invalid.");
  const out = await api("/api/cats/update", "POST", {
    id: selectedId,
    ...getCatEditorValues(),
  });
  renderSummary(out.summary);
  setHistory(out.history || {});
  state.selectedIds = new Set([selectedId]);
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
      "catfruit_500 / talent_orbs_s_50 / base_materials / catseyes / catamins / labyrinth_medals / treasure_chests: Sets catfruit to 500 each, adds only S-grade orb types at 50 each, and maxes the other categories.",
      "special_skills_max + cat_base_cannons_max: Maxes all base upgrades, cannon development, and cannon part levels.",
      "legit_max_cats: Unlocks all obtainable cats, applies legal max base/plus, unlocks true+4th forms where valid, maxes talents.",
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
      "special_skills_max + cat_base_cannons_max + legit_max_cats + max_gamatoto: Applies max progression on obtainable units/base/gamatoto.",
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

async function initUI() {
  bindEvents();
  bindStaticIconFallbacks();
  setButtonTooltips();
  hydrateTransferFormState();
  presetButtons();
  switchPage(state.page);
  switchPreviewTab(state.previewTab);
  $("pathLabel").textContent = "No file selected";
  activateInventoryTab(state.inventoryTab);
  renderPlaytime();
  renderCatTalents();
  renderTransferHistory();
  markDirty(false);
  await refreshStatus();
  await refreshTransferHistory();
  await refreshAllLoaded();
}
