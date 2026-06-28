#!/usr/bin/env node
import http from "node:http";

const port = Number(process.argv[2] ?? 9224);
const urlPattern = process.argv[3] ?? "grok.com";

async function getBrowserWsUrl(port) {
  const res = await fetch(`http://127.0.0.1:${port}/json/version`);
  if (!res.ok) throw new Error(`CDP version failed: ${res.status}`);
  const info = await res.json();
  return info.webSocketDebuggerUrl;
}

async function getTargets(port) {
  const res = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!res.ok) throw new Error(`CDP list failed: ${res.status}`);
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
      this.ws.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
      this.ws.addEventListener("error", (e) => { clearTimeout(timer); reject(new Error(`CDP ws error: ${e.message ?? "unknown"}`)); }, { once: true });
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
    });
    this.ws.send(payload);
    return promise;
  }

  close() {
    this.ws.close();
  }
}

async function main() {
  const targets = await getTargets(port);
  const grokTarget = targets.find(t => t.url && new RegExp(urlPattern, "i").test(t.url));
  if (!grokTarget) {
    console.error(JSON.stringify({ ok: false, error: `No target matching "${urlPattern}" found` }));
    process.exit(1);
  }

  const browserWs = await getBrowserWsUrl(port);
  const cdp = new Cdp(browserWs);
  await cdp.open();

  const bounds = await cdp.send("Browser.getWindowForTarget", { targetId: grokTarget.id });
  const oldBounds = bounds.bounds;
  const windowId = bounds.windowId;

  await cdp.send("Browser.setWindowBounds", {
    windowId,
    bounds: { left: -32000, top: -32000, width: 1, height: 1, windowState: "normal" }
  });

  cdp.close();

  console.log(JSON.stringify({
    ok: true,
    windowId,
    oldBounds,
    newBounds: { left: -32000, top: -32000, width: 1, height: 1 }
  }));
}

main().catch(err => {
  console.error(JSON.stringify({ ok: false, error: err.message }));
  process.exit(1);
});
