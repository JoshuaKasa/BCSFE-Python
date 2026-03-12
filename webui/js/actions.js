// API adapters and mutation actions
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
    talent_orbs: out.talent_orbs || [],
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
async function refreshPlaytime() {
  try {
    const out = await api("/api/playtime");
    state.playtime = {
      hours: Number(out.hours || 0),
      minutes: Number(out.minutes || 0),
      seconds: Number(out.seconds || 0),
      frames: Number(out.frames || 0),
    };
    renderPlaytime();
    if ($("applyPlaytimeBtn")) $("applyPlaytimeBtn").disabled = false;
    if ($("add24hBtn")) $("add24hBtn").disabled = false;
  } catch (error) {
    const message = String(error?.message || error || "");
    const missingEndpoint = message.includes("404") && (message.includes("/api/playtime") || message.includes("Not Found"));
    if (!missingEndpoint) throw error;
    state.playtime = null;
    renderPlaytime();
    if ($("playtimeMeta")) $("playtimeMeta").textContent = "Playtime editor unavailable on current backend. Restart backend to enable.";
    if ($("applyPlaytimeBtn")) $("applyPlaytimeBtn").disabled = true;
    if ($("add24hBtn")) $("add24hBtn").disabled = true;
  }
}
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
    refreshPlaytime,
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
    talent_orbs: out.inventory?.talent_orbs || [],
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
  const transferDownloadBtn = $("transferDownloadBtn");
  const transferUploadBtn = $("transferUploadBtn");
  const transferDownloadMeta = $("transferDownloadMeta");
  const transferUploadMeta = $("transferUploadMeta");
  if (transferDownloadBtn && !transferDownloadBtn.dataset.defaultLabel) {
    transferDownloadBtn.dataset.defaultLabel = transferDownloadBtn.textContent;
  }
  if (transferUploadBtn && !transferUploadBtn.dataset.defaultLabel) {
    transferUploadBtn.dataset.defaultLabel = transferUploadBtn.textContent;
  }
  if (transferDownloadBtn) {
    transferDownloadBtn.disabled = true;
    transferDownloadBtn.textContent = "Downloading...";
  }
  if (transferUploadBtn) transferUploadBtn.disabled = true;
  if (transferDownloadMeta) transferDownloadMeta.textContent = "Downloading and loading save data...";
  if (transferUploadMeta) transferUploadMeta.textContent = "";
  setStatus("Downloading save data from server...");
  try {
    const out = await api("/api/transfer/download", "POST", body);
    state.currentPath = out.path || null;
    $("pathLabel").textContent = state.currentPath || "No file selected";
    renderSummary(out.summary);
    setHistory(out.history || {});
    state.transferHistory = out.records || [];
    state.transferStorage = out.storage || state.transferStorage;
    renderTransferHistory();
    if (transferDownloadMeta) {
      transferDownloadMeta.textContent = `Downloaded and loaded: ${out.path || "-"}`;
    }
    persistTransferFormState();
    await refreshAllLoaded();
    markDirty(false);
    setStatus("Transfer download complete. Save loaded.");
  } finally {
    if (transferDownloadBtn) {
      transferDownloadBtn.disabled = false;
      transferDownloadBtn.textContent = transferDownloadBtn.dataset.defaultLabel || "Download + Load Save";
    }
    if (transferUploadBtn) transferUploadBtn.disabled = false;
  }
}

async function applyTransferUpload() {
  const body = {
    upload_managed_items: Boolean($("transferUploadManagedItems")?.checked),
  };
  const transferDownloadBtn = $("transferDownloadBtn");
  const transferUploadBtn = $("transferUploadBtn");
  const transferDownloadMeta = $("transferDownloadMeta");
  const transferUploadMeta = $("transferUploadMeta");
  if (transferDownloadBtn && !transferDownloadBtn.dataset.defaultLabel) {
    transferDownloadBtn.dataset.defaultLabel = transferDownloadBtn.textContent;
  }
  if (transferUploadBtn && !transferUploadBtn.dataset.defaultLabel) {
    transferUploadBtn.dataset.defaultLabel = transferUploadBtn.textContent;
  }
  if (transferUploadBtn) {
    transferUploadBtn.disabled = true;
    transferUploadBtn.textContent = "Uploading...";
  }
  if (transferDownloadBtn) transferDownloadBtn.disabled = true;
  if (transferUploadMeta) transferUploadMeta.textContent = "Uploading current save and requesting new transfer codes...";
  if (transferDownloadMeta) transferDownloadMeta.textContent = "";
  setStatus("Uploading save data to server...");
  try {
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
    if (transferUploadMeta) {
      transferUploadMeta.textContent = linked > 0
        ? `Upload complete. Linked ${linked} downloaded account(s) as uploaded.`
        : "Upload complete. New transfer codes generated.";
    }
    setStatus(linked > 0 ? `Upload complete. Linked ${linked} downloaded account(s) as uploaded.` : "Upload complete. New transfer codes generated.");
  } finally {
    if (transferUploadBtn) {
      transferUploadBtn.disabled = false;
      transferUploadBtn.textContent = transferUploadBtn.dataset.defaultLabel || "Upload + Get Codes";
    }
    if (transferDownloadBtn) transferDownloadBtn.disabled = false;
  }
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

