// Rendering functions
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

function renderPlaytime() {
  const meta = $("playtimeMeta");
  const hours = $("playtime_hours");
  const minutes = $("playtime_minutes");
  const seconds = $("playtime_seconds");
  const playtime = state.playtime;
  if (!meta || !hours || !minutes || !seconds) return;

  if (!playtime) {
    meta.textContent = "No save loaded.";
    hours.value = "";
    minutes.value = "";
    seconds.value = "";
    return;
  }

  hours.value = Number(playtime.hours || 0);
  minutes.value = Number(playtime.minutes || 0);
  seconds.value = Number(playtime.seconds || 0);
  meta.textContent = `Current: ${Number(playtime.hours || 0)}h ${Number(playtime.minutes || 0)}m ${Number(playtime.seconds || 0)}s (${Number(playtime.frames || 0)} frames)`;
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
  const selectedIconUrl = resolveCannonIconUrl({ name: "Cat Cannon" });
  selectedRow.innerHTML = `
    <span class="inv-left"><img class="item-icon" src="${selectedIconUrl}" alt="" loading="lazy" referrerpolicy="no-referrer" /> <strong>Selected Parts Set</strong><span class="muted">Current global part IDs</span></span>
    <span class="inv-edit">
      <input class="inv-input selected-part-input" type="number" min="0" value="${Number(selected[0] || 0)}" />
      <input class="inv-input selected-part-input" type="number" min="0" value="${Number(selected[1] || 0)}" />
      <input class="inv-input selected-part-input" type="number" min="0" value="${Number(selected[2] || 0)}" />
      <button class="inv-save-btn">Apply</button>
    </span>
  `;
  applyItemIconFallback(selectedRow.querySelector(".item-icon"), "materials");
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
    const cannonIconUrl = resolveCannonIconUrl(cannon);
    div.innerHTML = `
      <span class="inv-left">
        <img class="item-icon" src="${cannonIconUrl}" alt="" loading="lazy" referrerpolicy="no-referrer" />
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
    applyItemIconFallback(div.querySelector(".item-icon"), "materials");
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
          <label class="check-inline transfer-status-toggle" title="Mark this record as pending upload completion."><input class="transfer-needs-upload-input" type="checkbox"${needsUpload ? " checked" : ""} title="Mark this record as pending upload completion." /> Needs upload</label>
        </div>
        <div class="row-actions transfer-row-actions">
          <button class="inv-save-btn transfer-use-btn" title="Copy this record into the download fields above.">Use</button>
          <button class="inv-save-btn transfer-save-btn" title="Save edits made to this history record.">Save</button>
          <button class="inv-save-btn transfer-delete-btn" title="Delete this history record.">Delete</button>
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
  const applyBtn = $("applyCatEditBtn");
  if (!c) {
    root.textContent = "Select a cat to view details.";
    $("cat_id").value = "";
    $("cat_owned").value = "0";
    $("cat_base").value = "";
    $("cat_plus").value = "";
    $("cat_form").value = "";
    $("cat_unlocked_forms").value = "";
    $("cat_fourth").value = "";
    if (applyBtn) applyBtn.disabled = true;
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
  if (applyBtn) applyBtn.disabled = false;
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
  const categories = ["battle_items", "catamins", "catseyes", "catfruit", "talent_orbs", "materials"];
  const labels = {
    battle_items: "Battle Items",
    catamins: "Catamins",
    catseyes: "Catseyes",
    catfruit: "Catfruit",
    talent_orbs: "Talent Orbs",
    materials: "Base Mats",
  };
  const selected = state.inventoryTab === "all" ? categories : [state.inventoryTab];
  let rowIndex = 0;
  for (const category of selected) {
    const rows = [...(state.inventory[category] || [])];
    let orbGroupCounts = null;
    if (category === "talent_orbs") {
      rows.sort((a, b) => {
        const ga = String(a.group || "Unknown");
        const gb = String(b.group || "Unknown");
        if (ga !== gb) return ga.localeCompare(gb);
        const ea = String(a.effect || "");
        const eb = String(b.effect || "");
        if (ea !== eb) return ea.localeCompare(eb);
        const ra = String(a.rank || "");
        const rb = String(b.rank || "");
        if (ra !== rb) return ra.localeCompare(rb);
        return Number(a.index || 0) - Number(b.index || 0);
      });
      orbGroupCounts = new Map();
      for (const row of rows) {
        const group = String(row.group || "Unknown");
        orbGroupCounts.set(group, (orbGroupCounts.get(group) || 0) + 1);
      }
    }
    if (state.inventoryTab === "all") {
      const header = document.createElement("div");
      header.className = "inv-row inv-header";
      withReveal(header, rowIndex++);
      header.innerHTML = `<span class="inv-left"><img class="item-icon section-icon" src="${fallbackIconForCategory(category)}" alt="" /> <strong>${labels[category]}</strong></span><span class="muted">${(state.inventory[category] || []).length} items</span>`;
      root.appendChild(header);
    }
    let currentGroup = "";
    for (const row of rows) {
      if (category === "talent_orbs") {
        const group = String(row.group || "Unknown");
        if (group !== currentGroup) {
          currentGroup = group;
          const collapsed = state.collapsedTalentOrbGroups.has(group);
          const count = orbGroupCounts ? (orbGroupCounts.get(group) || 0) : 0;
          const sub = document.createElement("div");
          sub.className = "inv-row inv-header orb-group-header";
          withReveal(sub, rowIndex++);
          sub.innerHTML = `
            <span class="inv-left">
              <button class="orb-group-toggle" type="button" aria-expanded="${collapsed ? "false" : "true"}" aria-label="${collapsed ? "Expand" : "Collapse"} ${group}">
                <span class="orb-group-chevron" aria-hidden="true">${collapsed ? "▸" : "▾"}</span>
                <strong>${group}</strong>
              </button>
            </span>
            <span class="muted">${count} items</span>
          `;
          const toggle = sub.querySelector(".orb-group-toggle");
          toggle.onclick = () => {
            if (state.collapsedTalentOrbGroups.has(group)) state.collapsedTalentOrbGroups.delete(group);
            else state.collapsedTalentOrbGroups.add(group);
            renderInventory();
          };
          root.appendChild(sub);
        }
        if (state.collapsedTalentOrbGroups.has(group)) continue;
      }
      const div = document.createElement("div");
      div.className = "inv-row";
      withReveal(div, rowIndex++);
      const iconMarkup = category === "talent_orbs"
        ? renderTalentOrbIcon(row)
        : `<img class="item-icon" src="${resolveInventoryIconUrl(category, row)}" alt="" loading="lazy" referrerpolicy="no-referrer" />`;
      div.innerHTML = `
        <span class="inv-left">${iconMarkup} ${row.name}</span>
        <span class="inv-edit"><input class="inv-input" type="number" min="0" value="${row.amount}" /><button class="inv-save-btn">Apply</button></span>
      `;
      if (category !== "talent_orbs") applyItemIconFallback(div.querySelector(".item-icon"), category);
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
