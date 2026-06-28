#!/usr/bin/env node

import fs from "node:fs";

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const required = args.required ?? "grok.com";
const prompt = args.promptFile ? fs.readFileSync(args.promptFile, "utf8") : args.prompt;
const send = Boolean(args.send);

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      out[key] = true;
    } else {
      out[key] = next;
      i += 1;
    }
  }
  return out;
}

async function getTargets(port) {
  const res = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!res.ok) throw new Error(`CDP target list failed: ${res.status}`);
  return res.json();
}

class Cdp {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
  }

  async open() {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP websocket open timeout")), 5000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", (event) => {
        clearTimeout(timer);
        reject(new Error(`CDP websocket error: ${event.message ?? "unknown"}`));
      }, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else {
        this.events.push(msg);
      }
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    const payload = JSON.stringify({ id, method, params });
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP call timeout: ${method}`));
        }
      }, 10000);
    });
    this.ws.send(payload);
    return promise;
  }

  close() {
    this.ws.close();
  }
}

function redactUrl(raw) {
  if (!raw) return raw;
  try {
    const url = new URL(raw);
    return `${url.origin}${url.pathname}${url.search ? "?REDACTED" : ""}${url.hash ? "#REDACTED" : ""}`;
  } catch {
    return String(raw).replace(/\?.*$/, "?REDACTED");
  }
}

function visibleStateExpression() {
  return `(() => {
    const isVisible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const text = document.body?.innerText || "";
    const inputs = [...document.querySelectorAll("textarea, [contenteditable='true'], input[type='text']")]
      .filter(isVisible)
      .map((el, index) => ({
        index,
        tag: el.tagName,
        role: el.getAttribute("role"),
        aria: el.getAttribute("aria-label"),
        placeholder: el.getAttribute("placeholder"),
        text: (el.innerText || el.value || "").slice(0, 160)
      }));
    const buttons = [...document.querySelectorAll("button, [role='button']")]
      .filter(isVisible)
      .slice(-30)
      .map((el, index) => ({
        index,
        tag: el.tagName,
        aria: el.getAttribute("aria-label"),
        title: el.getAttribute("title"),
        text: (el.innerText || el.textContent || "").trim().slice(0, 80)
      }));
    return {
      title: document.title,
      url: location.href,
      readyState: document.readyState,
      inputCount: inputs.length,
      inputs,
      buttons,
      visibleTail: text.slice(-3500)
    };
  })()`;
}

function sendPromptExpression(promptText) {
  return `((promptText) => {
    const isVisible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const candidates = [...document.querySelectorAll("textarea, [contenteditable='true']")].filter(isVisible);
    const input = candidates[candidates.length - 1];
    if (!input) return { ok: false, reason: "NO_VISIBLE_INPUT" };
    input.focus();
    if (input.isContentEditable) {
      input.innerText = promptText;
    } else {
      input.value = promptText;
    }
    input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: promptText }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    const buttons = [...document.querySelectorAll("button, [role='button']")].filter(isVisible);
    const sendButton = buttons.find((el) => (el.getAttribute("aria-label") || "").toLowerCase() === "submit") || buttons.find((el) => {
      const label = [el.getAttribute("aria-label"), el.getAttribute("title"), el.innerText, el.textContent]
        .filter(Boolean).join(" ").toLowerCase();
      return /send|submit/.test(label);
    });
    if (!sendButton) return { ok: false, reason: "NO_VISIBLE_SEND_BUTTON", inputTag: input.tagName };
    const disabled = sendButton.disabled || sendButton.getAttribute("aria-disabled") === "true";
    if (disabled) return { ok: false, reason: "SEND_BUTTON_DISABLED", inputTag: input.tagName };
    sendButton.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    sendButton.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    sendButton.click();
    return {
      ok: true,
      inputTag: input.tagName,
      sendButtonText: (sendButton.innerText || sendButton.textContent || "").trim().slice(0, 80),
      sendButtonAria: sendButton.getAttribute("aria-label")
    };
  })(${JSON.stringify(promptText)})`;
}

const targets = await getTargets(port);
const pages = targets.filter((target) => target.type === "page");
const target = pages.find((page) => page.url.includes(required) || page.title.includes(required));

if (!target) {
  console.log(JSON.stringify({
    status: "NOTIFY_SETUP_REQUIRED",
    blocker: `No CDP page target matched '${required}' on port ${port}`,
    targetCount: pages.length,
    targetSample: pages.slice(0, 10).map((page) => ({ title: page.title, url: redactUrl(page.url) })),
  }, null, 2));
  process.exit(2);
}

// NOTE: Page.bringToFront deliberately REMOVED — it steals OS focus from the user.
// Instead we interact via Runtime.evaluate which works without window focus.
// If you need visual debugging, add --headless=false to chrome and uncomment:
//   await cdp.send("Page.bringToFront");
const cdp = new Cdp(target.webSocketDebuggerUrl);
await cdp.open();
await cdp.send("Runtime.enable");

const stateResult = await cdp.send("Runtime.evaluate", {
  expression: visibleStateExpression(),
  returnByValue: true,
  awaitPromise: true,
});

const state = stateResult.result.value;
const output = {
  status: "READY",
  target: { title: target.title, url: redactUrl(target.url) },
  state,
};

if (send) {
  if (!prompt || prompt.trim().length < 20) {
    throw new Error("--send requires --prompt or --promptFile with a substantial prompt");
  }
  const sendResult = await cdp.send("Runtime.evaluate", {
    expression: sendPromptExpression(prompt),
    returnByValue: true,
    awaitPromise: true,
  });
  output.send = sendResult.result.value;
}

console.log(JSON.stringify(output, null, 2));
cdp.close();



