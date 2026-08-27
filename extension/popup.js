// SpectraBrowser Extension Popup Script

const statusBadge = document.getElementById("statusBadge");
const tabTitle = document.getElementById("tabTitle");
const tabUrl = document.getElementById("tabUrl");
const attachedCard = document.getElementById("attachedCard");
const toggleBtn = document.getElementById("toggleBtn");

let currentTab = null;
let isAttached = false;

async function init() {
  // Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTab = tab;

  if (tab) {
    tabTitle.textContent = tab.title || "Untitled";
    tabUrl.textContent = tab.url || "";
  }

  // Check stored state
  const state = await chrome.storage.local.get(["mcpConnected", "attachedTabId"]);
  const connected = state.mcpConnected || false;
  isAttached = (state.attachedTabId === tab?.id);

  if (connected) {
    statusBadge.textContent = "MCP Connected";
    statusBadge.className = "badge badge-online";
  } else {
    statusBadge.textContent = "MCP Waiting";
    statusBadge.className = "badge badge-offline";
  }

  updateAttachUI();
}

function updateAttachUI() {
  if (isAttached) {
    attachedCard.style.display = "block";
    toggleBtn.className = "btn btn-danger";
    toggleBtn.innerHTML = "<span>Detach MCP from Tab</span>";
  } else {
    attachedCard.style.display = "none";
    toggleBtn.className = "btn btn-primary";
    toggleBtn.innerHTML = "<span>Attach MCP to Tab</span>";
  }
}

toggleBtn.addEventListener("click", async () => {
  if (!currentTab) return;

  toggleBtn.disabled = true;

  try {
    if (isAttached) {
      await chrome.debugger.detach({ tabId: currentTab.id });
      isAttached = false;
      await chrome.storage.local.remove("attachedTabId");
    } else {
      await chrome.debugger.attach({ tabId: currentTab.id }, "1.3");
      await chrome.debugger.sendCommand({ tabId: currentTab.id }, "Network.enable");
      await chrome.debugger.sendCommand({ tabId: currentTab.id }, "Console.enable");
      isAttached = true;
      await chrome.storage.local.set({ attachedTabId: currentTab.id });
    }
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    toggleBtn.disabled = false;
    updateAttachUI();
  }
});

init();
