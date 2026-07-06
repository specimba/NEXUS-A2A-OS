#!/usr/bin/env node
/** Probe a registry lane tab by host + conversation_key. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../..");
const REGISTRY = path.join(REPO, "nexus_os/nexusclaw/browser_lane_registry.json");

const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const laneId = process.argv.find((a, i) => process.argv[i - 1] === "--lane");
const registry = JSON.parse(fs.readFileSync(REGISTRY, "utf8"));
let lane = registry.lanes.find((l) => l.id === laneId);

// Legacy ID fallback (registry was renamed gemini_notebook -> gemini_app)
if (!lane && laneId === "gemini_notebook") {
  lane = registry.lanes.find((l) => l.id === "gemini_app");
}
if (!lane) {
  console.log(JSON.stringify({ status: "LANE_NOT_FOUND", laneId }));
  process.exit(2);
}

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const pages = list.filter((t) => t.type === "page");
const key = lane.conversation_key || "";
let pick =
  pages.find((p) => key && !/tbd|home$/i.test(key) && p.url.includes(key)) ||
  pages.find((p) => p.url.includes(lane.host || lane.required_probe));

const required =
  pick?.url?.includes("grok.com") ? "grok.com" :
  pick?.url?.includes("zo.computer") ? "zo.computer" :
  pick?.url?.includes("chatgpt.com") ? "chatgpt.com" :
  lane.required_probe;

if (pick) {
  try {
    const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
    if (ver.webSocketDebuggerUrl) {
      const ws = new WebSocket(ver.webSocketDebuggerUrl);
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("Browser CDP connection timeout")), 3000);
        ws.addEventListener("open", () => {
          clearTimeout(timer);
          resolve();
        });
        ws.addEventListener("error", (e) => {
          clearTimeout(timer);
          reject(new Error("Browser CDP connection error"));
        });
      });
      await new Promise((resolve) => {
        const timer = setTimeout(resolve, 2000);
        ws.addEventListener("message", (ev) => {
          const msg = JSON.parse(ev.data);
          if (msg.id === 99) {
            clearTimeout(timer);
            resolve();
          }
        });
        ws.send(JSON.stringify({ id: 99, method: "Target.activateTarget", params: { targetId: pick.id } }));
      });
      ws.close();
    }
  } catch (err) {
    // Ignore activation failure, proceed with probe
  }
}

const r = spawnSync(
  "node",
  [
    path.join(REPO, "tools/browser_ai_supervisor/grok_cdp_context_probe.mjs"),
    "--port",
    String(port),
    "--required",
    required,
    "--maxChars",
    "3000",
  ],
  { encoding: "utf8", cwd: REPO, timeout: 120000 },
);

let data = null;
try {
  data = JSON.parse(r.stdout);
} catch {
  data = { status: "PARSE_FAIL", stdout: (r.stdout || "").slice(-2000), stderr: (r.stderr || "").slice(-500) };
}

const tail = data?.state?.tailText || "";
const out = {
  status: data?.status || "PROBE_DONE",
  lane: lane.id,
  agent_id: lane.agent_id,
  required,
  targetId: pick?.id || null,
  pickUrl: pick?.url || null,
  title: data?.state?.title || data?.target?.title || null,
  url: data?.state?.url || data?.target?.url || null,
  tailLen: tail.length,
  tailSha256: crypto.createHash("sha256").update(tail, "utf8").digest("hex"),
  tail: tail.slice(-2500),
  generating:
    /thought for|thinking|zo is thinking|stop generating|deep research|researching/i.test(tail) ||
    /thought for|thinking/i.test(data?.state?.title || ""),
  exit: r.status,
};
console.log(JSON.stringify(out));