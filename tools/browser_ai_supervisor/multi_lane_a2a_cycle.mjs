#!/usr/bin/env node
/**
 * Multi-lane A2A collaboration cycle on authenticated CDP Chrome.
 * Sends role prompts and proves assistant-side response evidence before recording a result.
 *
 * Usage:
 *   node multi_lane_a2a_cycle.mjs --port 9224 --phase 1
 *   node multi_lane_a2a_cycle.mjs --port 9224 --phase 2
 *   node multi_lane_a2a_cycle.mjs --port 9224 --phase all --maxWaitSec 180
 */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { appendJsonlEvent, sha256Text, snapshotSearch, verifyCycleEvidence } from "./a2a_cycle_evidence.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../..");
const PROMPT_DIR = path.join(__dirname, "prompts", "a2a_cycle1");
const DEFAULT_LEDGER =
  process.platform === "win32"
    ? "C:\\Users\\speci.000\\Downloads\\NEXUSlogs\\NEXUScontinuity_runs.jsonl"
    : "/mnt/c/Users/speci.000/Downloads/NEXUSlogs/NEXUScontinuity_runs.jsonl";
const REPORT_DIR =
  process.platform === "win32"
    ? "C:\\Users\\speci.000\\Downloads\\NEXUSlogs\\private_team_20260709_grok45_scratch"
    : "/mnt/c/Users/speci.000/Downloads/NEXUSlogs/private_team_20260709_grok45_scratch";

const LANE_REGISTRY = path.join(REPO, "nexus_os", "nexusclaw", "browser_lane_registry.json");
const REGISTRY_ALIASES = {
  chatgpt: "chatgpt_gpt55",
  deepseek: "deepseek_expert",
  gemini: "gemini_app",
  qwen_deep: "qwen_deep_research",
  glm52: "glm_5_2",
  apodex: "apodex_discover",
};
let sessionEventsPath = null;
let sessionId = null;
let nextEvidenceCycle = 1;

function registryLaneId(lane) {
  return REGISTRY_ALIASES[lane.id] || lane.id;
}
function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = process.argv[i + 1];
  if (!v || v.startsWith("--")) return true;
  return v;
}

const port = Number(arg("port", 9224));
const phase = String(arg("phase", "1"));
const maxWaitSec = Number(arg("maxWaitSec", 150));
const pollSec = Number(arg("pollSec", 6));
const ledger = arg("ledger", process.env.NEXUS_CONTINUITY_LEDGER || DEFAULT_LEDGER);
const dryRun = process.argv.includes("--dry-run");

/** @type {{id:string, required:string, token:string, prompt:string, retries:number, note:string}[]} */
const PHASE1 = [
  {
    id: "grok",
    required: "4d8d8598-9da7-4639-918e-4ceb6a8812ba",
    token: "NEXUS_A2A_C1_GROK",
    prompt: "01_grok_coordinator.md",
    retries: 1,
    note: "coordinator + MCP sandbox",
  },
  {
    id: "chatgpt",
    required: "6a4600ec-0db0-83eb-932c-9d3496adbba0",
    token: "NEXUS_A2A_C1_CHATGPT",
    prompt: "02_chatgpt_mcp_architect.md",
    retries: 1,
    note: "MCP architect GPT-5.x",
  },
  {
    id: "deepseek",
    required: "07b0a633-9279-40c0-9015-86e088bb7d9e",
    token: "NEXUS_A2A_C1_DEEPSEEK",
    prompt: "03_deepseek_scout.md",
    retries: 1,
    note: "coding scout/hunter",
  },
  {
    id: "gemini",
    required: "6fba62a56f165a08",
    token: "NEXUS_A2A_C1_GEMINI",
    prompt: "04_gemini_canvas_cloud.md",
    retries: 1,
    note: "canvas + cloud project",
  },
  {
    id: "qwen_deep",
    required: "4d6ea806-a03e-4732-9077-2711d522867e",
    token: "NEXUS_A2A_C1_QWEN_DEEP",
    prompt: "05_qwen_deep_research.md",
    retries: 1,
    note: "deep research / eval",
  },
  {
    id: "qwen_webdev",
    required: "a321e504-d549-4ebd-b4db-e6313a73c774",
    token: "NEXUS_A2A_C1_QWEN_WEBDEV",
    prompt: "06_qwen_webdev_canvas.md",
    retries: 1,
    note: "HTML/JSON canvas — success=preview/code not chat wait",
    success_mode: "preview_not_chat",
  },
  {
    id: "glm52",
    required: "1b1cd50b-c78c-403d-9280-0612c76a56b3",
    token: "NEXUS_A2A_C1_GLM52",
    prompt: "07_glm52_nextjs.md",
    retries: 3,
    note: "GLM-5.2 only; retry, never switch model",
  },
  {
    id: "zo",
    required: "con_EL8I2vKUvldsLVJ6",
    token: "NEXUS_A2A_C1_ZO",
    prompt: "08_zo_hunter.md",
    retries: 1,
    note: "cloud Linux hunter",
  },
  {
    id: "apodex",
    required: "apodex.ai",
    token: "NEXUS_A2A_C1_APODEX",
    prompt: "09_apodex_deep_team.md",
    retries: 1,
    note: "multi-agent deep search",
  },
];

