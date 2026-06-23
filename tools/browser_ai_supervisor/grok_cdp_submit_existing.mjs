#!/usr/bin/env node

const port = Number(process.argv.includes("--port") ? process.argv[process.argv.indexOf("--port") + 1] : 9224);
const required = process.argv.includes("--required") ? process.argv[process.argv.indexOf("--required") + 1] : "Grok";

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
      }, 10000);
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

const cdp = new Cdp(target.webSocketDebuggerUrl);
await cdp.open();
await cdp.send("Page.bringToFront");
await cdp.send("Runtime.enable");

const rectResult = await cdp.send("Runtime.evaluate", {
  returnByValue: true,
  expression: `(() => {
    const isVisible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const input = [...document.querySelectorAll("textarea, [contenteditable='true']")].filter(isVisible).at(-1);
    if (input) input.focus();
    const submit = [...document.querySelectorAll("button, [role='button']")]
      .filter(isVisible)
      .find((el) => (el.getAttribute("aria-label") || "").toLowerCase() === "submit");
    if (!submit) return { ok: false, reason: "NO_SUBMIT_BUTTON" };
    const r = submit.getBoundingClientRect();
    return {
      ok: true,
      disabled: submit.disabled || submit.getAttribute("aria-disabled") === "true",
      inputTextLen: (input?.innerText || input?.value || "").length,
      x: r.left + r.width / 2,
      y: r.top + r.height / 2,
      width: r.width,
      height: r.height
    };
  })()`,
});

const rect = rectResult.result.value;
if (!rect.ok) {
  console.log(JSON.stringify({ status: "BLOCKED", rect }, null, 2));
  process.exit(3);
}

await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: rect.x, y: rect.y, button: "none" });
await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });

await new Promise((resolve) => setTimeout(resolve, 500));

await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, key: "Enter", code: "Enter" });
await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, key: "Enter", code: "Enter" });
await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, key: "Enter", code: "Enter", modifiers: 2 });
await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, key: "Enter", code: "Enter", modifiers: 2 });

console.log(JSON.stringify({ status: "SUBMIT_ATTEMPTED", rect }, null, 2));
cdp.close();
