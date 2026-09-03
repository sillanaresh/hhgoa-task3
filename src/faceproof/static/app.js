"use strict";

const state = {
  runId: null,
  record: null,
  health: null,
  polling: false,
  previewReadId: 0,
  toastTimer: null,
};

const ui = Object.fromEntries(
  [
    "readinessSummary",
    "readinessChecks",
    "walletSetup",
    "createWallet",
    "refreshHealth",
    "scanForm",
    "faceImage",
    "consent",
    "dropzone",
    "dropTitle",
    "localPreview",
    "startButton",
    "inputSection",
    "resultSection",
    "matchStatus",
    "comparison",
    "inputAnnotated",
    "matchImage",
    "matchSource",
    "matchFinding",
    "matchTitle",
    "matchLink",
    "similarityValue",
    "scoreFill",
    "thresholdMark",
    "thresholdText",
    "candidateDisclosure",
    "candidateSummary",
    "candidateList",
    "evidenceRecord",
    "evidenceHash",
    "copyHash",
    "downloadEvidence",
    "approval",
    "publishButton",
    "rejectButton",
    "rejectedRecord",
    "rejectedRetry",
    "verifiedRecord",
    "receiptNetwork",
    "receiptBlock",
    "receiptTransaction",
    "receiptConfirmations",
    "explorerLink",
    "verifyButton",
    "errorRecord",
    "errorTitle",
    "errorRecovery",
    "retryButton",
    "runIdentifier",
    "cancelButton",
    "stageList",
    "runPulse",
    "runMessage",
    "toast",
  ].map((id) => [id, document.getElementById(id)]),
);

const terminalStatuses = new Set(["awaiting_publish", "verified", "rejected", "failed", "canceled"]);
const stageSymbols = {
  complete: "✓",
  failed: "!",
  running: "•",
  skipped: "–",
};

function showToast(message) {
  window.clearTimeout(state.toastTimer);
  ui.toast.textContent = message;
  ui.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    ui.toast.hidden = true;
  }, 3200);
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : "#";
  } catch {
    return "#";
  }
}

