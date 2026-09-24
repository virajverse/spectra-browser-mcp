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

  ws.onopen = async () => {
    isConnected = true;
    console.log("[SpectraBridge] Connected to MCP server at", MCP_WS_URL);
    chrome.storage.local.set({ mcpConnected: true });
    updateBadge("ON", "#10B981");

    // Send initial status and tab list
    await sendTabList();
    try {
      await ensureAttached();
    } catch (e) {
      console.warn("[SpectraBridge] Auto-attach deferred:", e);
    }
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

// Lifecycle & runtime message handlers
chrome.runtime.onInstalled.addListener(() => {
  connectWebSocket();
});

chrome.runtime.onStartup.addListener(() => {
  connectWebSocket();
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "ensure_connected" || message.action === "reconnect") {
    connectWebSocket();
    sendResponse({ connected: isConnected });
  }
  return true;
});

// Connect immediately on extension startup
connectWebSocket();


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

      case "reload":
        result = await reloadTab(params?.ignore_cache !== false, params?.tabId);
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

      case "scroll":
        result = await scrollPage(params?.direction, params?.amount, params?.target, params?.tabId);
        break;

      case "select":
        result = await selectOption(params?.target, params?.option, params?.tabId);
        break;

      case "wait_for":
        result = await waitForElement(params?.target, params?.state, params?.timeout_ms, params?.tabId);
        break;

      case "wait_idle":
        result = await waitIdle(params?.timeout_ms, params?.tabId);
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
  const isInternal = (url) => !url || url.startsWith('chrome://') || url.startsWith('chrome-extension://') || url.startsWith('edge://') || url.startsWith('about:');

  let tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  let tab = tabs.find(t => !isInternal(t.url));

  if (!tab) {
    tabs = await chrome.tabs.query({ active: true });
    tab = tabs.find(t => !isInternal(t.url));
  }
  if (!tab) {
    const all = await chrome.tabs.query({});
    tab = all.reverse().find(t => !isInternal(t.url)) || all[0];
  }
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

async function reloadTab(ignoreCache = true, tabId = null) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available to reload.");

  // 1. Ensure debugger is attached with Network and Console telemetry enabled
  await ensureAttached(id);

  // 2. Trigger reload (with optional cache bypass)
  await chrome.tabs.reload(id, { bypassCache: ignoreCache });

  // 3. Wait for load completion
  return new Promise((resolve) => {
    const listener = (updatedId, changeInfo) => {
      if (updatedId === id && changeInfo.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        chrome.tabs.get(id).then(tab => {
          resolve({ success: true, url: tab.url, title: tab.title, reloaded: true, debugger_attached: true });
        });
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      chrome.tabs.get(id).then(tab => {
        resolve({ success: true, url: tab?.url, title: tab?.title, reloaded: true, note: "Reload timed out waiting for complete" });
      }).catch(() => resolve({ success: true }));
    }, 15000);
  });
}

