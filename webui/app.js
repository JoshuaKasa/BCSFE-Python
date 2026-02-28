const state = {
  cats: [],
  selectedIds: new Set(),
  selectedCat: null,
  inventoryTab: "catseyes",
  inventory: { catseyes: [], catfruit: [], materials: [] },
  trophies: [],
  leftTab: "summary",
  rightTab: "preview",
  currentPath: null,
  dirty: false,
};

const $ = (id) => document.getElementById(id);

function setStatus(text) {
  $("statusBar").textContent = text;
}

function markDirty(isDirty = true) {
  state.dirty = isDirty;
  const bar = $("saveBar");
  const label = $("dirtyState");
  if (!bar || !label) return;
  if (isDirty) {
    bar.classList.add("show");
    label.textContent = "Unsaved changes";
  } else {
    bar.classList.remove("show");
    label.textContent = "No unsaved changes";
  }
}

async function api(path, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || `Request failed: ${path}`);
  }
  return data;
}

function renderSummary(summary) {
  const root = $("summary");
  root.innerHTML = "";
  if (!summary) return;
  const entries = [
    ["Path", summary.path],
    ["Inquiry", summary.inquiry_code],
    ["Country", summary.country],
    ["Game Version", summary.game_version],
    ["Cats", `${summary.cats_unlocked}/${summary.cats_total}`],
    ["Catfood", summary.catfood],
    ["XP", summary.xp],
    ["NP", summary.np],
    ["Rare", summary.rare_tickets],
    ["Platinum", summary.platinum_tickets],
    ["Legend", summary.legend_tickets],
    ["Trophies", `${summary.trophies_owned ?? 0}/${summary.trophies_total ?? 0}`],
  ];
  for (const [k, v] of entries) {
    const row = document.createElement("div");
    row.innerHTML = `<span>${k}</span><span>${v}</span>`;
    root.appendChild(row);
  }

  const map = [
    "catfood",
    "xp",
    "np",
    "normal_tickets",
    "rare_tickets",
    "platinum_tickets",
    "legend_tickets",
    "leadership",
  ];
  for (const key of map) {
    const el = $(`res_${key}`);
    if (el && summary[key] !== undefined) el.value = summary[key];
  }
}

function presetButtons() {
  const map = [
    ["10", "Human-max progression (recommended)"],
    ["9", "Full legit max (keep current treasures)"],
    ["1", "Safer max resources"],
    ["5", "Starter boost"],
  ];
  const root = $("presets");
  root.innerHTML = "";
  for (const [id, name] of map) {
    const btn = document.createElement("button");
    btn.textContent = `${id}. ${name}`;
    btn.onclick = async () => {
      try {
        setStatus(`Applying preset ${id}...`);
        const out = await api("/api/preset", "POST", { preset: id });
        renderSummary(out.summary);
        await refreshCats();
        await refreshInventory();
        await refreshTrophies();
        markDirty(true);
        setStatus(out.failed?.length ? `Preset ${id} applied (some failures)` : `Preset ${id} applied`);
      } catch (e) {
        setStatus(`Preset error: ${e.message}`);
      }
    };
    root.appendChild(btn);
  }
}

function renderCats() {
  const body = $("catsTable").querySelector("tbody");
  body.innerHTML = "";
  for (const c of state.cats) {
    const tr = document.createElement("tr");
    tr.className = c.owned ? "owned" : "missing";
    if (state.selectedIds.has(c.id)) tr.classList.add("selected");
    tr.onclick = (ev) => {
      if (ev.ctrlKey || ev.metaKey) {
        if (state.selectedIds.has(c.id)) state.selectedIds.delete(c.id);
        else state.selectedIds.add(c.id);
      } else {
        state.selectedIds = new Set([c.id]);
      }
      state.selectedCat = c;
      renderCats();
      renderPreview();
      renderSelectionBadge();
    };
    tr.innerHTML = `
      <td><img class="cat-img" src="${c.image_url}" alt="${c.name}" loading="lazy" /></td>
      <td>${c.id}</td>
      <td>${c.name}</td>
      <td>${c.owned ? "Yes" : "No"}</td>
      <td>${c.base}</td>
      <td>${c.plus}</td>
      <td>${c.form}</td>
      <td>${c.unlocked_forms}</td>
      <td>${c.fourth}</td>
    `;
    body.appendChild(tr);
  }
  attachInlineEditors();
}

