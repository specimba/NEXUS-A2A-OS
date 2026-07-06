#!/usr/bin/env node
/**
 * Operator-only: restore Grok-lane Chrome from hidden/minimized to normal/maximized.
 * Use when passkey or manual Grok work needs a visible window (not for silent automation).
 */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const mode = process.argv.find((a, i) => process.argv[i - 1] === "--mode") ?? "maximized";
const urlMatch = process.argv.find((a, i) => process.argv[i - 1] === "--match") ?? "grok\\.com";
const urlRe = new RegExp(urlMatch, "i");

async function browserWsUrl() {
  const res = await fetch(`http://127.0.0.1:${port}/json/version`);
  if (!res.ok) throw new Error(`CDP version failed: ${res.status}`);
  const j = await res.json();
  return j.webSocketDebuggerUrl;
}

async function listTargets() {
  let res;
  try {
    res = await fetch(`http://127.0.0.1:${port}/json/list`);
  } catch (e) {
    const hint =
      "CDP not listening. Run: .\\scripts\\ensure_cdp_lane_up.ps1 OR .\\scripts\\grok_zo_cdp_lane.ps1 -Action RestartChrome";
    throw new Error(`CDP_DOWN port=${port} (${e.message}). ${hint}`);
  }
  if (!res.ok) throw new Error(`CDP list failed: ${res.status}`);
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
      const t = setTimeout(() => reject(new Error("ws timeout")), 8000);
      this.ws.addEventListener("open", () => { clearTimeout(t); resolve(); }, { once: true });
      this.ws.addEventListener("error", () => { clearTimeout(t); reject(new Error("ws error")); }, { once: true });
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
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() {
    try { this.ws.close(); } catch { /* ignore */ }
  }
}

async function main() {
  const targets = await listTargets();
  const grok = targets.find(
    (t) => t.type === "page" && t.url && urlRe.test(t.url) && !t.url.startsWith("chrome-extension")
  );
  if (!grok) {
    console.log(JSON.stringify({ status: "NO_MATCHING_TAB", port, match: urlMatch }, null, 2));
    process.exit(2);
  }

  const wsUrl = await browserWsUrl();
  const cdp = new Cdp(wsUrl);
  await cdp.open();

  const { windowId } = await cdp.send("Browser.getWindowForTarget", { targetId: grok.id });
  const windowState = mode === "normal" ? "normal" : "maximized";
  await cdp.send("Browser.setWindowBounds", {
    windowId,
    bounds: { windowState },
  });
  cdp.close();

  const pageCdp = new Cdp(grok.webSocketDebuggerUrl);
  await pageCdp.open();
  await pageCdp.send("Page.bringToFront");
  pageCdp.close();

  console.log(JSON.stringify({
    status: "WINDOW_RESTORED",
    port,
    windowState,
    title: grok.title,
    url: grok.url.replace(/\?.*$/, "?REDACTED"),
  }, null, 2));
}

main().catch((err) => {
  console.log(JSON.stringify({ status: "ERROR", error: String(err) }, null, 2));
  process.exit(1);
});