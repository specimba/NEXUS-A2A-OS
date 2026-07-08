#!/usr/bin/env node
/** Open Grok project chat tab only if none exists (avoid duplicate Grok tabs on restore). */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const grokUrl = (
  process.env.NEXUS_GROK_PROJECT_CHAT_URL ||
  process.env.NEXUS_GROK_PROJECT_URL ||
  "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba"
).trim();

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const hit = list.find(
  (t) => t.type === "page" && t.url && /grok\.com/i.test(t.url) && !t.url.startsWith("chrome-extension")
);
if (hit) {
  console.log(JSON.stringify({ status: "GROK_TAB_EXISTS", title: hit.title, url: hit.url }));
  process.exit(0);
}

const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
const wsock = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((res, rej) => {
  wsock.addEventListener("open", res, { once: true });
  wsock.addEventListener("error", rej, { once: true });
});
let id = 1;
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const my = id++;
    const handler = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id === my) {
        wsock.removeEventListener("message", handler);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
    wsock.addEventListener("message", handler);
    wsock.send(JSON.stringify({ id: my, method, params }));
  });
await send("Target.createTarget", { url: grokUrl });
wsock.close();
console.log(JSON.stringify({ status: "OPENED_GROK_TAB", url: grokUrl }));