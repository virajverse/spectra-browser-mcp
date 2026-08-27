// SpectraBrowser MCP Chrome Extension — Background Service Worker
// Connects to local MCP WebSocket bridge and controls tabs via chrome.debugger

const MCP_WS_URL = "ws://127.0.0.1:8765/extension_ws";
let ws = null;
let attachedTabId = null;
let reconnectTimer = null;
let isConnected = false;

// ─── WebSocket Connection Management ───
function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    return;
  }

  try {
    ws = new WebSocket(MCP_WS_URL);
  } catch (e) {
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    isConnected = true;
    console.log("[SpectraBridge] Connected to MCP server at", MCP_WS_URL);
    chrome.storage.local.set({ mcpConnected: true });
    updateBadge("ON", "#10B981");

    // Send initial status and tab list
    sendTabList();
  };

  ws.onclose = () => {
    isConnected = false;
    console.log("[SpectraBridge] Disconnected from MCP server");
    chrome.storage.local.set({ mcpConnected: false });
    updateBadge("OFF", "#EF4444");
    scheduleReconnect();
  };

  ws.onerror = (err) => {
    console.warn("[SpectraBridge] WebSocket error:", err);
  };

  ws.onmessage = async (event) => {
    try {
      const msg = JSON.parse(event.data);
      await handleMcpMessage(msg);
    } catch (e) {
      console.error("[SpectraBridge] Error parsing message:", e);
    }
  };
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    connectWebSocket();
  }, 2500);
}

function updateBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
}

// Keep-alive heartbeat every 20 seconds
setInterval(() => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping", timestamp: Date.now() }));
  } else {
    connectWebSocket();
  }
}, 20000);

// ─── Message Handling from MCP Server ───
async function handleMcpMessage(msg) {
  const { id, command, params } = msg;

  if (msg.type === "ping") {
    sendResponse(id, { pong: true });
    return;
  }

  try {
    let result = null;

    switch (command) {
      case "get_status":
        result = await getStatus();
        break;

      case "list_tabs":
        result = await listTabs();
        break;

      case "attach_tab":
        result = await attachToTab(params?.tabId);
        break;

      case "detach_tab":
        result = await detachTab();
        break;

      case "navigate":
        result = await navigateTab(params?.url, params?.tabId);
        break;

      case "screenshot":
        result = await captureScreenshot();
        break;

      case "inspect_page":
        result = await inspectPage(params?.tabId);
        break;

      case "click":
        result = await clickElement(params?.target, params?.tabId);
        break;

      case "type":
        result = await typeElement(params?.target, params?.value, params?.tabId);
        break;

      case "press_key":
        result = await pressKey(params?.key, params?.tabId);
        break;

      case "extract_images":
        result = await extractImages(params?.tabId);
        break;

      case "cdp_command":
        result = await executeCdpCommand(params?.method, params?.params, params?.tabId);
        break;

      default:
        throw new Error(`Unknown command: ${command}`);
    }

    sendResponse(id, { success: true, data: result });
  } catch (err) {
    sendResponse(id, { success: false, error: err.message || String(err) });
  }
}

function sendResponse(id, payload) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ id, ...payload }));
  }
}

function sendEvent(eventType, payload) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "event", eventType, payload }));
  }
}

// ─── Browser Capabilities ───

async function getStatus() {
  const activeTab = await getActiveTab();
  return {
    connected: isConnected,
    attachedTabId,
    activeTab: activeTab ? { id: activeTab.id, title: activeTab.title, url: activeTab.url } : null
  };
}

async function listTabs() {
  const tabs = await chrome.tabs.query({});
  return tabs.map(t => ({
    id: t.id,
    title: t.title,
    url: t.url,
    active: t.active,
    attached: t.id === attachedTabId
  }));
}

