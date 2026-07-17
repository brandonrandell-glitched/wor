let sessionId = null;
let currentWorkflow = "proposal";
let customerAccount = "";

const startPanel = document.getElementById("start-panel");
const chat = document.getElementById("chat");
const messages = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const customerInput = document.getElementById("customer-input");
const workflowSelect = document.getElementById("workflow-select");
const workflowDesc = document.getElementById("workflow-desc");
const startBtn = document.getElementById("start-btn");
const summaryPanel = document.getElementById("summary-panel");
const summaryList = document.getElementById("summary-list");
const jsonPanel = document.getElementById("json-panel");
const jsonOutput = document.getElementById("json-output");
const generateBtn = document.getElementById("generate-btn");
const downloadLink = document.getElementById("download-link");
const continuePanel = document.getElementById("continue-panel");
const continueButtons = document.getElementById("continue-buttons");

function updateWorkflowDesc() {
  const wf = (window.WORKFLOWS || []).find((w) => w.id === workflowSelect.value);
  workflowDesc.textContent = wf ? wf.description : "";
}

function addMessage(text, role) {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function showSummary(summary) {
  summaryList.innerHTML = "";
  for (const [label, value] of Object.entries(summary)) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = Array.isArray(value) ? value.join(", ") : String(value);
    summaryList.appendChild(dt);
    summaryList.appendChild(dd);
  }
  summaryPanel.hidden = false;
}

function showContinueOptions(options) {
  continueButtons.innerHTML = "";
  if (!options || !options.length) {
    continuePanel.hidden = true;
    return;
  }
  for (const opt of options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = opt.label;
    btn.addEventListener("click", () => continueWorkflow(opt.id, opt.label));
    continueButtons.appendChild(btn);
  }
  continuePanel.hidden = false;
}

function resetChatInput(enabled) {
  messageInput.disabled = !enabled;
  chatForm.querySelector("button").disabled = !enabled;
  if (enabled) messageInput.focus();
}

function handleResponse(data) {
  sessionId = data.session_id || sessionId;
  if (data.workflow) currentWorkflow = data.workflow;
  addMessage(data.message, "assistant");
  if (data.summary) showSummary(data.summary);
  if (data.generate_label) generateBtn.textContent = data.generate_label;
  if (data.json_output) {
    jsonOutput.textContent = JSON.stringify(data.json_output, null, 2);
    jsonPanel.hidden = false;
    resetChatInput(false);
    showContinueOptions(data.continue_options || []);
  } else {
    resetChatInput(true);
  }
}

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function continueWorkflow(targetWorkflow, label) {
  if (!sessionId) return;
  addMessage(`Continue: ${label}`, "user");
  continuePanel.hidden = true;
  downloadLink.hidden = true;
  generateBtn.disabled = false;
  try {
    const data = await api(`/api/session/${sessionId}/continue`, {
      workflow: targetWorkflow,
    });
    handleResponse(data);
  } catch (err) {
    addMessage(`Error: ${err.message}`, "assistant");
    continuePanel.hidden = false;
  }
}

workflowSelect.addEventListener("change", updateWorkflowDesc);
updateWorkflowDesc();

startBtn.addEventListener("click", async () => {
  const customer = customerInput.value.trim();
  if (!customer) return;

  customerAccount = customer;
  currentWorkflow = workflowSelect.value;
  startBtn.disabled = true;
  messages.innerHTML = "";
  summaryPanel.hidden = true;
  jsonPanel.hidden = true;
  continuePanel.hidden = true;
  downloadLink.hidden = true;
  generateBtn.disabled = false;

  try {
    const data = await api("/api/session/start", {
      customer_account: customer,
      workflow: currentWorkflow,
    });
    sessionId = data.session_id;
    startPanel.hidden = true;
    chat.hidden = false;
    addMessage(customer, "user");
    handleResponse(data);
  } catch (err) {
    alert(err.message);
    startBtn.disabled = false;
  }
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = messageInput.value.trim();
  if (!message || !sessionId) return;

  addMessage(message, "user");
  messageInput.value = "";
  resetChatInput(false);

  try {
    const data = await api(`/api/session/${sessionId}/message`, { message });
    handleResponse(data);
  } catch (err) {
    addMessage(`Error: ${err.message}`, "assistant");
    resetChatInput(true);
  }
});

generateBtn.addEventListener("click", async () => {
  if (!sessionId) return;
  generateBtn.disabled = true;
  try {
    const data = await api(`/api/session/${sessionId}/generate`, {});
    downloadLink.href = data.download_url;
    downloadLink.textContent = `Download ${data.filename}`;
    downloadLink.hidden = false;
    addMessage(`Document ready: ${data.filename}`, "assistant");
  } catch (err) {
    alert(err.message);
    generateBtn.disabled = false;
  }
});

fetch("/api/health")
  .then((r) => r.json())
  .then((data) => {
    const badge = document.getElementById("mode-badge");
    if (badge) badge.textContent = data.mode === "public" ? "Public content" : data.mode;
  })
  .catch(() => {});
