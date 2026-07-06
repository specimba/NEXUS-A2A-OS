#!/usr/bin/env node
/**
 * Long-run A2A browser experiment — probe, optional send, wait, record timing.
 * Zero API cost: CDP-only lane agents.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../..");
const REGISTRY = path.join(REPO, "nexus_os/nexusclaw/browser_lane_registry.json");
const LOG_ROOT = process.env.NEXUS_A2A_EXPERIMENT_DIR || "C:/Users/speci.000/Downloads/NEXUSlogs/a2a_experiment";
const COLLAB_LOCK = path.join(LOG_ROOT, "COLLAB_LOCK.json");
const PROTECTED_LANES = new Set(["grok", "chatgpt_gpt55", "zo"]);

async function deliberationWait(lane, importance = "normal") {
  const baseWait = importance === "high" ? 45000 : 30000;
  if (importance === "high" || lane === "grok") {
    await new Promise(r => setTimeout(r, baseWait));
    console.log(`[GROK-PLAN] Deliberation wait applied for ${lane} (COLLAB_LOCK + Mythos scaffold)`);
  }
}


function readCollabLock() {
  try {
    const j = JSON.parse(fs.readFileSync(COLLAB_LOCK, "utf8"));
    return Boolean(j.locked);
  } catch {
    return false;
  }
}

function parseArgs(argv) {
  const out = { port: 9224, durationMin: 90, cycleMin: 12, send: false, lanes: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--port") out.port = Number(argv[++i]);
    else if (a === "--duration-min") out.durationMin = Number(argv[++i]);
    else if (a === "--cycle-min") out.cycleMin = Number(argv[++i]);
    else if (a === "--send") out.send = true;
    else if (a === "--lanes") out.lanes = argv[++i] || "";
  }
  return out;
}

function ts() {
  return new Date().toISOString();
}

function appendJsonl(file, obj) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let offset = 0;
  try {
    offset = fs.statSync(file).size;
  } catch {
    offset = 0;
  }
  fs.appendFileSync(file, `${JSON.stringify({ ...obj, ts: ts() })}\n`, "utf8");
  return offset;
}

function sha256Hex(text) {
  return crypto.createHash("sha256").update(String(text ?? ""), "utf8").digest("hex");
}

function runPs1File(scriptPath, psArgs = []) {
  const r = spawnSync(
    "powershell.exe",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath, ...psArgs],
    { encoding: "utf8", timeout: 600000, cwd: REPO },
  );
  return {
    exit: r.status,
    stdout: (r.stdout || "").slice(-12000),
    stderr: (r.stderr || "").slice(-6000),
  };
}

function runNode(rel, nodeArgs = []) {
  const r = spawnSync("node", [path.join(REPO, rel), ...nodeArgs], {
    encoding: "utf8",
    timeout: 120000,
    cwd: REPO,
  });
  return { exit: r.status, stdout: (r.stdout || "").slice(-12000), stderr: (r.stderr || "").slice(-4000) };
}

const args = parseArgs(process.argv.slice(2));
const sessionId = `a2a_${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}`;
const sessionDir = path.join(LOG_ROOT, sessionId);
const eventsPath = path.join(sessionDir, "events.jsonl");
const registry = JSON.parse(fs.readFileSync(REGISTRY, "utf8"));

let laneFilter = null;
if (args.lanes) laneFilter = new Set(args.lanes.split(",").map((s) => s.trim()).filter(Boolean));

const priorityLanes = registry.lanes
  .filter((l) => (laneFilter ? laneFilter.has(l.id) : (l.priority || 9) <= 2))
  .sort((a, b) => (a.priority || 9) - (b.priority || 9));

appendJsonl(eventsPath, {
  type: "SESSION_START",
  sessionId,
  durationMin: args.durationMin,
  cycleMin: args.cycleMin,
  send: args.send,
  collabLock: readCollabLock(),
  laneCount: priorityLanes.length,
  lanes: priorityLanes.map((l) => l.id),
});

const endAt = Date.now() + args.durationMin * 60 * 1000;
let cycle = 0;
let verifiedCycles = 0;
let simulatedCycles = 0;

while (Date.now() < endAt) {
  cycle += 1;
  appendJsonl(eventsPath, { type: "CYCLE_START", cycle });

  const collabLock = readCollabLock();

  if (collabLock) {
    const lockedSet = new Set(["grok", "chatgpt_gpt55", "zo", "glm_5_2", "gemini_app", "apodex_discover"]);
    priorityLanes = priorityLanes.filter(l => lockedSet.has(l.id) || (l.priority || 9) <= 1);
  }

  const stab =
    cycle === 1 && !collabLock
      ? runPs1File(path.join(REPO, "scripts/align_browser_lanes.ps1"), ["-Port", String(args.port), "-SkipEnsure"])
      : { exit: 0, stdout: collabLock ? "align_skip_collab_lock" : "align_skip" };
  appendJsonl(eventsPath, { type: "ALIGN", cycle, exit: stab.exit, stdoutTail: stab.stdout.slice(-500) });

  if (!collabLock && cycle === 1) {
    const inv = runNode("tools/browser_ai_supervisor/open_or_navigate_lane.mjs", [
      "--port",
      String(args.port),
      "--all",
    ]);
    let invJson = null;
    try {
      invJson = JSON.parse(inv.stdout);
    } catch {
      invJson = { parseError: true, stdout: inv.stdout.slice(-2000) };
    }
    appendJsonl(eventsPath, { type: "LANE_ALIGN", cycle, exit: inv.exit, results: invJson?.results || [] });
  } else if (collabLock) {
    appendJsonl(eventsPath, { type: "LANE_ALIGN_SKIPPED", cycle, reason: "collab_lock_probe_only" });
  }

  await deliberationWait('grok', 'high');
  for (const lane of priorityLanes) {
    await deliberationWait(lane.id, 'normal');
    const probe = runNode("tools/browser_ai_supervisor/lane_registry_probe.mjs", [
      "--port",
      String(args.port),
      "--lane",
      lane.id,
    ]);
    let probeData = null;
    try {
      probeData = JSON.parse(probe.stdout);
    } catch {
      probeData = { raw: probe.stdout.slice(-1500), stderr: probe.stderr };
    }
    const tail = probeData?.tail || "";
    const generating = Boolean(probeData?.generating);

    appendJsonl(eventsPath, {
      type: "PROBE",
      cycle,
      lane: lane.id,
      agent_id: lane.agent_id,
      generating,
      tailLen: probeData?.tailLen ?? tail.length,
      title: probeData?.title || null,
      url: probeData?.url || probeData?.pickUrl || null,
      excerpt: tail.slice(-400),
      probeExit: probeData?.exit,
    });

    const maySend = args.send && !collabLock && !generating && !PROTECTED_LANES.has(lane.id);
    if (PROTECTED_LANES.has(lane.id) && args.send) {
      appendJsonl(eventsPath, { type: "SEND_SKIPPED", cycle, lane: lane.id, reason: "protected_tri_lane" });
    }
    if (maySend) {
      const prompt = `[A2A-EXP cycle=${cycle}] Hermes zero-cost probe. Reply one line: [${lane.agent_id.toUpperCase()}-PING] ok + elapsed guess seconds.`;
      const relPf = path.join("scratch", "a2a_experiment", sessionId, `ping_${lane.id}.txt`);
      const absPf = path.join(REPO, relPf);
      fs.mkdirSync(path.dirname(absPf), { recursive: true });
      fs.writeFileSync(absPf, prompt, "utf8");
      const sendScript = path.join(
        REPO,
        lane.id === "zo"
          ? "tools/browser_ai_supervisor/send_zo_cdp.ps1"
          : lane.id === "chatgpt_gpt55"
            ? "tools/browser_ai_supervisor/send_chatgpt_cdp.ps1"
            : "tools/browser_ai_supervisor/send_grok_cdp.ps1",
      );
      const sendArgs =
        lane.id === "zo"
          ? [
              "-Port",
              String(args.port),
              "-PromptFile",
              relPf,
              "-SkipRestore",
              "-SkipWait",
              "-NoWait",
            ]
          : [
              "-Port",
              String(args.port),
              "-PromptFile",
              relPf,
              "-SkipRestore",
              "-NoWait",
            ];
      const sendTs = ts();
      const send = runPs1File(sendScript, sendArgs);
      const sendOffset = appendJsonl(eventsPath, {
        type: "SEND_PING",
        cycle,
        lane: lane.id,
        exit: send.exit,
        stderr: send.stderr?.slice(-800),
      });

      const wait = runPs1File(path.join(REPO, "tools/browser_ai_supervisor/wait_lane_response.ps1"), [
        "-Port",
        String(args.port),
        "-Required",
        lane.required_probe,
        "-AgentId",
        lane.agent_id,
        "-TaskClass",
        "a2a_ping",
        "-MaxWaitSec",
        "240",
        "-BaselineTailLen",
        String(probeData?.tailLen ?? 0),
      ]);
      let waitJson = null;
      try {
        const lines = (wait.stdout || "").trim().split("\n");
        waitJson = JSON.parse(lines[lines.length - 1]);
      } catch {
        waitJson = { raw: (wait.stdout || "").slice(-2000) };
      }
      const waitOffset = appendJsonl(eventsPath, { type: "WAIT_RESULT", cycle, lane: lane.id, wait: waitJson });
      const responseTs = ts();

      const py = path.join(REPO, ".venv/Scripts/python.exe");
      const rec = spawnSync(
        py,
        [
          "-m",
          "nexus_os.nexusclaw.lane_timing_cli",
          "record",
          "--task-class",
          "a2a_ping",
          "--json",
          JSON.stringify(waitJson),
        ],
        { encoding: "utf8", cwd: REPO, timeout: 60000 },
      );
      appendJsonl(eventsPath, { type: "TIMING_RECORD", cycle, lane: lane.id, exit: rec.status });

      // Evidence gate: re-probe once for tail_after/targetId, then let the
      // python verifier recompute the verdict from primary evidence.
      const reProbe = runNode("tools/browser_ai_supervisor/lane_registry_probe.mjs", [
        "--port",
        String(args.port),
        "--lane",
        lane.id,
      ]);
      let reProbeData = null;
      try {
        reProbeData = JSON.parse(reProbe.stdout);
      } catch {
        reProbeData = {};
      }
      const evidenceRecord = {
        schema: 1,
        session_id: sessionId,
        cycle,
        lane: lane.id,
        agent_id: lane.agent_id,
        cdp_target_id: reProbeData?.targetId || probeData?.targetId || null,
        url: reProbeData?.url || reProbeData?.pickUrl || null,
        prompt_sha256: sha256Hex(prompt),
        tail_before_sha256: probeData?.tailSha256 || "",
        tail_after_sha256: reProbeData?.tailSha256 || "",
        tail_growth: (reProbeData?.tailLen ?? 0) - (probeData?.tailLen ?? 0),
        send_ts: sendTs,
        response_ts: responseTs,
        elapsed_sec: Number(waitJson?.elapsedSec ?? 0),
        wait_status: waitJson?.status || "",
        send_offset: sendOffset,
        wait_offset: waitOffset,
      };
      const verify = spawnSync(
        py,
        [
          "-m",
          "nexus_os.nexusclaw.a2a_evidence_cli",
          "verify",
          "--json",
          JSON.stringify(evidenceRecord),
          "--events",
          eventsPath,
          "--tail-excerpt",
          (reProbeData?.tail || "").slice(-2000),
        ],
        { encoding: "utf8", cwd: REPO, timeout: 60000 },
      );
      let verdictJson = null;
      try {
        const vLines = (verify.stdout || "").trim().split("\n");
        verdictJson = JSON.parse(vLines[vLines.length - 1]);
      } catch {
        verdictJson = { verdict: "SIMULATED", failures: ["verifier_unavailable"] };
      }
      evidenceRecord.verdict = verdictJson?.verdict || "SIMULATED";
      evidenceRecord.failures = verdictJson?.failures || [];
      if (evidenceRecord.verdict === "VERIFIED") verifiedCycles += 1;
      else if (evidenceRecord.verdict === "SIMULATED") simulatedCycles += 1;
      appendJsonl(eventsPath, {
        type: "CYCLE_EVIDENCE",
        cycle,
        lane: lane.id,
        verdict: evidenceRecord.verdict,
        failures: evidenceRecord.failures,
        evidence: evidenceRecord,
      });
    } else {
      // Probe-only lane this cycle: no send attempted, so the cycle is UNPROVEN.
      appendJsonl(eventsPath, {
        type: "CYCLE_EVIDENCE",
        cycle,
        lane: lane.id,
        verdict: "UNPROVEN",
        failures: [],
        evidence: {
          schema: 1,
          session_id: sessionId,
          cycle,
          lane: lane.id,
          agent_id: lane.agent_id,
          cdp_target_id: probeData?.targetId || null,
          url: probeData?.url || probeData?.pickUrl || null,
          tail_before_sha256: probeData?.tailSha256 || "",
          tail_after_sha256: probeData?.tailSha256 || "",
          send_offset: -1,
          wait_offset: -1,
          verdict: "UNPROVEN",
          failures: [],
        },
      });
    }
  }

  if (cycle % 3 === 0) {
    const chain = ["grok", "chatgpt_gpt55", "zo"];
    appendJsonl(eventsPath, {
      type: "A2A_CHAIN_PLAN",
      cycle,
      chain,
      note: "Handoff tags for human/agent paste — no auto blast to all",
    });
  }

  const reportPath = path.join(sessionDir, `cycle_${String(cycle).padStart(3, "0")}_summary.json`);
  fs.writeFileSync(
    reportPath,
    JSON.stringify(
      {
        cycle,
        at: ts(),
        lanesProbed: priorityLanes.length,
        nextCycleMin: args.cycleMin,
      },
      null,
      2,
    ),
    "utf8",
  );

  const remainingMs = endAt - Date.now();
  if (remainingMs <= 0) break;
  const sleepMs = Math.min(args.cycleMin * 60 * 1000, remainingMs);
  appendJsonl(eventsPath, { type: "CYCLE_SLEEP", cycle, sleepSec: Math.floor(sleepMs / 1000) });
  await new Promise((r) => setTimeout(r, sleepMs));
}

const aggScript = path.join(REPO, "nexus_os/nexusclaw/a2a_experiment_aggregate.py");
const agg = spawnSync(
  path.join(REPO, ".venv/Scripts/python.exe"),
  [aggScript, "--session-dir", sessionDir],
  { encoding: "utf8", cwd: REPO },
);

appendJsonl(eventsPath, {
  type: "SESSION_END",
  cycle,
  aggregateExit: agg.status,
  verified_cycles: verifiedCycles,
  simulated_cycles: simulatedCycles,
});
console.log(
  JSON.stringify({
    status: "A2A_EXPERIMENT_COMPLETE",
    sessionId,
    sessionDir,
    cycles: cycle,
    report: path.join(sessionDir, "FINAL_REPORT.md"),
    aggregateStdout: (agg.stdout || "").slice(-3000),
  }),
);