const PHASE2 = [
  {
    id: "grok_synth",
    required: "4d8d8598-9da7-4639-918e-4ceb6a8812ba",
    token: "NEXUS_A2A_C1_SYNTH",
    prompt: "10_grok_synthesize.md",
    retries: 2,
    note: "synthesize multi-lane into playbook",
  },
];

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

function runNode(scriptRel, args, timeoutMs = 180000) {
  const script = path.join(REPO, scriptRel);
  const r = spawnSync("node", [script, ...args], {
    encoding: "utf8",
    cwd: REPO,
    timeout: timeoutMs,
    maxBuffer: 12 * 1024 * 1024,
  });
  const out = (r.stdout || "").trim();
  return {
    exitCode: r.status ?? 1,
    stdout: out.slice(-6000),
    stderr: (r.stderr || "").slice(-1200),
    json: tryParseJson(out),
  };
}

function appendLedger(row) {
  if (!sessionEventsPath) return "events_path_uninitialized";
  try {
    return appendJsonlEvent(sessionEventsPath, row);
  } catch (e) {
    return String(e.message || e);
  }
}

async function listPages() {
  const res = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!res.ok) throw new Error(`CDP list ${res.status}`);
  return (await res.json()).filter((t) => t.type === "page" && t.url);
}

function pagePresent(pages, required) {
  return pages.some(
    (p) =>
      (p.url && p.url.includes(required)) ||
      (p.title && p.title.includes(required)),
  );
}

async function searchPage(required, needles) {
  return runNode(
    "tools/browser_ai_supervisor/page_text_search_cdp.mjs",
    ["--port", String(port), "--required", required, "--needles", needles.join(",")],
    60000,
  );
}

async function waitForToken(required, token, maxSec) {
  const deadline = Date.now() + maxSec * 1000;
  let last = null;
  while (Date.now() < deadline) {
    last = await searchPage(required, [token, "NEXUS_A2A_C1"]);
    const hits = last.json?.result?.hits || {};
    if (hits[token]) {
      return { ok: true, search: last.json };
    }
    await new Promise((r) => setTimeout(r, pollSec * 1000));
  }
  return { ok: false, search: last?.json || null };
}

function restoreLane(required) {
  // Use host-ish match for restore helper; conversation keys also work if in title/url after restore.
  const match =
    required.includes(".") || required.includes("-")
      ? required.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
      : required;
  return runNode(
    "tools/browser_ai_supervisor/grok_cdp_restore_window.mjs",
    ["--port", String(port), "--mode", "normal", "--match", match],
    30000,
  );
}

function sendPrompt(required, promptFile) {
  const full = path.join(PROMPT_DIR, promptFile);
  return runNode(
    "tools/browser_ai_supervisor/grok_cdp_director.mjs",
    [
      "--port",
      String(port),
      "--required",
      required,
      "--send",
      "--operatorFocus",
      "--promptFile",
      full,
    ],
    120000,
  );
}

