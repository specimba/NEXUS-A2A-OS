#!/usr/bin/env node
/**
 * LEGACY offscreen-park helper.
 *
 * DEFAULT IS NO-OP. Operator collab Chrome must stay visible.
 * Hiding to -32000x1x1 corrupts window_placement and forces watch_lane_stack / restore loops.
 *
 * Only runs if ALL of:
 *   - NEXUS_FORCE_HIDE=1  (explicit opt-in)
 *   - NEXUS_KEEP_VISIBLE is not 1
 *   - VISIBLE_LANES is not 1
 *   - no WINDOW_PROTECT.json with protected/keep_visible
 *
 * Prefer: never set NEXUS_FORCE_HIDE. Leave the CDP lane window on-screen.
 */
import fs from "node:fs";

const port = Number(process.argv[2] ?? 9224);
const urlPattern = process.argv[3] ?? "grok.com";

async function getBrowserWsUrl(p) {
  const res = await fetch(`http://127.0.0.1:${p}/json/version`);
  if (!res.ok) throw new Error(`CDP version failed: ${res.status}`);
  const info = await res.json();
  return info.webSocketDebuggerUrl;
}

async function getTargets(p) {
  const res = await fetch(`http://127.0.0.1:${p}/json/list`);
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
      const timer = setTimeout(() => reject(new Error("CDP websocket open timeout")), 5000);
      this.ws.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
      this.ws.addEventListener("error", (e) => {
        clearTimeout(timer);
        reject(new Error(`CDP ws error: ${e.message ?? "unknown"}`));
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
    });
    this.ws.send(JSON.stringify({ id, method, params }));
    return promise;
  }

  close() {
    this.ws.close();
  }
}

function shouldSkipHide() {
  // Permanent default: never hide unless FORCE_HIDE is set.
  if (process.env.NEXUS_FORCE_HIDE !== "1") {
    return "default_no_hide (set NEXUS_FORCE_HIDE=1 to override — not recommended)";
  }
  if (process.env.VISIBLE_LANES === "1") return "VISIBLE_LANES=1";
  if (process.env.NEXUS_KEEP_VISIBLE === "1") return "NEXUS_KEEP_VISIBLE=1";
  if (process.env.NEXUS_ALLOW_FOREGROUND_LANE_REPAIR === "1") return "NEXUS_ALLOW_FOREGROUND_LANE_REPAIR=1";
  try {
    const candidates = [
      "C:\\Users\\speci.000\\Downloads\\NEXUSlogs\\private_team_20260709_grok45_scratch\\WINDOW_PROTECT.json",
      "C:\\Users\\speci.000\\Documents\\NEXUS\\NEXUSlogs\\a2a_experiment\\WINDOW_PROTECT.json",
      "C:\\Users\\speci.000\\Downloads\\cdp_agent_scratch\\WINDOW_PROTECT.json",
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        const j = JSON.parse(fs.readFileSync(p, "utf8"));
        if (j.protected || j.keep_visible || j.permanent) return `protect_file:${p}`;
      }
    }
  } catch {
    /* ignore */
  }
  return null;
}

async function main() {
  const skip = shouldSkipHide();
  if (skip) {
    console.log(JSON.stringify({
      ok: true,
      skipped: true,
      reason: skip,
      policy: "KEEP_VISIBLE_DEFAULT",
    }));
    return;
  }

  const targets = await getTargets(port);
  const grokTarget = targets.find((t) => t.url && new RegExp(urlPattern, "i").test(t.url));
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

  // Only reachable with NEXUS_FORCE_HIDE=1 and no protect locks.
  await cdp.send("Browser.setWindowBounds", {
    windowId,
    bounds: { left: -32000, top: -32000, width: 1, height: 1, windowState: "normal" },
  });

  cdp.close();

  console.log(JSON.stringify({
    ok: true,
    windowId,
    oldBounds,
    newBounds: { left: -32000, top: -32000, width: 1, height: 1 },
    warning: "NEXUS_FORCE_HIDE applied — profile may save bad window_placement; run restore after.",
  }));
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: err.message }));
  process.exit(1);
});
