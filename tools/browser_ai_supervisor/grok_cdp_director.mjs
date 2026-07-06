#!/usr/bin/env node
/**
 * CDP director for Grok + Zo tabs on lane Chrome :9224.
 * Composer: Shift+Enter newline, Enter send (cdp_compose_submit.mjs).
 * Grok: send → wait for response → read probe → optional nudge. Zo: pre-idle → send → long wait.
 */

import fs from "node:fs";
import { clearComposerShortcut, submitPromptWithEnter } from "./cdp_compose_submit.mjs";

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const required = args.required ?? "grok.com";
const prompt = args.promptFile ? fs.readFileSync(args.promptFile, "utf8") : args.prompt;
const send = Boolean(args.send);
const operatorFocus = Boolean(args.operatorFocus);

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
    const denylist = ["Target.createTarget", "Target.closeTarget", "Browser.close"];
    if (denylist.includes(method)) {
      console.warn(`[CDP_GUARD] Blocked blacklisted method: ${method}`);
      return Promise.reject(new Error(`Blocked by CDP denylist guard: ${method}`));
    }
    if (method === "Page.navigate") {
      const url = params.url || "";
      const allowedHosts = [
        "grok.com",
        "chatgpt.com",
        "zo.computer",
        "gemini.google.com",
        "chat.z.ai",
        "console.gmicloud.ai",
        "apodex.ai",
        "meta.ai",
        "chat.qwen.ai",
        "agent.minimax.io",
        "aistudio.xiaomimimo.com",
        "chat.deepseek.com",
        "alphaxiv.org"
      ];
      const isAllowed = allowedHosts.some(host => url.includes(host));
      if (!isAllowed) {
        console.warn(`[CDP_GUARD] Blocked navigation to non-allowlisted URL: ${url}`);
        return Promise.reject(new Error(`Blocked by CDP navigation guard: ${url}`));
      }
    }

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
    const r = input.getBoundingClientRect();
    return {
      ok: true,
      inputTag: input.tagName,
      x: r.left + Math.min(40, r.width / 2),
      y: r.top + r.height / 2,
      len: promptText.length,
    };
  })(${JSON.stringify(promptText)})`;
}

async function sendViaEnter(cdp, promptText) {
  const focusResult = await cdp.send("Runtime.evaluate", {
    expression: sendPromptExpression(promptText),
    returnByValue: true,
    awaitPromise: true,
  });
  const focus = focusResult.result.value;
  if (!focus?.ok) return focus;

  await cdp.send("Input.dispatchMouseEvent", {
    type: "mousePressed",
    x: focus.x,
    y: focus.y,
    button: "left",
    clickCount: 1,
  });
  await cdp.send("Input.dispatchMouseEvent", {
    type: "mouseReleased",
    x: focus.x,
    y: focus.y,
    button: "left",
    clickCount: 1,
  });
  await clearComposerShortcut(cdp);
  const submitted = await submitPromptWithEnter(cdp, promptText);
  return { ...submitted, inputTag: focus.inputTag };
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

const cdp = new Cdp(target.webSocketDebuggerUrl);
await cdp.open();
await cdp.send("Runtime.enable");
if (operatorFocus) {
  await cdp.send("Page.bringToFront");
}

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
  if (!prompt || !String(prompt).trim()) {
    throw new Error("--send requires --prompt or --promptFile");
  }
  output.send = await sendViaEnter(cdp, prompt);
}

console.log(JSON.stringify(output, null, 2));
cdp.close();



