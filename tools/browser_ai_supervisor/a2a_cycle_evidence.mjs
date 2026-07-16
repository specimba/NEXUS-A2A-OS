import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

export function sha256Text(value) {
  return crypto.createHash("sha256").update(String(value || ""), "utf8").digest("hex");
}

export function snapshotSearch(search) {
  const payload = search?.json || search || {};
  const result = payload.result || {};
  const assistantTail = String(result.assistantLast1500 || result.last1500 || "");
  const textLength = Number(
    result.assistantLen ?? result.len ?? assistantTail.length,
  );
  return {
    cdpTargetId: payload.target?.id || null,
    url: payload.target?.url || result.url || null,
    tail: assistantTail,
    tailHash: sha256Text(assistantTail),
    textLength: Number.isFinite(textLength) ? textLength : assistantTail.length,
  };
}

export function appendJsonlEvent(eventsPath, record) {
  const target = path.resolve(eventsPath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const offset = fs.existsSync(target) ? fs.statSync(target).size : 0;
  fs.appendFileSync(target, JSON.stringify(record) + "\n", "utf8");
  return offset;
}

function parseLastJson(text) {
  const lines = String(text || "").trim().split(/\r?\n/).reverse();
  for (const line of lines) {
    try {
      return JSON.parse(line);
    } catch {
      // CLI diagnostics may precede its one JSON result.
    }
  }
  return null;
}

export function verifyCycleEvidence({
  evidence,
  eventsPath,
  registryPath,
  tailExcerpt = "",
  python = process.env.NEXUS_A2A_PYTHON,
}) {
  const executable = python || (process.platform === "win32" ? "py" : "python3");
  const prefix = python ? [] : process.platform === "win32" ? ["-3.13"] : [];
  const args = [
    ...prefix,
    "-m",
    "nexus_os.nexusclaw.a2a_evidence_cli",
    "verify",
    "--json",
    JSON.stringify(evidence),
    "--events",
    path.resolve(eventsPath),
    "--registry",
    path.resolve(registryPath),
    "--tail-excerpt",
    String(tailExcerpt || "").slice(-1800),
  ];
  const run = spawnSync(executable, args, {
    encoding: "utf8",
    timeout: 30000,
    maxBuffer: 1024 * 1024,
  });
  const payload = parseLastJson(run.stdout);
  return {
    exitCode: run.status ?? 1,
    verdict: payload?.verdict || "UNPROVEN",
    failures: Array.isArray(payload?.failures) ? payload.failures : [],
    stderr: String(run.stderr || "").slice(-800),
  };
}
