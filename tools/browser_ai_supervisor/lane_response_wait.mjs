#!/usr/bin/env node
/**
 * Wait until a browser-AI lane finishes generating (observe Thinking / Thought for / Zo is thinking).
 * Records elapsed polls; optional baseline tail length after Hermes send.
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../..");

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

export function analyzeLaneActivity(laneMatch, state) {
  const tail = String(state?.tailText || "");
  const buttons = (state?.buttons || []).map((b) => b.label || "").join("\n");
  const blob = `${tail}\n${buttons}`;
  const lower = blob.toLowerCase();
  const lane = String(laneMatch || "").toLowerCase();
  const signals = [];

  if (lane.includes("zo")) {
    if (/zo is thinking/i.test(blob)) signals.push("zo_thinking");
  }
  if (lane.includes("grok")) {
    if (/thought for \d/i.test(blob)) signals.push("grok_thought_for");
    if (/\bthinking\b/i.test(blob) && !/finished thinking/i.test(lower)) signals.push("thinking_text");
    if (/stop generating/i.test(lower)) signals.push("stop_generating");
  }
  if (lane.includes("chatgpt")) {
    if (/stop generating/i.test(lower)) signals.push("chatgpt_stop_generating");
    if (/\bthinking\b/i.test(blob)) signals.push("chatgpt_thinking");
    if (/researching/i.test(lower)) signals.push("chatgpt_researching");
  }

  const generating = signals.length > 0;
  return {
    phase: generating ? "generating" : "idle",
    signals,
    tailLen: tail.length,
    tailSnippet: tail.slice(-500),
  };
}

function runProbe(port, required, maxChars) {
  return new Promise((resolve, reject) => {
    const probePath = path.join(__dirname, "grok_cdp_context_probe.mjs");
    const child = spawn(
      process.execPath,
      [probePath, "--port", String(port), "--required", required, "--maxChars", String(maxChars)],
      { cwd: REPO, stdio: ["ignore", "pipe", "pipe"] },
    );
    let stdout = "";
    child.stdout.on("data", (d) => {
      stdout += d;
    });
    child.stderr.on("data", (d) => {
      stdout += d;
    });
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`probe exit ${code}: ${stdout.slice(0, 800)}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        reject(new Error(`probe json parse: ${e.message}`));
      }
    });
  });
}

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const required = args.required ?? "grok.com";
const taskClass = args.taskClass ?? "general";
const agentId = args.agentId ?? required.replace(/\.com$/, "").replace(/\./g, "_");
const maxWaitSec = Number(args.maxWaitSec ?? 600);
const pollSec = Number(args.pollSec ?? 4);
const baselineTailLen = Number(args.baselineTailLen ?? 0);
const minGrowth = Number(args.minGrowth ?? 40);
const stablePolls = Number(args.stablePolls ?? 2);
const mode = String(args.mode ?? "response");

const started = Date.now();
const polls = [];
let lastLen = -1;
let stableIdle = 0;

while ((Date.now() - started) / 1000 < maxWaitSec) {
  const elapsedSec = Math.round((Date.now() - started) / 1000);
  let probe;
  try {
    probe = await runProbe(port, required, 3500);
  } catch (err) {
    polls.push({ elapsedSec, error: String(err.message || err) });
    await new Promise((r) => setTimeout(r, pollSec * 1000));
    continue;
  }

  const state = probe.state || {};
  const act = analyzeLaneActivity(required, state);
  polls.push({
    elapsedSec,
    phase: act.phase,
    signals: act.signals,
    tailLen: act.tailLen,
  });

  if (act.phase === "generating") {
    stableIdle = 0;
    process.stdout.write(
      `[lane-wait] ${agentId} ${taskClass} +${elapsedSec}s generating signals=${act.signals.join(",")}\n`,
    );
    await new Promise((r) => setTimeout(r, pollSec * 1000));
    continue;
  }

  if (mode === "preidle") {
    const result = {
      status: "IDLE_READY",
      agentId,
      taskClass,
      required,
      elapsedSec,
      pollCount: polls.length,
      phase: "idle",
      polls,
    };
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }

  const grew = act.tailLen >= baselineTailLen + minGrowth;
  if (act.tailLen === lastLen && grew) stableIdle += 1;
  else stableIdle = 0;
  lastLen = act.tailLen;

  if (grew && stableIdle >= stablePolls) {
    const result = {
      status: "RESPONSE_READY",
      agentId,
      taskClass,
      required,
      elapsedSec,
      pollCount: polls.length,
      baselineTailLen,
      finalTailLen: act.tailLen,
      tailSnippet: act.tailSnippet,
      polls,
    };
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }

  process.stdout.write(
    `[lane-wait] ${agentId} +${elapsedSec}s idle tail=${act.tailLen} stable=${stableIdle}/${stablePolls}\n`,
  );
  await new Promise((r) => setTimeout(r, pollSec * 1000));
}

const elapsedSec = Math.round((Date.now() - started) / 1000);
console.log(
  JSON.stringify(
    {
      status: "TIMEOUT",
      agentId,
      taskClass,
      required,
      elapsedSec,
      pollCount: polls.length,
      polls: polls.slice(-20),
    },
    null,
    2,
  ),
);
process.exit(1);