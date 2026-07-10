#!/usr/bin/env node
/**
 * Browser CDP: fix slim-line / off-screen Chrome windows, then maximize.
 * Root cause: profile saved 1x1 @ -32000 from SilentBackground; maximize-only CDP cannot fix height.
 */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const argNum = (flag, def) => {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? Number(process.argv[i + 1]) : def;
};
const workLeft = argNum("--work-left", 0);
const workTop = argNum("--work-top", 0);
const workWidth = argNum("--work-width", 1920);
const workHeight = argNum("--work-height", 1080);
const minW = argNum("--min-width", 900);
const minH = argNum("--min-height", 600);
const margin = argNum("--margin", 80);
const interactive = process.argv.includes("--interactive");
const onlyIfBroken = process.argv.includes("--only-if-broken");
const modeArg = process.argv.find((a, i) => process.argv[i - 1] === "--mode");
// normal | maximized — default maximized unless interactive or only-if-broken
const restoreMode = modeArg || (interactive || onlyIfBroken ? "normal" : "maximized");

const targetW = Math.min(Math.max(minW, workWidth - margin * 2), workWidth - 40);
const targetH = Math.min(Math.max(minH, workHeight - margin * 2), workHeight - 80);
const targetLeft = workLeft + Math.floor((workWidth - targetW) / 2);
const targetTop = workTop + Math.floor((workHeight - targetH) / 2);

function broken(bounds) {
  if (!bounds) return true;
  const { left = 0, top = 0, width = 0, height = 0, windowState } = bounds;
  if (windowState === "minimized") return true;
  if (height < 200 || width < 400) return true;
  if (left < -500 || top < -500) return true;
  if (width <= 2 || height <= 2) return true;
  return false;
}

class Cdp {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
  }
  async open() {
    await new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("CDP open timeout")), 8000);
      this.ws.addEventListener("open", () => {
        clearTimeout(t);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", () => {
        clearTimeout(t);
        reject(new Error("CDP ws error"));
      }, { once: true });
    });
    this.ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
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
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`timeout ${method}`));
        }
      }, 15000);
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() {
    this.ws.close();
  }
}

const verRes = await fetch(`http://127.0.0.1:${port}/json/version`);
if (!verRes.ok) {
  console.log(JSON.stringify({ status: "CDP_DOWN", port }));
  process.exit(2);
}
const ver = await verRes.json();
const browserWs = ver.webSocketDebuggerUrl;
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const pages = targets.filter((t) => t.type === "page" && t.url && !t.url.startsWith("chrome-extension"));

const cdp = new Cdp(browserWs);
await cdp.open();
await cdp.send("Target.setDiscoverTargets", { discover: true });

const windowIds = new Set();
for (const page of pages.slice(0, 12)) {
  try {
    const win = await cdp.send("Browser.getWindowForTarget", { targetId: page.id });
    if (win?.windowId) windowIds.add(win.windowId);
  } catch {
    /* ignore */
  }
}

const steps = [];
const errors = [];

for (const windowId of windowIds) {
  try {
    let before = null;
    try {
      const got = await cdp.send("Browser.getWindowBounds", { windowId });
      before = got?.bounds ?? null;
    } catch {
      before = null;
    }

    const needsFix = broken(before);
    // Policy: if only-if-broken and window is fine, leave operator alone (no maximize twitch).
    if (onlyIfBroken && !needsFix) {
      steps.push({ windowId, phase: "skip_ok", before });
      continue;
    }

    if (needsFix || interactive || !onlyIfBroken) {
      await cdp.send("Browser.setWindowBounds", {
        windowId,
        bounds: {
          left: targetLeft,
          top: targetTop,
          width: targetW,
          height: targetH,
          windowState: "normal",
        },
      });
      steps.push({
        windowId,
        phase: interactive ? "interactive_normal" : "normal_explicit",
        targetW,
        targetH,
        targetLeft,
        targetTop,
        before,
        needsFix,
      });
    }

    // Maximize only when explicitly requested and not in gentle only-if-broken mode.
    if (!interactive && restoreMode === "maximized" && !onlyIfBroken) {
      await cdp.send("Browser.setWindowBounds", {
        windowId,
        bounds: { windowState: "maximized" },
      });
      steps.push({ windowId, phase: "maximized", needsFix });
    }

    let after = null;
    try {
      const got = await cdp.send("Browser.getWindowBounds", { windowId });
      after = got?.bounds ?? null;
    } catch {
      after = null;
    }
    if (broken(after)) {
      await cdp.send("Browser.setWindowBounds", {
        windowId,
        bounds: {
          left: targetLeft,
          top: targetTop,
          width: targetW,
          height: targetH,
          windowState: "normal",
        },
      });
      steps.push({ windowId, phase: "normal_fallback_after_bad_bounds", after });
    }
  } catch (e) {
    errors.push({ windowId, err: String(e.message || e) });
  }
}

cdp.close();
console.log(
  JSON.stringify({
    status: steps.length ? "BROWSER_CDP_RESTORE" : "NO_WINDOWS",
    port,
    windowIds: [...windowIds],
    workArea: { workLeft, workTop, workWidth, workHeight },
    target: { targetLeft, targetTop, targetW, targetH },
    steps,
    errors,
  })
);