async function captureScreenshot(tabId = null) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  
  // 1. Primary Attempt: chrome.tabs.captureVisibleTab
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: "png" });
    if (dataUrl && dataUrl.startsWith("data:image/")) {
      return { dataUrl };
    }
  } catch (e) {
    console.warn("[SpectraBridge] captureVisibleTab failed, trying CDP fallback:", e);
  }

  // 2. Resilient Fallback: CDP Page.captureScreenshot (Works even if window is unfocused or in background!)
  try {
    const activeTabId = await ensureAttached(id);
    const result = await chrome.debugger.sendCommand({ tabId: activeTabId }, "Page.captureScreenshot", { format: "png" });
    if (result && result.data) {
      return { dataUrl: `data:image/png;base64,${result.data}` };
    }
  } catch (cdpErr) {
    console.error("[SpectraBridge] CDP Page.captureScreenshot failed:", cdpErr);
  }

  throw new Error("Screenshot failed: Ensure Chrome has an active open tab and Spectra extension is loaded.");
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

  // Buttons, links, inputs, selects, textareas, images
  const selector = 'a, button, input, select, textarea, img, [role="button"], [role="link"], [role="textbox"], [role="combobox"], [contenteditable="true"]';
  document.querySelectorAll(selector).forEach(el => {
    // Visibility check
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;

    const refId = `@${refCount++}`;
    el.setAttribute('data-spectra-ref', refId);

    let name = el.innerText?.trim() || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.value || el.name || '';
    if (el.tagName.toLowerCase() === 'img') {
      const cleanSrc = (el.src && el.src.startsWith('http')) ? el.src : '';
      name = `${el.alt || 'Image'}|||${el.naturalWidth}x${el.naturalHeight}|||${cleanSrc}`;
    }
    const role = el.getAttribute('role') || el.tagName.toLowerCase();

    elements.push({
      ref_id: refId,
      role: role,
      name: el.tagName.toLowerCase() === 'img' ? name : name.substring(0, 100),
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      attributes: { src: el.src || '' },
      src: el.src || ''
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
    func: async (targetStr) => {
      let el = null;
      let targetX = null;
      let targetY = null;

      // 1. Check if target is coordinate format "x, y" (e.g. "540, 720" from visual screenshot inspection)
      if (typeof targetStr === 'string' && /^\s*\d+\s*,\s*\d+\s*$/.test(targetStr)) {
        const [px, py] = targetStr.split(',').map(n => parseInt(n.trim(), 10));
        targetX = px;
        targetY = py;
        el = document.elementFromPoint(px, py) || document.body;
      } else if (targetStr.startsWith('@')) {
        el = document.querySelector(`[data-spectra-ref="${targetStr}"]`);
      } else {
        el = document.querySelector(targetStr);
      }

      if (!el) {
        // Fallback: search by visible text / aria-label
        const all = document.querySelectorAll('button, a, input[type="submit"], [role="button"], [role="link"], [role="tab"]');
        for (const candidate of all) {
          if (candidate.innerText?.trim().toLowerCase().includes(targetStr.toLowerCase()) ||
              candidate.getAttribute('aria-label')?.toLowerCase().includes(targetStr.toLowerCase())) {
            el = candidate;
            break;
          }
        }
      }
      if (!el) return { success: false, error: `Element not found: ${targetStr}` };

      // Direct image download support
      if (el.tagName.toLowerCase() === 'img') {
        const cleanName = (el.alt || 'extracted_image').replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 50);
        return new Promise((resolve) => {
          fetch(el.src, { credentials: 'include' })
            .then(res => res.blob())
            .then(blob => {
              const blobUrl = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = blobUrl;
              a.download = `${cleanName}.png`;
              document.body.appendChild(a);
              a.click();
              setTimeout(() => {
                a.remove();
                URL.revokeObjectURL(blobUrl);
                resolve({ success: true, downloaded: el.src, size: blob.size, name: `${cleanName}.png` });
              }, 500);
            })
            .catch(err => {
              resolve({ success: false, error: err.message });
            });
        });
      }

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise(r => setTimeout(r, 60));

      // Calculate realistic human click coordinates with subtle jitter
      const rect = el.getBoundingClientRect();
      const jitterX = (Math.random() - 0.5) * Math.min(6, rect.width * 0.2);
      const jitterY = (Math.random() - 0.5) * Math.min(6, rect.height * 0.2);
      const clientX = targetX !== null ? targetX : Math.round(rect.left + rect.width / 2 + jitterX);
      const clientY = targetY !== null ? targetY : Math.round(rect.top + rect.height / 2 + jitterY);

      const mouseInit = {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX,
        clientY,
        screenX: clientX + (window.screenX || 0),
        screenY: clientY + (window.screenY || 0),
        button: 0,
        buttons: 1
      };

      // 1. Natural Hover / Mouse Move
      el.dispatchEvent(new PointerEvent('pointerover', mouseInit));
      el.dispatchEvent(new MouseEvent('mouseover', mouseInit));
      el.dispatchEvent(new PointerEvent('pointerenter', mouseInit));
      el.dispatchEvent(new MouseEvent('mouseenter', mouseInit));
      el.dispatchEvent(new PointerEvent('pointermove', mouseInit));
      el.dispatchEvent(new MouseEvent('mousemove', mouseInit));

      // 2. Human touch/press down delay (40ms - 70ms)
      const pressDelay = Math.floor(Math.random() * 30) + 40;
      await new Promise(r => setTimeout(r, pressDelay));

      // 3. Pointer & Mouse Down
      el.dispatchEvent(new PointerEvent('pointerdown', mouseInit));
      el.dispatchEvent(new MouseEvent('mousedown', mouseInit));

      // 4. Focus element naturally
      if (typeof el.focus === 'function') {
        el.focus();
      }

      // 5. Short hold duration before release (30ms - 50ms)
      await new Promise(r => setTimeout(r, Math.floor(Math.random() * 20) + 30));

      // 6. Pointer & Mouse Up
      const upInit = { ...mouseInit, buttons: 0 };
      el.dispatchEvent(new PointerEvent('pointerup', upInit));
      el.dispatchEvent(new MouseEvent('mouseup', upInit));

      // 7. Click event
      el.dispatchEvent(new MouseEvent('click', upInit));

      // 8. Native DOM click fallback if not handled
      if (typeof el.click === 'function') {
        el.click();
      }

      return { success: true, clicked: targetStr, coordinates: { x: clientX, y: clientY } };
    }
  });

  return results?.[0]?.result || { success: false, error: "Script execution returned null" };
}