function shortHash(value, visible = 7) {
  if (!value || value.length <= visible * 2) return value || "";
  return `${value.slice(0, visible)}…${value.slice(-visible)}`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Request failed with status ${response.status}.`);
  }
  if (!response.ok) {
    const detail = payload.error || payload.detail || {};
    const message = typeof detail === "string" ? detail : detail.message;
    const recovery = typeof detail === "object" ? detail.recovery : null;
    throw new Error([message || "The request could not be completed.", recovery]
      .filter(Boolean)
      .join(" "));
  }
  return payload;
}

function addHealthCheck(label, ready, detail = "") {
  const item = document.createElement("span");
  item.className = "health-check";
  item.dataset.ready = String(ready);
  item.textContent = label;
  if (detail) item.title = detail;
  ui.readinessChecks.append(item);
}

async function loadHealth({ quiet = false } = {}) {
  ui.refreshHealth.disabled = true;
  if (!quiet) ui.readinessSummary.textContent = "Checking local and public services…";
  try {
    const health = await fetchJson("/api/health");
    state.health = health;
    ui.readinessChecks.replaceChildren();
    addHealthCheck("Face models", health.models_ready, "Pinned OpenCV YuNet and SFace models");
    addHealthCheck("Live search", health.search_configured, "SerpApi Google Lens");
    addHealthCheck("Test wallet", health.wallet_configured, health.wallet_address || "Not created");
    addHealthCheck("Test ETH", health.wallet_funded, "Gas for one Base Sepolia transaction");
    addHealthCheck("Base Sepolia", health.blockchain_reachable, "Public chain 84532");

    const missing = [];
    if (!health.search_configured) missing.push("a search key");
    if (!health.wallet_configured) missing.push("a test wallet");
    else if (!health.wallet_funded) missing.push("free test ETH");
    if (!health.blockchain_reachable) missing.push("a Base Sepolia connection");
    ui.readinessSummary.textContent = missing.length
      ? `Setup still needs ${missing.join(", ")}. Face analysis remains local.`
      : "All services are ready for a complete public verification run.";
    ui.walletSetup.hidden = health.wallet_configured;
    ui.startButton.disabled = !health.search_configured;
    ui.startButton.title = health.search_configured
      ? ""
      : "Add SERPAPI_API_KEY to .context/secrets.env and restart the app.";
  } catch (error) {
    ui.readinessSummary.textContent = "Readiness could not be checked. Is the local server running?";
    ui.readinessChecks.replaceChildren();
    addHealthCheck("Local API", false);
    ui.startButton.disabled = true;
    if (!quiet) showToast(error.message);
  } finally {
    ui.refreshHealth.disabled = false;
  }
}

function updatePreview(file) {
  const readId = state.previewReadId + 1;
  state.previewReadId = readId;
  ui.localPreview.hidden = true;
  ui.localPreview.removeAttribute("src");
  if (!file) {
    ui.dropTitle.textContent = "Choose an image or drop it here";
    return;
  }
  const allowed = new Set(["image/jpeg", "image/png", "image/webp"]);
  if (!allowed.has(file.type)) {
    ui.faceImage.value = "";
    showToast("Choose a JPEG, PNG, or WebP image.");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    ui.faceImage.value = "";
    showToast("Choose an image smaller than 10 MB.");
    return;
  }
  ui.dropTitle.textContent = file.name;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    if (state.previewReadId !== readId || typeof reader.result !== "string") return;
    ui.localPreview.src = reader.result;
    ui.localPreview.hidden = false;
  });
  reader.addEventListener("error", () => {
    if (state.previewReadId !== readId) return;
    ui.faceImage.value = "";
    ui.dropTitle.textContent = "Choose an image or drop it here";
    showToast("The selected image preview could not be loaded. Choose the file again.");
  });
  reader.readAsDataURL(file);
}

function resetRun() {
  state.runId = null;
  state.record = null;
  state.polling = false;
  ui.scanForm.reset();
  updatePreview(null);
  ui.inputSection.hidden = false;
  ui.resultSection.hidden = true;
  ui.comparison.hidden = true;
  ui.matchFinding.hidden = true;
  ui.candidateDisclosure.hidden = true;
  ui.evidenceRecord.hidden = true;
  ui.approval.hidden = true;
  ui.rejectedRecord.hidden = true;
  ui.verifiedRecord.hidden = true;
  ui.errorRecord.hidden = true;
  ui.cancelButton.hidden = true;
  ui.runIdentifier.textContent = "No run started";
  ui.runMessage.textContent = "Choose an image to begin.";
  ui.runPulse.dataset.active = "false";
  [...ui.stageList.children].forEach((item, index) => {
    item.dataset.stage = "pending";
    item.querySelector(".stage-marker").textContent = String(index + 1);
  });
  loadHealth({ quiet: true });
  ui.inputSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderStages(steps) {
  const items = [...ui.stageList.children];
  steps.forEach((step, index) => {
    const item = items[index];
    if (!item) return;
    item.dataset.stage = step.status;
    item.querySelector("strong").textContent = step.title;
    item.querySelector("p").textContent = step.detail;
    item.querySelector(".stage-marker").textContent = stageSymbols[step.status] || String(index + 1);
  });
}

function renderCandidates(candidates) {
  ui.candidateList.replaceChildren();
  candidates.forEach((candidate, index) => {
    const row = document.createElement("div");
    row.className = "candidate-row";

    const rank = document.createElement("span");
    rank.className = "candidate-rank";
    rank.textContent = String(index + 1).padStart(2, "0");

    const copy = document.createElement("div");
    copy.className = "candidate-copy";
    const link = document.createElement("a");
    link.href = safeExternalUrl(candidate.post_url);
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = candidate.title;
    const meta = document.createElement("span");
    const faceNote = candidate.faces_detected === null || candidate.faces_detected === undefined
      ? "not evaluated"
      : `${candidate.faces_detected} face${candidate.faces_detected === 1 ? "" : "s"}`;
    meta.textContent = `${candidate.source} · ${candidate.query_kind.replace("_", " ")} · ${faceNote}`;
    copy.append(link, meta);

    const score = document.createElement("span");
    score.className = "candidate-score";
    score.dataset.passed = String(candidate.passes_threshold);
    score.textContent = candidate.similarity === null || candidate.similarity === undefined
      ? "—"
      : candidate.similarity.toFixed(3);
    if (candidate.evaluation_error) score.title = candidate.evaluation_error;

    row.append(rank, copy, score);
    ui.candidateList.append(row);
  });
  ui.candidateSummary.textContent = `Candidates evaluated: ${candidates.length}`;
  ui.candidateDisclosure.hidden = candidates.length === 0;
}

function renderMatch(record) {
  const match = record.selected_match;
  if (!match) return;
  ui.comparison.hidden = false;
  ui.matchFinding.hidden = false;
  ui.inputAnnotated.src = record.face.annotated_url;
  ui.matchImage.src = match.local_image_url;
  ui.matchSource.textContent = match.source;
  ui.matchTitle.textContent = match.title;
  ui.matchLink.href = safeExternalUrl(match.post_url);
  ui.similarityValue.textContent = match.similarity.toFixed(3);
  ui.thresholdText.textContent = `Decision threshold: ${match.threshold.toFixed(3)} · higher means more similar`;
  const scorePercent = Math.max(0, Math.min(100, ((match.similarity + 1) / 2) * 100));
  const thresholdPercent = Math.max(0, Math.min(100, ((match.threshold + 1) / 2) * 100));
  ui.scoreFill.style.transform = `scaleX(${scorePercent / 100})`;
  ui.thresholdMark.style.left = `${thresholdPercent}%`;
  ui.matchStatus.textContent = "Match passed";
  ui.matchStatus.dataset.status = "match";
}

function renderEvidence(record) {
  if (!record.evidence) return;
  ui.evidenceRecord.hidden = false;
  ui.evidenceHash.textContent = record.evidence.evidence_id;
  ui.downloadEvidence.href = `/api/runs/${encodeURIComponent(record.run_id)}/evidence/download`;
}

function renderBlockchain(record) {
  const receipt = record.blockchain;
  if (!receipt || !receipt.verification_passed) return;
  ui.verifiedRecord.hidden = false;
  ui.approval.hidden = true;
  ui.receiptNetwork.textContent = `${receipt.network} · chain ${receipt.chain_id}`;
  ui.receiptBlock.textContent = String(receipt.block_number);
  ui.receiptTransaction.textContent = shortHash(receipt.transaction_hash, 10);
  ui.receiptTransaction.title = receipt.transaction_hash;
  ui.receiptConfirmations.textContent = String(receipt.confirmations);
  ui.explorerLink.href = safeExternalUrl(receipt.explorer_url);
  ui.matchStatus.textContent = "Publicly verified";
  ui.matchStatus.dataset.status = "verified";
}

function renderRecord(record) {
  state.record = record;
  state.runId = record.run_id;
  ui.runIdentifier.textContent = `Run ${record.run_id.slice(0, 8)}`;
  ui.runIdentifier.title = record.run_id;
  ui.runMessage.textContent = record.status_message;
  ui.runPulse.dataset.active = String(["running", "publishing"].includes(record.status));
  ui.cancelButton.hidden = !["created", "running"].includes(record.status);
  renderStages(record.steps);

  if (record.status !== "created") {
    ui.resultSection.hidden = false;
    ui.matchStatus.textContent = ["running", "publishing"].includes(record.status)
      ? "Working"
      : record.status.replace("_", " ");
    ui.matchStatus.dataset.status = record.status === "failed" ? "failed" : "";
  }
  if (record.candidates.length) renderCandidates(record.candidates);
  if (record.selected_match) renderMatch(record);
  if (record.evidence) renderEvidence(record);
  ui.approval.hidden = record.status !== "awaiting_publish";
  ui.publishButton.disabled = record.status !== "awaiting_publish";
  ui.rejectButton.disabled = record.status !== "awaiting_publish";
  if (record.status === "verified") renderBlockchain(record);

  if (record.status === "rejected") {
    ui.rejectedRecord.hidden = false;
    ui.matchStatus.textContent = "Match rejected";
    ui.matchStatus.dataset.status = "failed";
  }

  if (record.status === "failed") {
    ui.errorRecord.hidden = false;
    ui.errorTitle.textContent = record.error?.message || record.status_message;
    ui.errorRecovery.textContent = record.error?.recovery || "Keep this run for inspection and try again.";
    ui.matchStatus.textContent = "Run stopped";
    ui.matchStatus.dataset.status = "failed";
  }
}

async function pollRun() {
  if (state.polling || !state.runId) return;
  state.polling = true;
  try {
    while (state.runId) {
      const record = await fetchJson(`/api/runs/${encodeURIComponent(state.runId)}`);
      renderRecord(record);
      if (terminalStatuses.has(record.status)) break;
      await new Promise((resolve) => window.setTimeout(resolve, 750));
    }
  } catch (error) {
    showToast(error.message);
  } finally {
    state.polling = false;
  }
}

ui.faceImage.addEventListener("change", () => updatePreview(ui.faceImage.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  ui.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    ui.dropzone.dataset.dragging = "true";
  });
});

["dragleave", "drop"].forEach((eventName) => {
  ui.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    ui.dropzone.dataset.dragging = "false";
  });
});

ui.dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  ui.faceImage.files = transfer.files;
  updatePreview(file);
});

ui.scanForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!ui.faceImage.files[0] || !ui.consent.checked) {
    ui.scanForm.reportValidity();
    return;
  }
  ui.startButton.disabled = true;
  ui.startButton.textContent = "Starting search…";
  try {
    const form = new FormData();
    form.append("image", ui.faceImage.files[0]);
    form.append("consent", "true");
    const record = await fetchJson("/api/runs", { method: "POST", body: form });
    renderRecord(record);
    ui.resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    pollRun();
  } catch (error) {
    showToast(error.message);
    ui.startButton.disabled = false;
  } finally {
    ui.startButton.replaceChildren("Start live search");
  }
});

ui.publishButton.addEventListener("click", async () => {
  if (!state.runId) return;
  ui.publishButton.disabled = true;
  ui.publishButton.textContent = "Publishing…";
  try {
    const record = await fetchJson(`/api/runs/${encodeURIComponent(state.runId)}/publish`, {
      method: "POST",
    });
    renderRecord(record);
    pollRun();
  } catch (error) {
    showToast(error.message);
    ui.publishButton.disabled = false;
  } finally {
    ui.publishButton.textContent = "Publish fingerprint";
  }
});

ui.rejectButton.addEventListener("click", async () => {
  if (!state.runId) return;
  ui.rejectButton.disabled = true;
  try {
    const record = await fetchJson(`/api/runs/${encodeURIComponent(state.runId)}/reject`, {
      method: "POST",
    });
    renderRecord(record);
    showToast("Match rejected. Nothing was published.");
  } catch (error) {
    showToast(error.message);
    ui.rejectButton.disabled = false;
  }
});

ui.verifyButton.addEventListener("click", async () => {
  if (!state.runId) return;
  ui.verifyButton.disabled = true;
  try {
    const record = await fetchJson(`/api/runs/${encodeURIComponent(state.runId)}/verify`, {
      method: "POST",
    });
    renderRecord(record);
    showToast(record.blockchain?.verification_passed
      ? "The local evidence still matches the public transaction."
      : "Verification failed.");
  } catch (error) {
    showToast(error.message);
  } finally {
    ui.verifyButton.disabled = false;
  }
});

ui.cancelButton.addEventListener("click", async () => {
  if (!state.runId) return;
  ui.cancelButton.disabled = true;
  try {
    renderRecord(await fetchJson(`/api/runs/${encodeURIComponent(state.runId)}/cancel`, {
      method: "POST",
    }));
  } catch (error) {
    showToast(error.message);
  } finally {
    ui.cancelButton.disabled = false;
  }
});

ui.copyHash.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(ui.evidenceHash.textContent);
    showToast("Evidence fingerprint copied.");
  } catch {
    showToast("Copy was blocked. Select the fingerprint manually.");
  }
});

ui.createWallet.addEventListener("click", async () => {
  ui.createWallet.disabled = true;
  try {
    const wallet = await fetchJson("/api/wallet", { method: "POST" });
    showToast(`Test wallet created: ${shortHash(wallet.address)}`);
    await loadHealth({ quiet: true });
  } catch (error) {
    showToast(error.message);
  } finally {
    ui.createWallet.disabled = false;
  }
});

ui.refreshHealth.addEventListener("click", () => loadHealth());
ui.retryButton.addEventListener("click", resetRun);
ui.rejectedRetry.addEventListener("click", resetRun);

loadHealth();
