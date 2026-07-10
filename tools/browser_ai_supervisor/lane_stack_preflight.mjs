#!/usr/bin/env node
/**
 * Multi-lane CDP preflight for the authenticated NEXUS Chrome profile (:9224).
 * For each lane: optional dedupe -> window restore -> context probe.
 *
 * IMPORTANT: This does NOT open a new Chrome process and does NOT send chat
 * messages. It reuses the existing remote-debugging profile on :9224.
 *   - silent (default): restore + probe for automation readiness
 *   - --observe: dwell on each lane tab so a human can watch the same window
 *
 * Usage:
 *   node lane_stack_preflight.mjs --port 9224
 *   node lane_stack_preflight.mjs --port 9224 --observe
 *   node lane_stack_preflight.mjs --port 9224 --ledger C:\Users\...\NEXUScontinuity_runs.jsonl
 *   node lane_stack_preflight.mjs --lanes grok,qwen,gemini --no-restore
 */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../..");
const DEFAULT_VAULT_LEDGER =
  process.platform === "win32"
    ? "C:\\Users\\speci.000\\Downloads\\NEXUSlogs\\NEXUScontinuity_runs.jsonl"
    : "/mnt/c/Users/speci.000/Downloads/NEXUSlogs/NEXUScontinuity_runs.jsonl";

function arg(name, fallback = undefined) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = process.argv[i + 1];
  if (!v || v.startsWith("--")) return true;
  return v;
}

const port = Number(arg("port", 9224));
const noRestore = process.argv.includes("--no-restore");
const noDedupe = process.argv.includes("--no-dedupe");
const observe = process.argv.includes("--observe");
const observeDwellMs = Number(arg("dwellMs", 1500));
const ledger =
  arg("ledger", process.env.NEXUS_CONTINUITY_LEDGER) ||
  process.env.NEXUS_CONTINUITY_LEDGER ||
  DEFAULT_VAULT_LEDGER;

const DEFAULT_LANES = [
  { id: "grok", match: "grok\\.com", required: "grok.com" },
  { id: "gemini", match: "gemini\\.google\\.com", required: "gemini.google.com" },
  { id: "qwen", match: "chat\\.qwen\\.ai", required: "chat.qwen.ai" },
  { id: "chatgpt", match: "chatgpt\\.com", required: "chatgpt.com" },
  { id: "meta", match: "meta\\.ai", required: "meta.ai" },
  { id: "zai", match: "chat\\.z\\.ai", required: "chat.z.ai" },
  { id: "deepseek", match: "chat\\.deepseek\\.com", required: "deepseek.com" },
];

const laneFilter = String(arg("lanes", "") || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const lanes = laneFilter.length
  ? DEFAULT_LANES.filter((l) => laneFilter.includes(l.id))
  : DEFAULT_LANES;

function tryParseJson(out) {
  if (!out) return null;
  const start = out.indexOf("{");
  const end = out.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    return JSON.parse(out.slice(start, end + 1));
  } catch {
    return null;
  }
}

function runNode(scriptRel, args, timeoutMs = 90000) {
  const script = path.join(REPO, scriptRel);
  const r = spawnSync("node", [script, ...args], {
    encoding: "utf8",
    cwd: REPO,
    timeout: timeoutMs,
    maxBuffer: 8 * 1024 * 1024,
  });
  const out = (r.stdout || "").trim();
  const json = tryParseJson(out);
  return {
    exitCode: r.status ?? 1,
    stdout: out.slice(-4000),
    stderr: (r.stderr || "").slice(-800),
    json,
  };
}

function redact(raw) {
  if (!raw) return raw;
  try {
    const u = new URL(raw);
    return `${u.origin}${u.pathname}${u.search ? "?REDACTED" : ""}`;
  } catch {
    return String(raw).replace(/\?.*$/, "?REDACTED");
  }
}

async function listPages() {
  const res = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!res.ok) throw new Error(`CDP list failed: ${res.status}`);
  const all = await res.json();
  return all.filter((t) => t.type === "page" && t.url && !t.url.startsWith("chrome"));
}

const startedAt = new Date().toISOString();
const results = [];

let version = null;
try {
  version = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
} catch (e) {
  const fail = {
    status: "CDP_DOWN",
    port,
    error: String(e.message || e),
    startedAt,
  };
  console.log(JSON.stringify(fail, null, 2));
  process.exit(2);
}

const pagesBefore = await listPages();