async function typeElement(target, value, clear = false, tabId = null) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [target, value, clear],
    func: async (targetStr, val, shouldClear) => {
      let el = null;
      if (targetStr.startsWith('@')) {
        el = document.querySelector(`[data-spectra-ref="${targetStr}"]`);
      } else {
        el = document.querySelector(targetStr);
      }
      if (!el) {
        const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        for (const input of inputs) {
          const placeholder = input.getAttribute('placeholder') || '';
          const name = input.getAttribute('name') || '';
          const aria = input.getAttribute('aria-label') || '';
          if (placeholder.toLowerCase().includes(targetStr.toLowerCase()) || 
              name.toLowerCase().includes(targetStr.toLowerCase()) ||
              aria.toLowerCase().includes(targetStr.toLowerCase())) {
            el = input;
            break;
          }
        }
      }
      if (!el) return { success: false, error: `Element not found: ${targetStr}` };

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise(r => setTimeout(r, 50));
      el.focus();

      const isContentEditable = el.isContentEditable || el.getAttribute('contenteditable') === 'true';

      if (isContentEditable) {
        if (shouldClear) {
          document.execCommand('selectAll', false, null);
          document.execCommand('delete', false, null);
        }
        // Human-like character insertion with natural keystroke timing
        for (let i = 0; i < val.length; i++) {
          const char = val[i];
          document.execCommand('insertText', false, char);
          el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: char }));
          // Human typing rhythm: 15ms - 45ms per keystroke
          const delay = Math.floor(Math.random() * 30) + 15;
          await new Promise(r => setTimeout(r, delay));
        }
      } else {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
        const nativeTextAreaSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
        const setter = el.tagName.toLowerCase() === 'textarea' ? nativeTextAreaSetter : nativeInputValueSetter;
        
        let current = shouldClear ? '' : el.value;
        if (setter) {
          setter.call(el, current);
        } else {
          el.value = current;
        }

        for (let i = 0; i < val.length; i++) {
          const char = val[i];
          current += char;
          if (setter) {
            setter.call(el, current);
          } else {
            el.value = current;
          }

          el.dispatchEvent(new KeyboardEvent('keydown', { key: char, code: `Key${char.toUpperCase()}`, bubbles: true }));
          el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: char }));
          el.dispatchEvent(new KeyboardEvent('keyup', { key: char, code: `Key${char.toUpperCase()}`, bubbles: true }));

          // Human typing rhythm: 15ms - 45ms per keystroke
          const delay = Math.floor(Math.random() * 30) + 15;
          await new Promise(r => setTimeout(r, delay));
        }

        el.dispatchEvent(new Event('change', { bubbles: true }));
      }

      return { success: true, typed: val, target: targetStr };
    }
  });

  return results?.[0]?.result || { success: false, error: "Script execution returned null" };
}

async function selectOption(target, option, tabId = null) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [target, option],
    func: (targetStr, opt) => {
      let el = targetStr.startsWith('@') ? document.querySelector(`[data-spectra-ref="${targetStr}"]`) : document.querySelector(targetStr);
      if (!el) return { success: false, error: `Select element not found: ${targetStr}` };

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();

      if (el.tagName.toLowerCase() === 'select') {
        let matched = false;
        for (const o of el.options) {
          if (o.value === opt || o.text.trim().toLowerCase() === opt.toLowerCase()) {
            el.value = o.value;
            matched = true;
            break;
          }
        }
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return { success: matched, selected: opt };
      }

      el.click();
      return { success: true, clicked_dropdown: targetStr };
    }
  });

  return results?.[0]?.result || { success: false };
}

