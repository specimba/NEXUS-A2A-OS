#!/usr/bin/env node
/** Close disposable about:blank / new-tab pages when real lane tabs exist. */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const pages = list.filter((t) => t.type === "page");
const real = pages.filter(
  (t) =>
    t.url &&
    !t.url.startsWith("about:") &&
    !t.url.startsWith("chrome://") &&
    t.url.length > 12,
);
if (real.length < 2) {
  console.log(JSON.stringify({ status: "SKIP_PRUNE", real: real.length }));
  process.exit(0);
}
const disposable = pages.filter(
  (t) =>
    !t.url ||
    t.url === "about:blank" ||
    t.url.startsWith("chrome://newtab"),
);
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
for (const tab of disposable) {
  try {
    await send("Target.closeTarget", { targetId: tab.id });
    closed.push(tab.id);
  } catch {}
}
ws.close();
console.log(JSON.stringify({ status: "PRUNED_BLANK_TABS", closed: closed.length, ids: closed }));