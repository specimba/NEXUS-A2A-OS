const STATE = {
  lastMutationAt: Date.now(),
  continueCount: 0,
  lastSignature: "",
  lastActionAt: 0
};

const observer = new MutationObserver(() => {
  STATE.lastMutationAt = Date.now();
});

observer.observe(document.documentElement, {
  childList: true,
  subtree: true,
  characterData: true
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "NEXUS_GROK_CHECK") return;
  const settings = message.settings || {};
  const result = checkAndMaybeContinue(settings);
  sendResponse(result);
});

function checkAndMaybeContinue(settings) {
  const snapshot = inspectPage(settings);
  let actionTaken = "observe_only";

  if (shouldContinue(snapshot, settings)) {
    if (settings.autoSend === true) {
      actionTaken = sendContinuation(settings.continuationPrompt) ? "auto_continue_sent" : "auto_continue_failed";
    } else {
      actionTaken = draftContinuation(settings.continuationPrompt) ? "continue_drafted" : "continue_draft_failed";
    }
    STATE.continueCount += actionTaken.endsWith("failed") ? 0 : 1;
    STATE.lastActionAt = Date.now();
  }

  const payload = {
    status: snapshot.status,
    response_chars: snapshot.responseText.length,
    continue_count: STATE.continueCount,
    surface_sweep_suspected: snapshot.surfaceSweepSuspected,
    action_taken: actionTaken,
    preview: snapshot.responseText.slice(0, 500)
  };
  chrome.runtime.sendMessage({ type: "NEXUS_GROK_STATE", payload });
  return { ok: true, payload };
}

function inspectPage(settings) {
  const responseText = getLastAssistantText();
  const isGenerating = detectGenerating();
  const quietFor = Date.now() - STATE.lastMutationAt;
  const status = isGenerating
    ? "generating"
    : quietFor >= Number(settings.quietMillisAfterMutation || 3500)
      ? "idle"
      : "settling";

  return {
    status,
    responseText,
    quietFor,
    surfaceSweepSuspected: responseText.length > 0 && responseText.length < Number(settings.minUsefulChars || 900)
  };
}

function shouldContinue(snapshot, settings) {
  if (settings.autoContinue !== true) return false;
  if (snapshot.status !== "idle") return false;
  if (!snapshot.surfaceSweepSuspected) return false;
  if (STATE.continueCount >= Number(settings.maxContinuesPerChat || 3)) return false;
  const signature = `${location.href}|${snapshot.responseText.slice(-240)}`;
  if (signature === STATE.lastSignature) return false;
  if (Date.now() - STATE.lastActionAt < 10000) return false;
  STATE.lastSignature = signature;
  return true;
}

function getLastAssistantText() {
  const candidates = [
    ...document.querySelectorAll('[data-testid*="assistant" i], [class*="assistant" i], article, main [role="article"]')
  ];
  const textCandidates = candidates
    .map((node) => normalizeText(node.innerText || node.textContent || ""))
    .filter((text) => text.length > 0);
  if (textCandidates.length > 0) {
    return textCandidates.sort((a, b) => b.length - a.length)[0];
  }
  const main = document.querySelector("main") || document.body;
  return normalizeText(main.innerText || main.textContent || "");
}

function detectGenerating() {
  const stopButton = [...document.querySelectorAll("button")].some((button) => {
    const label = `${button.getAttribute("aria-label") || ""} ${button.title || ""} ${button.innerText || ""}`.toLowerCase();
    return /\bstop\b/.test(label) || label.includes("stop generating") || label.includes("stop response");
  });
  if (stopButton) return true;
  return Boolean(document.querySelector('[aria-busy="true"], [data-state="streaming"]'));
}

function draftContinuation(prompt) {
  const composer = findComposer();
  if (!composer) return false;
  setComposerText(composer, prompt);
  return true;
}

function sendContinuation(prompt) {
  if (!draftContinuation(prompt)) return false;
  const button = findSendButton();
  if (!button) return false;
  button.click();
  return true;
}

function findComposer() {
  return (
    document.querySelector('[contenteditable="true"][role="textbox"][aria-label="Ask Grok anything"]') ||
    document.querySelector('textarea:not([disabled])') ||
    document.querySelector('[contenteditable="true"][role="textbox"]') ||
    document.querySelector('[contenteditable="true"]') ||
    document.querySelector('input[type="text"]:not([disabled])')
  );
}

function setComposerText(composer, text) {
  focusComposer(composer);
  if (composer.isContentEditable) {
    selectComposerContents(composer);
    const inserted = document.execCommand("insertText", false, text);
    if (!inserted || !normalizeText(composer.innerText || composer.textContent || "").includes(normalizeText(text))) {
      composer.textContent = text;
    }
  } else {
    composer.value = text;
  }
  dispatchEditorEvent(composer, "input", text);
  dispatchEditorEvent(composer, "change");
}

function focusComposer(composer) {
  if (typeof composer.focus === "function") {
    composer.focus();
    return;
  }
  composer.dispatchEvent(createDomEvent("click", { cancelable: true }));
}

function selectComposerContents(composer) {
  const selection = window.getSelection();
  if (!selection) return;
  const range = document.createRange();
  range.selectNodeContents(composer);
  selection.removeAllRanges();
  selection.addRange(range);
}

function dispatchEditorEvent(composer, type, data = null) {
  if (type === "input" && typeof InputEvent === "function") {
    composer.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data }));
    return;
  }
  composer.dispatchEvent(createDomEvent(type));
}

function createDomEvent(type, options = {}) {
  if (typeof Event === "function") {
    return new Event(type, { bubbles: true, cancelable: options.cancelable === true });
  }
  const event = document.createEvent("Event");
  event.initEvent(type, true, options.cancelable === true);
  return event;
}

function findSendButton() {
  const preferred = document.querySelector(
    'button[data-testid="chat-submit"]:not([disabled]), button[type="submit"][aria-label="Submit"]:not([disabled])'
  );
  if (preferred) return preferred;

  const buttons = [...document.querySelectorAll("button:not([disabled])")];
  return buttons.find((button) => {
    const label = `${button.getAttribute("aria-label") || ""} ${button.title || ""} ${button.innerText || ""}`.toLowerCase();
    return label.includes("send") || label.includes("submit");
  });
}

function normalizeText(text) {
  return String(text).replace(/\s+/g, " ").trim();
}
