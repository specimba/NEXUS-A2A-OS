#!/usr/bin/env node
/**
 * Close duplicate page targets for a lane URL pattern on a CDP port.
 * Keeps the first matching page per normalized URL; closes extras.
 *
 * Usage:
 *   node dedupe_lane_tabs_cdp.mjs --port 9224 --match grok\\.com [--dry-run]
 */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const matchArg = process.argv.find((a, i) => process.argv[i - 1] === "--match") ?? "grok\\.com";
const dryRun = process.argv.includes("--dry-run");
const urlRe = new RegExp(matchArg, "i");

function normUrl(raw) {
  if (!raw) return "";
  try {
    const u = new URL(raw);
    // Same project/chat without query noise counts as same lane surface
    return `${u.origin}${u.pathname}`;
  } catch {
    return String(raw).split("?")[0];
  }
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

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const pages = list.filter(
  (t) =>
    t.type === "page" &&
    t.url &&
    urlRe.test(t.url) &&
    !t.url.startsWith("chrome-extension") &&
    !t.url.startsWith("chrome://"),
);

const byKey = new Map();
for (const p of pages) {
  const key = normUrl(p.url);
  if (!byKey.has(key)) byKey.set(key, []);
  byKey.get(key).push(p);
}

const keep = [];
const close = [];
for (const [, group] of byKey) {
  keep.push(group[0]);
  for (let i = 1; i < group.length; i += 1) close.push(group[i]);
}

if (close.length === 0) {
  console.log(
    JSON.stringify(
      {
        status: "NO_DUPES",
        port,
        match: matchArg,
        kept: keep.map((p) => ({ id: p.id, title: p.title, url: redact(p.url) })),
      },
      null,
      2,
    ),
  );
  process.exit(0);
}

if (dryRun) {
  console.log(
    JSON.stringify(
      {
        status: "DRY_RUN_WOULD_CLOSE",
        port,
        match: matchArg,
        wouldClose: close.map((p) => ({ id: p.id, title: p.title, url: redact(p.url) })),
        keep: keep.map((p) => ({ id: p.id, title: p.title, url: redact(p.url) })),
      },
      null,
      2,
    ),
  );
  process.exit(0);
}

const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
const ws = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((r, j) => {
  ws.addEventListener("open", r, { once: true });
  ws.addEventListener("error", j, { once: true });
});
let id = 1;
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const my = id++;
    const h = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id === my) {
        ws.removeEventListener("message", h);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
    ws.addEventListener("message", h);
    ws.send(JSON.stringify({ id: my, method, params }));
  });

const closed = [];
const errors = [];
for (const tab of close) {
  try {
    await send("Target.closeTarget", { targetId: tab.id });
    closed.push({ id: tab.id, title: tab.title, url: redact(tab.url) });
  } catch (e) {
    errors.push({ id: tab.id, error: String(e?.message || e) });
  }
}
ws.close();

console.log(
  JSON.stringify(
    {
      status: "DEDUPE_DONE",
      port,
      match: matchArg,
      closed,
      errors,
      kept: keep.map((p) => ({ id: p.id, title: p.title, url: redact(p.url) })),
    },
    null,
    2,
  ),
);
process.exit(errors.length ? 1 : 0);