async function runLane(lane) {
  const started = new Date().toISOString();
  const evidenceCycle = nextEvidenceCycle++;
  const pages = await listPages();
  const present = pagePresent(pages, lane.required);
  const entry = {
    lane: lane.id,
    required: lane.required,
    token: lane.token,
    note: lane.note,
    present,
    started,
    send: null,
    evidence_cycle: evidenceCycle,
    wait: null,
    attempts: 0,
  };
  if (!present) {
    entry.status = "LANE_ABSENT";
    entry.finished = new Date().toISOString();
    appendLedger({
      ts: entry.finished,
      kind: "a2a_lane_result",
      cycle: "NEXUS_A2A_C1",
      lane: lane.id,
      status: entry.status,
      port,
    });
    return entry;
  }

  restoreLane(lane.required);
  let attempt = 0;
  let success = false;
  while (attempt < lane.retries && !success) {
    attempt += 1;
    entry.attempts = attempt;
    if (dryRun) {
      entry.status = "DRY_RUN";
      break;
    }
    const promptText = fs.readFileSync(path.join(PROMPT_DIR, lane.prompt), "utf8");
    const beforeSearch = await searchPage(lane.required, [lane.token, "HANDOFF"]);
    const before = snapshotSearch(beforeSearch.json);
    const sentAt = new Date().toISOString();
    const sendOffset = appendJsonlEvent(sessionEventsPath, {
      type: "SEND_PING",
      cycle: evidenceCycle,
      lane: registryLaneId(lane),
      ts: sentAt,
      cdp_target_id: before.cdpTargetId,
      url: before.url,
      prompt_sha256: sha256Text(promptText),
    });
    const sendRes = sendPrompt(lane.required, lane.prompt);
    entry.send = {
      exitCode: sendRes.exitCode,
      director: sendRes.json,
      landed: sendRes.json?.send?.landed,
      ok: sendRes.json?.send?.ok,
    };
    // A token can appear in the user prompt, so it is only a pacing signal.
    // The evidence gate below requires an assistant-side tail delta.
    const wait = await waitForToken(lane.required, lane.token, maxWaitSec);
    const waitSnapshot = snapshotSearch(wait.search);
    entry.wait = {
      token_visible: wait.ok,
      hits: wait.search?.result?.hits,
      assistant_tail_sha256: waitSnapshot.tailHash,
      assistant_len: waitSnapshot.textLength,
    };
    if (entry.send.ok || entry.send.landed || wait.ok) {
      // Re-search after a bounded settling interval; a send/token heuristic
      // cannot substitute for the persisted evidence gate.
      await new Promise((r) => setTimeout(r, 8000));
      const again = await searchPage(lane.required, [lane.token, "HANDOFF"]);
      const after = snapshotSearch(again.json);
      let artifactProof = {};
      if (lane.success_mode === "preview_not_chat") {
        const preview = probePreview(lane);
        artifactProof = preview.json || { status: "PREVIEW_PROBE_FAILED", success: false };
      }
      const respondedAt = new Date().toISOString();
      const tailGrew = after.tailHash !== before.tailHash
        && after.textLength > before.textLength;
      const waitStatus = tailGrew ? "RESPONSE_READY" : "RESPONSE_UNPROVEN";
      const waitOffset = appendJsonlEvent(sessionEventsPath, {
        type: "WAIT_RESULT",
        cycle: evidenceCycle,
        lane: registryLaneId(lane),
        ts: respondedAt,
        wait: { status: waitStatus },
        cdp_target_id: after.cdpTargetId || before.cdpTargetId,
        tail_growth: Math.max(0, after.textLength - before.textLength),
      });
      entry.collect = {
        hits: again.json?.result?.hits,
        assistant_len: after.textLength,
        assistant_tail_sha256: after.tailHash,
        tail_growth: Math.max(0, after.textLength - before.textLength),
      };
      if (tailGrew) {
        const gated = verifyLaneEvidence({
          lane,
          cycle: evidenceCycle,
          promptText,
          before,
          after,
          sentAt,
          respondedAt,
          sendOffset,
          waitOffset,
          artifactProof,
        });
        entry.evidence = gated.evidence;
        entry.verification = gated.verification;
        entry.status = gated.verification.verdict === "VERIFIED"
          ? "VERIFIED"
          : "UNPROVEN_EVIDENCE";
      } else {
        entry.verification = {
          verdict: "UNPROVEN",
          failures: ["no_assistant_tail_delta", "no_assistant_tail_growth"],
        };
        entry.status = "UNPROVEN_EVIDENCE";
      }
      success = entry.status === "VERIFIED";
      if (!success && attempt < lane.retries) {
        // Bounded patience; a failed gate is not a success claim.
        await new Promise((r) => setTimeout(r, 5000 * attempt));
      }
    } else if (attempt < lane.retries) {
      await new Promise((r) => setTimeout(r, 5000 * attempt));
    } else {
      entry.status = "SEND_FAILED";
    }
  }
  entry.finished = new Date().toISOString();
  appendLedger({
    ts: entry.finished,
    kind: "a2a_lane_result",
    cycle: "NEXUS_A2A_C1",
    agent: "multi_lane_a2a_cycle",
    lane: lane.id,
    status: entry.status,
    attempts: entry.attempts,
    port,
    token: lane.token,
    landed: entry.send?.landed || false,
  });
  return entry;
}

