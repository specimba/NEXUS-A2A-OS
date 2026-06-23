#!/usr/bin/env node

import fs from "node:fs";

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const required = args.required ?? "Grok";
const outFile = args.outFile;
const expand = Boolean(args.expand);
const maxChars = Number(args.maxChars ?? 24000);
const maxCodeChars = Number(args.maxCodeChars ?? Math.max(5000, maxChars));

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

function redactUrl(raw) {
  if (!raw) return raw;
  try {
    const url = new URL(raw);
    return `${url.origin}${url.pathname}${url.search ? "?REDACTED" : ""}${url.hash ? "#REDACTED" : ""}`;
  } catch {
    return String(raw).replace(/\?.*$/, "?REDACTED");
  }
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
  const output = {
    status: "NOTIFY_SETUP_REQUIRED",
    blocker: `No page target matched '${required}' on port ${port}`,
    targetSample: targets.filter((item) => item.type === "page").slice(0, 10)
      .map((item) => ({ title: item.title, url: redactUrl(item.url) })),
  };
  console.log(JSON.stringify(output, null, 2));
  process.exit(2);
}

const cdp = new Cdp(target.webSocketDebuggerUrl);
await cdp.open();
await cdp.send("Page.bringToFront");
await cdp.send("Runtime.enable");

const probeExpression = `async ({ expand, maxChars, maxCodeChars }) => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
  };
  const labelOf = (el) => [el.getAttribute("aria-label"), el.getAttribute("title"), el.innerText, el.textContent]
    .filter(Boolean).join(" ").replace(/\\s+/g, " ").trim();

  window.scrollTo(0, document.body.scrollHeight);
  await sleep(500);

  const expansionLog = [];
  if (expand) {
    const buttons = [...document.querySelectorAll("button, [role='button']")].filter(isVisible);
    for (const button of buttons) {
      const label = labelOf(button);
      const safeExpandable =
        /^Thought for\\b/i.test(label) ||
        /^Show full message$/i.test(label) ||
        /^Expand$/i.test(label) ||
        /^Collapse$/i.test(label) ||
        /^Wrap$/i.test(label);
      const forbidden = /\\b(Run|Submit|Regenerate|Delete|Publish|Share|Connect|Attach|Copy install command)\\b/i.test(label);
      if (!safeExpandable || forbidden) continue;
      try {
        button.click();
        expansionLog.push(label.slice(0, 120));
        await sleep(250);
      } catch {}
    }
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(500);
  }

  const bodyText = (document.body?.innerText || "").replace(/\\u0000/g, "");
  const lines = bodyText.split(/\\r?\\n/).map((line) => line.trim()).filter(Boolean);
  const tailLines = lines.slice(-260);
  const codeBlocks = [...document.querySelectorAll("pre, code")]
    .filter(isVisible)
    .slice(-12)
    .map((el, index) => ({
      index,
      text: (el.innerText || el.textContent || "") .slice(0, maxCodeChars),
    }));
  const buttons = [...document.querySelectorAll("button, [role='button']")]
    .filter(isVisible)
    .slice(-80)
    .map((el, index) => ({ index, label: labelOf(el).slice(0, 180) }));
  const inputs = [...document.querySelectorAll("textarea, [contenteditable='true'], input[type='text']")]
    .filter(isVisible)
    .map((el, index) => ({
      index,
      tag: el.tagName,
      role: el.getAttribute("role"),
      aria: el.getAttribute("aria-label"),
      textLength: (el.innerText || el.value || "").length,
    }));

  return {
    title: document.title,
    url: location.href,
    readyState: document.readyState,
    expansionLog,
    inputs,
    buttons,
    codeBlocks,
    tailText: tailLines.join("\\n").slice(-maxChars),
  };
}`;

const result = await cdp.send("Runtime.evaluate", {
  expression: `(${probeExpression})(${JSON.stringify({ expand, maxChars, maxCodeChars })})`,
  returnByValue: true,
  awaitPromise: true,
});

const state = result.result.value;
state.url = redactUrl(state.url);
const output = {
  status: "READY",
  target: { title: target.title, url: redactUrl(target.url) },
  state,
};

const json = JSON.stringify(output, null, 2);
if (outFile) {
  fs.writeFileSync(outFile, json, "utf8");
}
console.log(json);
cdp.close();



