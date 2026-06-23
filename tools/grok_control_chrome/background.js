const DEFAULT_SETTINGS = Object.freeze({
  enabled: true,
  bridgeEnabled: false,
  bridgeEndpoint: "http://127.0.0.1:7352/api/grok-control/events",
  pollPeriodMinutes: 1,
  autoContinue: false,
  autoSend: false,
  maxContinuesPerChat: 3,
  minUsefulChars: 900,
  quietMillisAfterMutation: 3500,
  continuationPrompt:
    "Continue the task. Be evidence-grounded, avoid surface sweep, and produce concrete next artifacts. If blocked, state exact blocker and next probe."
});

chrome.runtime.onInstalled.addListener(async () => {
  const existing = await chrome.storage.local.get(Object.keys(DEFAULT_SETTINGS));
  await chrome.storage.local.set({ ...DEFAULT_SETTINGS, ...existing });
  await resetAlarm();
});

chrome.runtime.onStartup.addListener(resetAlarm);

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "nexus-grok-control-poll") return;
  await pollGrokTabs();
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: String(error) }));
  return true;
});

async function resetAlarm() {
  const settings = await getSettings();
  await chrome.alarms.clear("nexus-grok-control-poll");
  if (!settings.enabled) return;
  chrome.alarms.create("nexus-grok-control-poll", {
    periodInMinutes: Math.max(1, Number(settings.pollPeriodMinutes) || 1)
  });
}

async function pollGrokTabs() {
  const settings = await getSettings();
  if (!settings.enabled) return;
  const tabs = await chrome.tabs.query({ url: ["https://grok.com/*", "https://*.grok.com/*"] });
  for (const tab of tabs) {
    if (!tab.id) continue;
    try {
      await chrome.tabs.sendMessage(tab.id, { type: "NEXUS_GROK_CHECK", settings });
    } catch (_error) {
      // Tab may not be ready or content script may not be injected yet.
    }
  }
}

async function handleMessage(message, sender) {
  if (!message || typeof message !== "object") return { ok: false, error: "invalid_message" };
  if (message.type === "NEXUS_GROK_SETTINGS_UPDATED") {
    await chrome.storage.local.set(message.settings || {});
    await resetAlarm();
    return { ok: true };
  }
  if (message.type === "NEXUS_GROK_STATE") {
    const payload = normalizeState(message.payload, sender);
    await chrome.storage.local.set({ lastGrokState: payload });
    const settings = await getSettings();
    if (settings.bridgeEnabled) {
      await postToBridge(settings.bridgeEndpoint, payload);
    }
    return { ok: true };
  }
  return { ok: false, error: "unknown_message_type" };
}

async function getSettings() {
  const stored = await chrome.storage.local.get(Object.keys(DEFAULT_SETTINGS));
  return { ...DEFAULT_SETTINGS, ...stored };
}

function normalizeState(payload, sender) {
  const safePayload = payload && typeof payload === "object" ? payload : {};
  return {
    kind: "grok_control_state",
    generated_at: new Date().toISOString(),
    tab_id: sender.tab?.id || null,
    url: sender.tab?.url || "",
    status: safePayload.status || "unknown",
    response_chars: Number(safePayload.response_chars || 0),
    continue_count: Number(safePayload.continue_count || 0),
    surface_sweep_suspected: Boolean(safePayload.surface_sweep_suspected),
    action_taken: safePayload.action_taken || "none",
    preview: String(safePayload.preview || "").slice(0, 500)
  };
}

async function postToBridge(endpoint, payload) {
  const parsed = new URL(endpoint);
  if (parsed.protocol !== "http:" || parsed.hostname !== "127.0.0.1") {
    throw new Error("bridge_endpoint_must_be_localhost_http");
  }
  await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}