async function sendTabList() {
  const tabs = await listTabs();
  sendEvent("tab_list_updated", { tabs });
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function attachToTab(targetTabId) {
  let tabId = targetTabId;
  if (!tabId) {
    const active = await getActiveTab();
    if (!active) throw new Error("No active tab found to attach.");
    tabId = active.id;
  }

  // If already attached to another tab, detach first
  if (attachedTabId && attachedTabId !== tabId) {
    try { await chrome.debugger.detach({ tabId: attachedTabId }); } catch (e) {}
  }

  try {
    await chrome.debugger.attach({ tabId }, "1.3");
    attachedTabId = tabId;

    // Enable telemetry domains
    await chrome.debugger.sendCommand({ tabId }, "Network.enable");
    await chrome.debugger.sendCommand({ tabId }, "Console.enable");
    await chrome.debugger.sendCommand({ tabId }, "Page.enable");
    await chrome.debugger.sendCommand({ tabId }, "Runtime.enable");

    chrome.storage.local.set({ attachedTabId });
    const tab = await chrome.tabs.get(tabId);
    return { attached: true, tabId, title: tab.title, url: tab.url };
  } catch (err) {
    attachedTabId = null;
    throw new Error(`Failed to attach debugger: ${err.message}`);
  }
}

async function detachTab() {
  if (!attachedTabId) return { detached: true };
  try {
    await chrome.debugger.detach({ tabId: attachedTabId });
  } catch (e) {}
  const oldId = attachedTabId;
  attachedTabId = null;
  chrome.storage.local.remove("attachedTabId");
  return { detached: true, tabId: oldId };
}

async function ensureAttached(tabId) {
  if (!attachedTabId) {
    await attachToTab(tabId);
  }
  return attachedTabId;
}

async function navigateTab(url, tabId) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available to navigate.");

  await chrome.tabs.update(id, { url });

  // Wait for load event
  return new Promise((resolve) => {
    const listener = (updatedId, changeInfo) => {
      if (updatedId === id && changeInfo.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        chrome.tabs.get(id).then(tab => {
          resolve({ success: true, url: tab.url, title: tab.title });
        });
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
    // Timeout fallback: 15s
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      chrome.tabs.get(id).then(tab => {
        resolve({ success: true, url: tab?.url, title: tab?.title, note: "Navigation timed out waiting for complete" });
      }).catch(() => resolve({ success: true }));
    }, 15000);
  });
}

async function captureScreenshot() {
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: "png" });
    return { dataUrl };
  } catch (err) {
    throw new Error(`Screenshot failed: ${err.message}`);
  }
}

async function executeCdpCommand(method, params = {}, tabId = null) {
  const id = await ensureAttached(tabId);
  return await chrome.debugger.sendCommand({ tabId: id }, method, params);
}

// ─── DOM Inspection & Element Resolution ───
async function inspectPage(tabId) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available to inspect.");

  // Inject observer script to extract semantic DOM elements
  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    func: extractPageElements
  });

  return results?.[0]?.result || { interactive_elements: [], forms: [], text: "" };
}

function extractPageElements() {
  const elements = [];
  let refCount = 1;

  // Buttons, links, inputs, selects, textareas
  const selector = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="textbox"], [role="combobox"], [contenteditable="true"]';
  document.querySelectorAll(selector).forEach(el => {
    // Visibility check
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;

    const refId = `@${refCount++}`;
    el.setAttribute('data-spectra-ref', refId);

    const name = el.innerText?.trim() || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.value || el.name || '';
    const role = el.getAttribute('role') || el.tagName.toLowerCase();

    elements.push({
      ref_id: refId,
      role: role,
      name: name.substring(0, 100),
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
    });
  });

  // Forms
  const forms = [];
  document.querySelectorAll('form').forEach((f, idx) => {
    const inputs = [];
    f.querySelectorAll('input, select, textarea').forEach(i => {
      inputs.push({
        name: i.name || i.id || '',
        type: i.type || 'text',
        ref_id: i.getAttribute('data-spectra-ref') || ''
      });
    });
    forms.push({ form_id: f.id || `form_${idx + 1}`, inputs });
  });

  return {
    url: window.location.href,
    title: document.title,
    interactive_elements: elements,
    forms: forms,
    text: document.body.innerText?.substring(0, 2000) || ''
  };
}

async function clickElement(target, tabId) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [target],
    func: (targetStr) => {
      let el = null;
      if (targetStr.startsWith('@')) {
        el = document.querySelector(`[data-spectra-ref="${targetStr}"]`);
      } else {
        el = document.querySelector(targetStr);
      }
      if (!el) {
        // Fallback: search by text
        const all = document.querySelectorAll('button, a, input[type="submit"]');
        for (const candidate of all) {
          if (candidate.innerText?.trim().toLowerCase().includes(targetStr.toLowerCase())) {
            el = candidate;
            break;
          }
        }
      }
      if (!el) return { success: false, error: `Element not found: ${targetStr}` };

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.click();
      return { success: true, clicked: targetStr };
    }
  });

  return results?.[0]?.result || { success: false, error: "Script execution returned null" };
}