function renderSelectionBadge() {
  const n = state.selectedIds.size;
  $("selectionBadge").textContent = `${n} selected`;
}

function renderPreview() {
  const root = $("catPreview");
  const c = state.selectedCat;
  if (!c) {
    root.textContent = "Select a cat to view details.";
    return;
  }
  root.innerHTML = `
    <img class="preview-img" src="${c.image_url}" alt="${c.name}" />
    ID: ${c.id}
    Number: ${c.number}
    Name: ${c.name}
    Owned: ${c.owned ? "Yes" : "No"}
    Base: ${c.base}
    Plus: ${c.plus}
    Current Form: ${c.form}
    Unlocked Forms: ${c.unlocked_forms}
    Fourth Form: ${c.fourth}
  `;
  $("cat_id").value = c.id;
  $("cat_owned").value = c.owned ? "1" : "0";
  $("cat_base").value = c.base;
  $("cat_plus").value = c.plus;
  $("cat_form").value = c.form;
  $("cat_unlocked_forms").value = c.unlocked_forms;
  $("cat_fourth").value = c.fourth;
}

function renderInventory() {
  const root = $("inventoryList");
  root.innerHTML = "";
  const iconMap = {
    catseyes: "/webui/icons/catseye.svg",
    catfruit: "/webui/icons/catfruit.svg",
    materials: "/webui/icons/material.svg",
  };
  const icon = iconMap[state.inventoryTab] || "/webui/icons/inventory.svg";
  for (const row of state.inventory[state.inventoryTab] || []) {
    const div = document.createElement("div");
    div.className = "inv-row";
    if (state.inventoryTab === "catseyes" || state.inventoryTab === "catfruit") {
      div.innerHTML = `
        <span class="inv-left"><img class="icon" src="${icon}" alt="" /> ${row.name}</span>
        <span class="inv-edit">
          <input class="inv-input" type="number" min="0" value="${row.amount}" />
          <button class="inv-save-btn">Apply</button>
        </span>
      `;
      const input = div.querySelector(".inv-input");
      const btn = div.querySelector(".inv-save-btn");
      const apply = async () => {
        const amount = Number(input.value || 0);
        await applyInventoryEdit(state.inventoryTab, Number(row.index), amount);
      };
      btn.onclick = apply;
      input.onkeydown = (e) => {
        if (e.key === "Enter") apply();
      };
    } else {
      div.innerHTML = `
        <span class="inv-left"><img class="icon" src="${icon}" alt="" /> ${row.name}</span>
        <span>${row.amount}</span>
      `;
    }
    root.appendChild(div);
  }
}

function renderTrophies() {
  const root = $("trophiesList");
  if (!root) return;
  root.innerHTML = "";
  for (const row of state.trophies || []) {
    const div = document.createElement("div");
    div.className = "inv-row";
    const left = document.createElement("span");
    left.className = "inv-left";
    left.textContent = `${row.name} (#${row.id})${row.description ? ` - ${row.description}` : ""}`;

    const right = document.createElement("span");
    right.className = "inv-edit";
    const status = document.createElement("span");
    status.textContent = row.owned ? "Owned" : "Missing";
    const btn = document.createElement("button");
    btn.className = "inv-save-btn";
    btn.textContent = row.owned ? "Remove" : "Add";
    btn.onclick = () => applyTrophyEdit(Number(row.id), !row.owned);
    right.appendChild(status);
    right.appendChild(btn);

    div.appendChild(left);
    div.appendChild(right);
    root.appendChild(div);
  }
}

async function applyTrophyEdit(id, owned) {
  try {
    setStatus(`${owned ? "Adding" : "Removing"} trophy ${id}...`);
    const out = await api("/api/trophies/update", "POST", { id, owned });
    state.trophies = out.trophies || [];
    renderSummary(out.summary);
    renderTrophies();
    markDirty(true);
    setStatus(`${owned ? "Added" : "Removed"} trophy ${id}.`);
  } catch (e) {
    setStatus(`Trophy edit error: ${e.message}`);
  }
}

