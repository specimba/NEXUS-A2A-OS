import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  appendJsonlEvent,
  sha256Text,
  snapshotSearch,
} from "../../tools/browser_ai_supervisor/a2a_cycle_evidence.mjs";

test("snapshot prefers assistant-only evidence and retains CDP identity", () => {
  const snapshot = snapshotSearch({
    target: { id: "target-1", url: "https://chat.qwen.ai/c/demo" },
    result: {
      len: 999,
      assistantLen: 42,
      last1500: "user text",
      assistantLast1500: "assistant text",
    },
  });

  assert.equal(snapshot.cdpTargetId, "target-1");
  assert.equal(snapshot.url, "https://chat.qwen.ai/c/demo");
  assert.equal(snapshot.tail, "assistant text");
  assert.equal(snapshot.textLength, 42);
  assert.equal(snapshot.tailHash, sha256Text("assistant text"));
});

test("event append returns exact JSONL offsets", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "nexus-a2a-evidence-"));
  const events = path.join(root, "events.jsonl");
  const first = appendJsonlEvent(events, { type: "SEND_PING", cycle: 1 });
  const second = appendJsonlEvent(events, { type: "WAIT_RESULT", cycle: 1 });

  assert.equal(first, 0);
  assert.equal(second, Buffer.byteLength('{"type":"SEND_PING","cycle":1}\n'));
  const rows = fs.readFileSync(events, "utf8").trim().split("\n").map(JSON.parse);
  assert.deepEqual(rows.map((row) => row.type), ["SEND_PING", "WAIT_RESULT"]);
});

test("cycle controller only accepts verifier-backed assistant evidence", () => {
  const controller = fs.readFileSync(
    path.resolve("tools/browser_ai_supervisor/multi_lane_a2a_cycle.mjs"), "utf8",
  );
  assert.match(controller, /const gated = verifyLaneEvidence/);
  assert.match(controller, /success = entry\.status === "VERIFIED"/);
  assert.match(controller, /success_mode === "preview_not_chat"/);
  assert.match(controller, /probePreview\(lane\)/);
  assert.doesNotMatch(controller, /REPLY_COLLECTED|TOKEN_PRESENT|SEND_UNCERTAIN/);
});