async function typeElement(target, value, tabId) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [target, value],
    func: (targetStr, val) => {
      let el = null;
      if (targetStr.startsWith('@')) {
        el = document.querySelector(`[data-spectra-ref="${targetStr}"]`);
      } else {
        el = document.querySelector(targetStr);
      }
      if (!el) return { success: false, error: `Element not found: ${targetStr}` };

      el.focus();
      if (el.isContentEditable || el.getAttribute('contenteditable') === 'true') {
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, val);
      } else {
        el.value = val;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }
      return { success: true, typed: targetStr };
    }
  });

  return results?.[0]?.result || { success: false, error: "Script execution returned null" };
}

async function pressKey(key, tabId) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  return await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [key],
    func: (keyName) => {
      const active = document.activeElement || document.body;
      const isEnter = keyName.toLowerCase() === 'enter';
      const eventInit = {
        key: isEnter ? 'Enter' : keyName,
        code: isEnter ? 'Enter' : keyName,
        which: isEnter ? 13 : 0,
        keyCode: isEnter ? 13 : 0,
        bubbles: true,
        cancelable: true
      };
      active.dispatchEvent(new KeyboardEvent('keydown', eventInit));
      active.dispatchEvent(new KeyboardEvent('keypress', eventInit));
      active.dispatchEvent(new KeyboardEvent('keyup', eventInit));
      return { success: true, key: keyName };
    }
  });
}

async function extractImages(tabId) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  // Step 1: Scan DOM in page context
  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    func: async () => {
      const imgs = Array.from(document.querySelectorAll('img'));
      const output = [];

      for (const img of imgs) {
        // Skip tiny icons, tracking pixels, and empty sources
        const w = img.naturalWidth || img.width || 0;
        const h = img.naturalHeight || img.height || 0;
        if (!img.src || img.src.startsWith('data:image/svg') || (w < 80 && h < 80)) {
          continue;
        }

        let base64Data = null;

        // Try in-page blob fetch
        try {
          const res = await fetch(img.src);
          const blob = await res.blob();
          base64Data = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.readAsDataURL(blob);
          });
        } catch (e) {
          // Try canvas draw as fallback
          try {
            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            base64Data = canvas.toDataURL('image/png');
          } catch (e2) {}
        }

        output.push({
          src: img.src,
          alt: img.alt || '',
          naturalWidth: w,
          naturalHeight: h,
          base64: base64Data
        });
      }

      return output;
    }
  });

  const candidates = results?.[0]?.result || [];

  // Step 2: For any images where in-page fetch failed due to CORS,
  // fetch in background script context (bypasses CORS via host_permissions: <all_urls>)
  for (const item of candidates) {
    if (!item.base64 && item.src && !item.src.startsWith('blob:')) {
      try {
        const resp = await fetch(item.src);
        const blob = await resp.blob();
        const buffer = await blob.arrayBuffer();
        const bytes = new Uint8Array(buffer);
        let binary = '';
        const len = bytes.byteLength;
        // Batch convert to avoid call stack limits on huge images
        const chunkSize = 8192;
        for (let i = 0; i < len; i += chunkSize) {
          binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
        }
        const b64 = btoa(binary);
        const mime = blob.type || 'image/png';
        item.base64 = `data:${mime};base64,${b64}`;
      } catch (err) {
        console.warn("[SpectraBridge] Background fetch failed for:", item.src, err);
      }
    }
  }

  // Filter only successfully extracted images
  return candidates.filter(i => i.base64 && i.base64.length > 100);
}

// ─── Chrome Debugger Event Forwarder ───
chrome.debugger.onEvent.addListener((source, method, params) => {
  if (source.tabId === attachedTabId) {
    sendEvent("cdp_event", { method, params, tabId: source.tabId });
  }
});

chrome.debugger.onDetach.addListener((source, reason) => {
  if (source.tabId === attachedTabId) {
    attachedTabId = null;
    chrome.storage.local.remove("attachedTabId");
    sendEvent("debugger_detached", { tabId: source.tabId, reason });
  }
});

// Auto-start on extension launch
connectWebSocket();