async function applyInventoryEdit(category, index, amount) {
  try {
    setStatus(`Applying ${category} edit...`);
    const out = await api("/api/inventory/update", "POST", { category, index, amount });
    state.inventory = {
      catseyes: out.inventory.catseyes || [],
      catfruit: out.inventory.catfruit || [],
      materials: out.inventory.materials || [],
    };
    renderSummary(out.summary);
    renderInventory();
    markDirty(true);
    setStatus(`Updated ${category} item ${index}.`);
  } catch (e) {
    setStatus(`Inventory edit error: ${e.message}`);
  }
}

function bulkIdsFromScope() {
  const scope = $("bulkScope")?.value || "visible";
  if (scope === "all") return [];
  return state.cats.map((c) => c.id);
}

async function runBulk(payload, label) {
  try {
    const ids = bulkIdsFromScope();
    const ownedOnly = Boolean($("bulkOwnedOnly")?.checked);
    const requestBody = { ...payload, ids, owned_only: ownedOnly };
    setStatus(`Applying bulk action: ${label}...`);
    const out = await api("/api/cats/bulk", "POST", requestBody);
    renderSummary(out.summary);
    await refreshCats();
    markDirty(true);
    setStatus(`${label} applied to ${out.count} cats.`);
  } catch (e) {
    setStatus(`Bulk action error: ${e.message}`);
  }
}

async function applyBulkLevelsForms() {
  const payload = {};
  const base = $("bulkBase")?.value?.trim();
  const plus = $("bulkPlus")?.value?.trim();
  const form = $("bulkForm")?.value?.trim();
  const unlockedForms = $("bulkUnlockedForms")?.value?.trim();
  if (base !== "") payload.base = Number(base);
  if (plus !== "") payload.plus = Number(plus);
  if (form !== "") payload.form = Number(form);
  if (unlockedForms !== "") payload.unlocked_forms = Number(unlockedForms);

  if (Object.keys(payload).length === 0) {
    setStatus("Enter at least one level/form value.");
    return;
  }
  await runBulk(payload, "Levels/Forms update");
}

function activateLeftTab(tab) {
  state.leftTab = tab;
  document.querySelectorAll(".left-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.leftTab === tab);
  });
  document.querySelectorAll(".left-panel-content").forEach((el) => {
    el.classList.toggle("active", el.id === `left_${tab}`);
  });
}

function activateRightTab(tab) {
  state.rightTab = tab;
  document.querySelectorAll(".right-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.rightTab === tab);
  });
  document.querySelectorAll(".right-panel-content").forEach((el) => {
    el.classList.toggle("active", el.id === `right_${tab}`);
  });
}