async function main() {
  const startedAt = new Date().toISOString();
  let version = null;
  try {
    version = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
  } catch (e) {
    console.log(JSON.stringify({ status: "CDP_DOWN", error: String(e.message || e) }, null, 2));
    process.exit(2);
  }

  const lanes =
    phase === "2" ? PHASE2 : phase === "all" ? [...PHASE1, ...PHASE2] : PHASE1;

  fs.mkdirSync(REPORT_DIR, { recursive: true });
  sessionId = `NEXUS_A2A_C1_${Date.now()}`;
  sessionEventsPath = path.join(REPORT_DIR, `${sessionId}.events.jsonl`);

  appendLedger({
    ts: startedAt,
    kind: "a2a_cycle_start",
    cycle: "NEXUS_A2A_C1",
    phase,
    port,
    browser: version?.Browser,
    lanes: lanes.map((l) => l.id),
  });

  const results = [];
  for (const lane of lanes) {
    console.error(`[A2A] lane=${lane.id} token=${lane.token} ...`);
    const r = await runLane(lane);
    results.push(r);
    console.error(`[A2A] lane=${lane.id} status=${r.status}`);
  }

  const finishedAt = new Date().toISOString();
  const summary = {
    status: "A2A_CYCLE_DONE",
    cycle: "NEXUS_A2A_C1",
    phase,
    port,
    browser: version?.Browser,
    startedAt,
    finishedAt,
    events_path: sessionEventsPath,
    requested_legacy_ledger: ledger,
    counts: {
      total: results.length,
      verified: results.filter((r) => r.status === "VERIFIED").length,
      unproven: results.filter((r) => r.status === "UNPROVEN_EVIDENCE").length,
      absent: results.filter((r) => r.status === "LANE_ABSENT").length,
      failed: results.filter((r) => r.status === "SEND_FAILED").length,
    },
    results,
  };

  const reportPath = path.join(REPORT_DIR, `NEXUS_A2A_C1_phase${phase}_${Date.now()}.json`);
  fs.writeFileSync(reportPath, JSON.stringify(summary, null, 2), "utf8");
  summary.report_path = reportPath;

  appendLedger({
    ts: finishedAt,
    kind: "a2a_cycle_done",
    cycle: "NEXUS_A2A_C1",
    phase,
    port,
    status: summary.status,
    counts: summary.counts,
    report_path: reportPath,
  });

  console.log(JSON.stringify(summary, null, 2));
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
function probePreview(lane) {
  return runNode(
    "tools/browser_ai_supervisor/qwen_preview_success_probe.mjs",
    ["--port", String(port), "--required", lane.required],
    60000,
  );
}

function verifyLaneEvidence({
  lane,
  cycle,
  promptText,
  before,
  after,
  sentAt,
  respondedAt,
  sendOffset,
  waitOffset,
  artifactProof,
}) {
  const elapsedSec = Math.max(
    0,
    (Date.parse(respondedAt) - Date.parse(sentAt)) / 1000,
  );
  const evidence = {
    schema: 1,
    session_id: sessionId,
    cycle,
    lane: registryLaneId(lane),
    agent_id: lane.id,
    cdp_target_id: after.cdpTargetId || before.cdpTargetId,
    url: after.url || before.url,
    prompt_sha256: sha256Text(promptText),
    tail_before_sha256: before.tailHash,
    tail_after_sha256: after.tailHash,
    tail_growth: Math.max(0, after.textLength - before.textLength),
    send_ts: sentAt,
    response_ts: respondedAt,
    elapsed_sec: elapsedSec,
    wait_status: "RESPONSE_READY",
    send_offset: sendOffset,
    wait_offset: waitOffset,
    success_mode: lane.success_mode || "chat_response",
    artifact_proof: artifactProof || {},
  };
  const verification = verifyCycleEvidence({
    evidence,
    eventsPath: sessionEventsPath,
    registryPath: LANE_REGISTRY,
    tailExcerpt: after.tail,
  });
  return { evidence, verification };
}