async function waitForElement(target, state = "visible", timeoutMs = 15000, tabId = null) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [target, state, timeoutMs],
    func: async (targetStr, targetState, timeout) => {
      const start = Date.now();
      while (Date.now() - start < timeout) {
        let el = targetStr.startsWith('@') ? document.querySelector(`[data-spectra-ref="${targetStr}"]`) : document.querySelector(targetStr);
        if (!el) {
          const all = Array.from(document.querySelectorAll('*'));
          el = all.find(c => c.innerText?.trim().toLowerCase().includes(targetStr.toLowerCase()));
        }

        const isAttached = Boolean(el && el.isConnected);
        let isVisible = false;
        if (isAttached) {
          const style = window.getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0;
        }

        if (targetState === 'visible' && isVisible) return { success: true, elapsed_ms: Date.now() - start };
        if (targetState === 'attached' && isAttached) return { success: true, elapsed_ms: Date.now() - start };
        if (targetState === 'hidden' && !isVisible) return { success: true, elapsed_ms: Date.now() - start };

        await new Promise(r => setTimeout(r, 200));
      }
      return { success: false, error: `Timeout waiting for '${targetStr}' to become ${targetState}` };
    }
  });

  return results?.[0]?.result || { success: false };
}

async function waitIdle(timeoutMs = 10000, tabId = null) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [timeoutMs],
    func: async (timeout) => {
      return new Promise((resolve) => {
        let lastMutation = Date.now();
        const start = Date.now();
        const observer = new MutationObserver(() => {
          lastMutation = Date.now();
        });
        observer.observe(document.body, { childList: true, subtree: true, attributes: true });

        const checkInterval = setInterval(() => {
          const idleTime = Date.now() - lastMutation;
          if (idleTime >= 500 || Date.now() - start >= timeout) {
            clearInterval(checkInterval);
            observer.disconnect();
            resolve({ success: true, idle_ms: idleTime });
          }
        }, 100);
      });
    }
  });

  return results?.[0]?.result || { success: true };
}

async function scrollPage(direction = "down", amount = 600, target = null, tabId = null) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available to scroll.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [direction, amount, target],
    func: async (dir, amt, tgt) => {
      // 1. If explicit target is specified (@ref, #id, .class), scroll that element
      if (tgt) {
        let el = tgt.startsWith('@') ? document.querySelector(`[data-spectra-ref="${tgt}"]`) : document.querySelector(tgt);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          return { success: true, scrolled_to: tgt };
        }
      }

      const totalScrollY = (dir && dir.toLowerCase() === 'up') ? -amt : amt;

      // 2. Discover candidate scrollable containers
      const allScrollables = Array.from(document.querySelectorAll('*')).filter(el => {
        const style = window.getComputedStyle(el);
        const isScrollable = (style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight;
        if (!isScrollable) return false;
        
        const rect = el.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return false;
        return true;
      });

      // Filter out sidebars, navigation trees, history lists unless they occupy the full screen
      const contentScrollables = allScrollables.filter(el => {
        if (el.closest('nav, aside, [role="navigation"], [aria-label*="sidebar"], [aria-label*="history"]')) {
          return false;
        }
        const rect = el.getBoundingClientRect();
        if (rect.left < 50 && rect.width < 340 && window.innerWidth > 768) {
          return false; // Ignored left history sidebar
        }
        return true;
      });

      // Pick the primary content container (check <main>, [role="main"], or largest surface area)
      let primaryContainer = document.querySelector('main, [role="main"], article, .chat-container, [role="presentation"]');
      if (!primaryContainer || !contentScrollables.includes(primaryContainer)) {
        if (contentScrollables.length > 0) {
          // Sort by visible surface area descending
          contentScrollables.sort((a, b) => {
            const rectA = a.getBoundingClientRect();
            const rectB = b.getBoundingClientRect();
            return (rectB.width * rectB.height) - (rectA.width * rectA.height);
          });
          primaryContainer = contentScrollables[0];
        }
      }

      const targetContainer = primaryContainer || window;

      // 3. Human-like Eased Incremental Scrolling (6 micro-steps)
      const steps = 6;
      const stepDelay = 25; // ms
      for (let i = 1; i <= steps; i++) {
        const progress = Math.sin((i / steps) * (Math.PI / 2));
        const prevProgress = Math.sin(((i - 1) / steps) * (Math.PI / 2));
        const delta = Math.round(totalScrollY * (progress - prevProgress));

        if (targetContainer === window) {
          window.scrollBy({ top: delta, behavior: 'instant' });
        } else {
          targetContainer.scrollBy({ top: delta, behavior: 'instant' });
          targetContainer.dispatchEvent(new WheelEvent('wheel', { deltaY: delta, deltaMode: 0, bubbles: true }));
        }
        await new Promise(r => setTimeout(r, stepDelay));
      }

      return {
        success: true,
        scrolled_by: totalScrollY,
        container: targetContainer === window ? 'window' : (targetContainer.tagName.toLowerCase() + (targetContainer.className ? `.${targetContainer.className.split(' ')[0]}` : ''))
      };
    }
  });

  return results?.[0]?.result || { success: true };
}

