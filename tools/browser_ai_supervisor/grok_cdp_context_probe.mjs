#!/usr/bin/env node

import fs from "node:fs";

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const required = args.required ?? "Grok";
const outFile = args.outFile;
const expand = Boolean(args.expand);
const pickFirst = Boolean(args.pickFirst);
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
        const { resolve, reject, timer } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        clearTimeout(timer);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
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
    // Keep probe snappy: sleeping/discarded tabs must fail fast (reload path handles one retry).
    const timeoutMs = method === "Runtime.evaluate" ? 45000 : 12000;
    const promise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP call timeout: ${method}`));
        }
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
    });
    this.ws.send(JSON.stringify({ id, method, params }));
    return promise;
  }
  close() {
    this.ws.close();
  }
}

function matchesRequired(item, requiredRaw) {
  const req = String(requiredRaw || "");
  const title = item.title || "";
  const url = item.url || "";
  if (title.includes(req) || url.includes(req)) return true;
  // Host-style required (e.g. chatgpt.com) should match even when title is a chat name.
  try {
    if (url && url.startsWith("http")) {
      const host = new URL(url).hostname;
      if (host === req || host.endsWith(`.${req}`) || host.includes(req)) return true;
    }
  } catch {
    /* ignore */
  }
  return false;
}

async function activateTarget(targetId) {
  try {
    const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
    if (!ver.webSocketDebuggerUrl) return;
    const browser = new Cdp(ver.webSocketDebuggerUrl);
    await browser.open();
    try {
      await browser.send("Target.activateTarget", { targetId });
    } catch {
      /* best-effort for sleeping tabs */
    }
    browser.close();
    await new Promise((r) => setTimeout(r, 400));
  } catch {
    /* ignore */
  }
}

let targets = await getTargets(port);
let matchingTargets = targets
  .filter((item) => item.type === "page")
  .filter((item) => matchesRequired(item, required));

// Prefer pages that still have a real URL over empty-url ghosts.
matchingTargets = [
  ...matchingTargets.filter((t) => t.url && t.url.startsWith("http")),
  ...matchingTargets.filter((t) => !t.url || !t.url.startsWith("http")),
];

if (matchingTargets.length > 1 && !pickFirst) {
  const output = {
    status: "NOTIFY_SETUP_REQUIRED",
    blocker: `Duplicate page targets matched '${required}' on port ${port}; close or merge duplicates before automation (or pass --pickFirst)`,
    reason: "duplicate_target_match",
    matchingTargets: matchingTargets.slice(0, 10).map((item) => ({ title: item.title, url: redactUrl(item.url) })),
  };
  console.log(JSON.stringify(output, null, 2));
  process.exit(2);
}

let target = matchingTargets[0];

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

// Wake sleeping / discarded tabs, then refresh target list for a live websocket URL.
await activateTarget(target.id);
targets = await getTargets(port);
matchingTargets = targets
  .filter((item) => item.type === "page")
  .filter((item) => matchesRequired(item, required));
matchingTargets = [
  ...matchingTargets.filter((t) => t.url && t.url.startsWith("http")),
  ...matchingTargets.filter((t) => !t.url || !t.url.startsWith("http")),
];
target = matchingTargets.find((t) => t.id === target.id) || matchingTargets[0] || target;

if (!target.webSocketDebuggerUrl) {
  const output = {
    status: "NOTIFY_SETUP_REQUIRED",
    blocker: `Matched '${required}' but target has no webSocketDebuggerUrl (tab may be crashed/discarded)`,
    target: { title: target.title, url: redactUrl(target.url), id: target.id },
  };
  console.log(JSON.stringify(output, null, 2));
  process.exit(2);
}

// Wake path: activateTarget (above) + bringToFront + optional reload for discarded tabs.
const cdp = new Cdp(target.webSocketDebuggerUrl);
await cdp.open();
try {
  await cdp.send("Page.enable");
} catch {
  /* some targets reject Page domain until loaded */
}
try {
  await cdp.send("Page.bringToFront");
} catch {
  /* best-effort */
}
try {
  await cdp.send("Runtime.enable");
} catch (firstErr) {
  // Discarded/sleeping tabs often need a reload before Runtime attaches.
  try {
    await cdp.send("Page.reload", { ignoreCache: false });
    await new Promise((r) => setTimeout(r, 2500));
    await cdp.send("Runtime.enable");
  } catch {
    throw firstErr;
  }
}

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

