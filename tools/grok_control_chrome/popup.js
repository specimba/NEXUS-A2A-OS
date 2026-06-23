const FIELDS = [
  "enabled",
  "autoContinue",
  "autoSend",
  "bridgeEnabled",
  "maxContinuesPerChat",
  "minUsefulChars",
  "bridgeEndpoint",
  "continuationPrompt"
];

document.addEventListener("DOMContentLoaded", async () => {
  const settings = await chrome.storage.local.get(FIELDS);
  for (const field of FIELDS) {
    const element = document.getElementById(field);
    if (!element) continue;
    if (element.type === "checkbox") {
      element.checked = Boolean(settings[field]);
    } else if (settings[field] !== undefined) {
      element.value = settings[field];
    }
  }
});

document.getElementById("save").addEventListener("click", async () => {
  const settings = {};
  for (const field of FIELDS) {
    const element = document.getElementById(field);
    if (!element) continue;
    settings[field] = element.type === "checkbox" ? element.checked : element.value;
  }
  settings.maxContinuesPerChat = Number(settings.maxContinuesPerChat || 3);
  settings.minUsefulChars = Number(settings.minUsefulChars || 900);
  await chrome.runtime.sendMessage({ type: "NEXUS_GROK_SETTINGS_UPDATED", settings });
  document.getElementById("status").textContent = "Saved.";
});