async function pressKey(key, tabId) {
  const id = tabId || attachedTabId || (await getActiveTab())?.id;
  if (!id) throw new Error("No tab available.");

  return await chrome.scripting.executeScript({
    target: { tabId: id },
    args: [key],
    func: async (keyName) => {
      const active = document.activeElement || document.body;
      const isEnter = keyName.toLowerCase() === 'enter';
      const isTab = keyName.toLowerCase() === 'tab';
      const isEscape = keyName.toLowerCase() === 'escape';

      let code = keyName;
      let keyCode = 0;
      if (isEnter) { code = 'Enter'; keyCode = 13; }
      else if (isTab) { code = 'Tab'; keyCode = 9; }
      else if (isEscape) { code = 'Escape'; keyCode = 27; }
      else if (keyName === 'ArrowDown') { keyCode = 40; }
      else if (keyName === 'ArrowUp') { keyCode = 38; }

      const eventInit = {
        key: keyName,
        code: code,
        keyCode: keyCode,
        which: keyCode,
        bubbles: true,
        cancelable: true,
        view: window
      };

      active.dispatchEvent(new KeyboardEvent('keydown', eventInit));
      if (keyCode === 13 || keyName.length === 1) {
        active.dispatchEvent(new KeyboardEvent('keypress', eventInit));
      }
      await new Promise(r => setTimeout(r, 40));
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
      const allImgs = Array.from(document.querySelectorAll('img')).filter(img => {
        if (!img.src || img.src.startsWith('data:image/svg')) return false;
        const w = img.naturalWidth || img.width || 0;
        const h = img.naturalHeight || img.height || 0;
        if (w > 0 && w < 300 && h > 0 && h < 300) return false;
        return true;
      });

      // Sort by area descending so highest resolution images are prioritized
      allImgs.sort((a, b) => {
        const areaA = (a.naturalWidth || a.width || 0) * (a.naturalHeight || a.height || 0);
        const areaB = (b.naturalWidth || b.width || 0) * (b.naturalHeight || b.height || 0);
        return areaB - areaA;
      });

      // Deduplicate by clean URL (strip transient signature but keep unique file identifier)
      const uniqueMap = new Map();
      for (const img of allImgs) {
        const key = (img.src || '').split('&sig=')[0];
        if (key && !uniqueMap.has(key)) {
          uniqueMap.set(key, img);
        }
      }

      const topImgs = Array.from(uniqueMap.values()).slice(0, 5);
      const output = [];

      for (const img of topImgs) {
        const w = img.naturalWidth || img.width || 0;
        const h = img.naturalHeight || img.height || 0;
        let base64Data = null;

        // Try in-page blob fetch with credentials
        try {
          const res = await fetch(img.src, { credentials: 'include' });
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
            canvas.width = img.naturalWidth || img.width || 800;
            canvas.height = img.naturalHeight || img.height || 600;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            base64Data = canvas.toDataURL('image/png');
          } catch (e2) {}
        }

        output.push({
          src: img.src,
          alt: img.alt || '',
          naturalWidth: img.naturalWidth || w,
          naturalHeight: img.naturalHeight || h,
          base64: base64Data
        });
      }

      return output;
    }
  });

  const candidates = results?.[0]?.result || [];

  // Step 2: For any images where in-page fetch failed due to CORS,
  // fetch in background script context with credentials (bypasses CORS via host_permissions: <all_urls>)
  const MAX_IMAGES = 5;
  const remaining = Math.max(0, MAX_IMAGES - candidates.filter(i => i.base64).length);
  const needsFetch = candidates.filter(i => !i.base64 && i.src && !i.src.startsWith('blob:'));
  const toFetch = needsFetch.slice(0, remaining);

  for (const item of toFetch) {
      try {
        const resp = await fetch(item.src, { credentials: 'include' });
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

  // Return images that have base64 data or valid image src URLs (max 20)
  return candidates.filter(i => (i.base64 && i.base64.length > 100) || (i.src && i.src.startsWith('http'))).slice(0, 20);
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

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  if (isConnected) {
    try {
      const tab = await chrome.tabs.get(activeInfo.tabId);
      if (tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('chrome-extension://')) {
        await attachToTab(activeInfo.tabId);
      }
    } catch (e) {}
  }
});

// Auto-start on extension launch
connectWebSocket();
