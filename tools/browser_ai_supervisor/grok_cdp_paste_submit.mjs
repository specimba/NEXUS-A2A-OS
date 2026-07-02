#!/usr/bin/env node

import fs from "node:fs";

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const required = args.required ?? "Grok";
const prompt = args.promptFile ? fs.readFileSync(args.promptFile, "utf8") : args.prompt;

if (!prompt || prompt.trim().length < 20) {
  throw new Error("--prompt or --promptFile is required");
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) out[key] = true;
    else {
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
  }
  async open() {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP websocket open timeout")), 5000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", () => {
        clearTimeout(timer);
        reject(new Error("CDP websocket error"));
      }, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    });
  }
  send(method, params = {}) {
    const id = this.nextId++;
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP call timeout: ${method}`));
        }
      }, 45000);
    });
    this.ws.send(JSON.stringify({ id, method, params }));
    return promise;
  }
  close() {
    this.ws.close();
  }
}

const targets = await getTargets(port);
const target = targets
  .filter((item) => item.type === "page")
  .find((item) => item.title.includes(required) || item.url.includes(required));

if (!target) {
  console.log(JSON.stringify({ status: "NOTIFY_SETUP_REQUIRED", blocker: `No page matched ${required}` }, null, 2));
  process.exit(2);
}

// Page.bringToFront only when operator visibility is requested (see grok_cdp_restore_window.mjs).
const cdp = new Cdp(target.webSocketDebuggerUrl);
await cdp.open();
await cdp.send("Runtime.enable");
if (process.env.NEXUS_GROK_OPERATOR_VISIBLE === "1") {
  await cdp.send("Page.bringToFront");
}

const focusResult = await cdp.send("Runtime.evaluate", {
  returnByValue: true,
  awaitPromise: true,
  expression: `(() => {
    const isVisible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const input = [...document.querySelectorAll("textarea, [contenteditable='true']")].filter(isVisible).at(-1);
    if (!input) return { ok: false, reason: "NO_INPUT" };
    input.focus();
    const r = input.getBoundingClientRect();
    return { ok: true, x: r.left + Math.min(40, r.width / 2), y: r.top + r.height / 2, tag: input.tagName };
  })()`,
});

const focus = focusResult.result.value;
if (!focus.ok) {
  console.log(JSON.stringify({ status: "BLOCKED", focus }, null, 2));
  process.exit(3);
}

await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: focus.x, y: focus.y, button: "none" });
await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: focus.x, y: focus.y, button: "left", clickCount: 1 });
await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: focus.x, y: focus.y, button: "left", clickCount: 1 });
await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65, modifiers: 2 });
await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65, modifiers: 2 });
await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
await cdp.send("Input.insertText", { text: prompt });

await new Promise((resolve) => setTimeout(resolve, 1200));

const submitResult = await cdp.send("Runtime.evaluate", {
  returnByValue: true,
  awaitPromise: true,
  expression: `(() => {
    const isVisible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const input = [...document.querySelectorAll("textarea, [contenteditable='true']")].filter(isVisible).at(-1);
    const submit = [...document.querySelectorAll("button, [role='button']")]
      .filter(isVisible)
      .find((el) => (el.getAttribute("aria-label") || "").toLowerCase() === "submit");
    if (!submit) return { ok: false, reason: "NO_SUBMIT", inputTextLen: (input?.innerText || input?.value || "").length };
    const disabled = submit.disabled || submit.getAttribute("aria-disabled") === "true";
    const r = submit.getBoundingClientRect();
    return { ok: true, disabled, inputTextLen: (input?.innerText || input?.value || "").length, x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`,
});

const submit = submitResult.result.value;
if (!submit.ok || submit.disabled || submit.inputTextLen < 20) {
  console.log(JSON.stringify({ status: "STAGED_NOT_SUBMITTED", focus, submit }, null, 2));
  process.exit(4);
}

await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: submit.x, y: submit.y, button: "none" });
await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: submit.x, y: submit.y, button: "left", clickCount: 1 });
await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: submit.x, y: submit.y, button: "left", clickCount: 1 });

console.log(JSON.stringify({ status: "SUBMITTED", focus, submit }, null, 2));
cdp.close();
