// Frontend entrypoint
initUI().catch((e) => {
  setStatus(`Init error: ${e.message}`);
  showToast(`Init error: ${e.message}`, "error");
});