for (const lane of lanes) {
  const entry = {
    lane: lane.id,
    match: lane.match,
    required: lane.required,
    present: false,
    dedupe: null,
    restore: null,
    probe: null,
  };

  // Refresh each iteration so prior dedupe/close is visible.
  const pagesNow = await listPages();
  const matching = pagesNow.filter(
    (p) => new RegExp(lane.match, "i").test(p.url || "") || new RegExp(lane.match, "i").test(p.title || ""),
  );
  entry.present = matching.length > 0;
  entry.page_count = matching.length;
  entry.urls = matching.slice(0, 5).map((p) => redact(p.url));

  if (!entry.present) {
    entry.probe = { status: "LANE_ABSENT" };
    results.push(entry);
    continue;
  }

  if (!noDedupe && matching.length > 1) {
    entry.dedupe = runNode("tools/browser_ai_supervisor/dedupe_lane_tabs_cdp.mjs", [
      "--port",
      String(port),
      "--match",
      lane.match,
    ]).json;
  }

  if (!noRestore || observe) {
    // --no-bring-to-front prevents multi-lane "tab travel" focus thrash.
    // Observe mode still dwells so a human can glance — keep dwell short (default 400–1500ms).
    const restoreArgs = [
      "--port",
      String(port),
      "--mode",
      observe ? "maximized" : "normal",
      "--match",
      lane.match,
      "--no-bring-to-front",
    ];
    entry.restore = runNode("tools/browser_ai_supervisor/grok_cdp_restore_window.mjs", restoreArgs).json;
    if (observe) {
      // Only activate/bring front in explicit observe mode, one lane at a time.
      try {
        await fetch(`http://127.0.0.1:${port}/json/activate/${matching[0].id}`);
      } catch {
        /* ignore */
      }
      await new Promise((r) => setTimeout(r, observeDwellMs));
      entry.observe_dwell_ms = observeDwellMs;
    }
  }

  // --pickFirst: multi-chat same host (e.g. two Qwen threads) is normal; pick primary.
  const probeRun = runNode(
    "tools/browser_ai_supervisor/grok_cdp_context_probe.mjs",
    [
      "--port",
      String(port),
      "--required",
      lane.required,
      "--maxChars",
      "1200",
      "--pickFirst",
    ],
    120000,
  );
  entry.probe = probeRun.json || {
    status: "PROBE_FAIL",
    exitCode: probeRun.exitCode,
    stderr: probeRun.stderr,
    stdout_tail: probeRun.stdout.slice(-500),
  };
  if (entry.probe?.status === "READY" && entry.probe.state) {
    entry.probe = {
      status: "READY",
      title: entry.probe.target?.title || entry.probe.state?.title,
      url: redact(entry.probe.target?.url || entry.probe.state?.url),
      readyState: entry.probe.state.readyState,
      inputs: (entry.probe.state.inputs || []).slice(0, 3),
      hasSubmit: (entry.probe.state.buttons || []).some((b) => /submit/i.test(b.label || "")),
      tailLen: (entry.probe.state.tailText || "").length,
    };
  }

  results.push(entry);
}

const pagesAfter = await listPages();
const ready = results.filter((r) => r.probe?.status === "READY").map((r) => r.lane);
const absent = results.filter((r) => r.probe?.status === "LANE_ABSENT").map((r) => r.lane);
const blocked = results
  .filter((r) => r.probe && !["READY", "LANE_ABSENT"].includes(r.probe.status))
  .map((r) => ({ lane: r.lane, status: r.probe.status, blocker: r.probe.blocker || r.probe.reason }));

const summary = {
  status: blocked.length === 0 && ready.length > 0 ? "STACK_READY" : blocked.length ? "STACK_PARTIAL" : "STACK_EMPTY",
  port,
  browser: version?.Browser || null,
  mode: observe ? "observe_existing_cdp_chrome" : "silent_preflight",
  note:
    "Reuses authenticated Chrome on this CDP port. Does not launch a new browser and does not send chat messages. Use send_grok_cdp.ps1 / director for real conversation I/O.",
  startedAt,
  finishedAt: new Date().toISOString(),
  page_count_before: pagesBefore.length,
  page_count_after: pagesAfter.length,
  ready_lanes: ready,
  absent_lanes: absent,
  blocked_lanes: blocked,
  lanes: results,
};

if (ledger) {
  try {
    const dir = path.dirname(ledger);
    fs.mkdirSync(dir, { recursive: true });
    const rec = {
      ts: summary.finishedAt,
      kind: "lane_stack_preflight",
      agent: "grok-build-0.1",
      port,
      status: summary.status,
      ready_lanes: ready,
      absent_lanes: absent,
      blocked_lanes: blocked,
      page_count: summary.page_count_after,
    };
    fs.appendFileSync(ledger, JSON.stringify(rec) + "\n", "utf8");
    summary.ledger_appended = ledger;
  } catch (e) {
    summary.ledger_error = String(e.message || e);
  }
}

console.log(JSON.stringify(summary, null, 2));
process.exit(summary.status === "STACK_READY" || summary.status === "STACK_PARTIAL" ? 0 : 2);