function activateInventoryTab(tab) {
  state.inventoryTab = tab;
  document.querySelectorAll(".inventory-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  renderInventory();
}

async function refreshStatus() {
  const out = await api("/api/status");
  renderSummary(out.summary);
  state.currentPath = out.summary?.path || null;
  $("pathLabel").textContent = state.currentPath || "No file selected";
  setStatus(out.loaded ? "Save loaded." : "No save loaded.");
}

async function refreshCats() {
  const q = encodeURIComponent($("searchInput").value.trim());
  const f = encodeURIComponent($("filterSelect").value);
  const out = await api(`/api/cats?query=${q}&filter=${f}`);
  state.cats = out.cats;
  if (state.selectedIds.size) {
    const ids = new Set(state.cats.map((x) => x.id));
    for (const id of [...state.selectedIds]) if (!ids.has(id)) state.selectedIds.delete(id);
  }
  const firstId = [...state.selectedIds][0];
  state.selectedCat = state.cats.find((x) => x.id === firstId) || null;
  renderCats();
  renderPreview();
  renderSelectionBadge();
}

async function refreshInventory() {
  const out = await api("/api/inventory");
  state.inventory = out;
  renderInventory();
}

async function refreshTrophies() {
  const out = await api("/api/trophies");
  state.trophies = out.trophies || [];
  renderTrophies();
}

async function doCatAction(action) {
  if (!state.selectedIds.size) {
    setStatus("Select one or more cats first.");
    return;
  }
  await api("/api/cats/action", "POST", { action, ids: [...state.selectedIds] });
  await refreshStatus();
  await refreshCats();
  markDirty(true);
  setStatus(`Applied action: ${action}`);
}

async function loadSave() {
  try {
    if (state.dirty && !window.confirm("Discard unsaved changes and load another save?")) return;
    setStatus("Choose a save file...");
    const picked = await api("/api/pick_path");
    const path = picked.path;
    setStatus("Loading save...");
    const out = await api("/api/load", "POST", { path });
    state.currentPath = path;
    $("pathLabel").textContent = path;
    renderSummary(out.summary);
    await refreshCats();
    await refreshInventory();
    await refreshTrophies();
    markDirty(false);
    setStatus("Save loaded.");
  } catch (e) {
    setStatus(`Load error: ${e.message}`);
  }
}

async function saveAs() {
  try {
    const picked = await api("/api/pick_save_path");
    const outPath = picked.path;
    setStatus("Saving...");
    const out = await api("/api/save", "POST", { path: outPath });
    state.currentPath = out.path;
    $("pathLabel").textContent = out.path;
    markDirty(false);
    setStatus(`Saved: ${out.path}`);
  } catch (e) {
    setStatus(`Save error: ${e.message}`);
  }
}

async function applyResourceEdits() {
  try {
    const payload = {
      catfood: Number($("res_catfood").value || 0),
      xp: Number($("res_xp").value || 0),
      np: Number($("res_np").value || 0),
      normal_tickets: Number($("res_normal_tickets").value || 0),
      rare_tickets: Number($("res_rare_tickets").value || 0),
      platinum_tickets: Number($("res_platinum_tickets").value || 0),
      legend_tickets: Number($("res_legend_tickets").value || 0),
      leadership: Number($("res_leadership").value || 0),
    };
    const out = await api("/api/resources", "POST", payload);
    renderSummary(out.summary);
    markDirty(true);
    setStatus("Applied resource edits.");
    await refreshCats();
  } catch (e) {
    setStatus(`Resource edit error: ${e.message}`);
  }
}

async function applyOperation(key, label) {
  try {
    setStatus(`Applying ${label}...`);
    const out = await api("/api/op", "POST", { key });
    renderSummary(out.summary);
    await refreshCats();
    await refreshInventory();
    await refreshTrophies();
    markDirty(true);
    setStatus(`${label} applied.`);
  } catch (e) {
    setStatus(`${label} error: ${e.message}`);
  }
}

async function applySelectedCatEdit() {
  try {
    if (!$("cat_id").value) {
      setStatus("Select a cat first.");
      return;
    }
    const payload = {
      id: Number($("cat_id").value),
      owned: $("cat_owned").value === "1",
      base: Number($("cat_base").value || 1),
      plus: Number($("cat_plus").value || 0),
      form: Number($("cat_form").value || 0),
      unlocked_forms: Number($("cat_unlocked_forms").value || 0),
      fourth: Number($("cat_fourth").value || 0),
    };
    const out = await api("/api/cats/update", "POST", payload);
    renderSummary(out.summary);
    await refreshCats();
    markDirty(true);
    setStatus(`Applied edits to cat ${payload.id}.`);
  } catch (e) {
    setStatus(`Cat edit error: ${e.message}`);
  }
}

async function syncMyGamatoto() {
  try {
    setStatus("Syncing MyGamatoto...");
    const out = await api("/api/sync_mygamatoto", "POST", {});
    await refreshCats();
    setStatus(`Synced MyGamatoto: ${out.count} cat forms.`);
  } catch (e) {
    setStatus(`Sync error: ${e.message}`);
  }
}

async function revertCurrent() {
  try {
    if (!state.currentPath) {
      setStatus("No loaded path to revert.");
      return;
    }
    if (!window.confirm("Revert all unsaved changes by reloading current save?")) return;
    setStatus("Reverting...");
    const out = await api("/api/load", "POST", { path: state.currentPath });
    renderSummary(out.summary);
    await refreshCats();
    await refreshInventory();
    await refreshTrophies();
    markDirty(false);
    setStatus("Reverted to last loaded save.");
  } catch (e) {
    setStatus(`Revert error: ${e.message}`);
  }
}

async function updateCatField(id, key, value) {
  const payload = { id };
  payload[key] = value;
  await api("/api/cats/update", "POST", payload);
}

function makeInlineEditable(td, id, key, initialValue, parseFn = Number) {
  td.ondblclick = async () => {
    if (td.querySelector("input")) return;
    const input = document.createElement("input");
    input.type = "number";
    input.value = String(initialValue);
    input.className = "inline-input";
    td.textContent = "";
    td.appendChild(input);
    input.focus();
    input.select();

    const cancel = () => {
      td.textContent = String(initialValue);
    };

    const commit = async () => {
      const nextValue = parseFn(input.value);
      if (Number.isNaN(nextValue)) {
        cancel();
        return;
      }
      try {
        await updateCatField(id, key, nextValue);
        markDirty(true);
        await refreshCats();
        setStatus(`Updated cat ${id} ${key}.`);
      } catch (e) {
        setStatus(`Inline edit error: ${e.message}`);
        cancel();
      }
    };

    input.onkeydown = (e) => {
      if (e.key === "Enter") commit();
      if (e.key === "Escape") cancel();
    };
    input.onblur = commit;
  };
}

function attachInlineEditors() {
  const rows = $("catsTable").querySelectorAll("tbody tr");
  rows.forEach((row) => {
    const cells = row.querySelectorAll("td");
    const id = Number(cells[1].textContent);
    const base = Number(cells[4].textContent);
    const plus = Number(cells[5].textContent);
    const form = Number(cells[6].textContent);
    makeInlineEditable(cells[4], id, "base", base, Number);
    makeInlineEditable(cells[5], id, "plus", plus, Number);
    makeInlineEditable(cells[6], id, "form", form, Number);
  });
}

function bindEvents() {
  $("loadBtn").onclick = loadSave;
  $("refreshBtn").onclick = async () => {
    await refreshStatus();
    if (state.currentPath) {
      await refreshCats();
      await refreshInventory();
      await refreshTrophies();
    }
    setStatus("Refreshed.");
  };
  $("saveBtn").onclick = saveAs;
  $("saveBarSaveBtn").onclick = saveAs;
  $("revertBtn").onclick = revertCurrent;
  $("syncBtn").onclick = syncMyGamatoto;
  $("applyResourcesBtn").onclick = applyResourceEdits;
  $("maxGamatotoBtn").onclick = () => applyOperation("max_gamatoto", "Max Gamatoto");
  $("applyCatEditBtn").onclick = applySelectedCatEdit;
  $("searchInput").oninput = refreshCats;
  $("filterSelect").onchange = refreshCats;
  $("bulkUnlockBtn").onclick = () => runBulk({ unlock: true }, "Unlock");
  $("bulkTrueFormBtn").onclick = () => runBulk({ true_form: true }, "True Forms");
  $("bulkFourthFormBtn").onclick = () => runBulk({ fourth_form: true }, "4th Forms");
  $("bulkLegitMaxBtn").onclick = () => runBulk({ legit_max: true }, "Legit Max");
  $("bulkApplyLevelsBtn").onclick = applyBulkLevelsForms;

  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.onclick = () => doCatAction(btn.dataset.action);
  });

  document.querySelectorAll(".left-tab").forEach((btn) => {
    btn.onclick = () => activateLeftTab(btn.dataset.leftTab);
  });
  document.querySelectorAll(".right-tab").forEach((btn) => {
    btn.onclick = () => activateRightTab(btn.dataset.rightTab);
  });
  document.querySelectorAll(".inventory-tab").forEach((btn) => {
    btn.onclick = () => activateInventoryTab(btn.dataset.tab);
  });

  window.addEventListener("beforeunload", (e) => {
    if (!state.dirty) return;
    e.preventDefault();
    e.returnValue = "";
  });
}

async function init() {
  bindEvents();
  presetButtons();
  $("pathLabel").textContent = "No file selected";
  activateLeftTab(state.leftTab);
  activateRightTab(state.rightTab);
  activateInventoryTab(state.inventoryTab);
  markDirty(false);
  await refreshStatus();
  if (state.currentPath) {
    await refreshCats();
    await refreshInventory();
    await refreshTrophies();
  }
}

init();
