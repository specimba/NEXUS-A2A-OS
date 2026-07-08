#!/usr/bin/env node
/** Open ChatGPT tab in lane Chrome :9224. */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const url =
  (process.env.NEXUS_CHATGPT_CHAT_URL || process.env.NEXUS_OPENAI_CHAT_URL || "https://chatgpt.com/").trim();

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const hit = list.find(
  (t) => t.type === "page" && t.url && /chatgpt\.com|chat\.openai\.com/i.test(t.url)
);
if (hit) {
  console.log(JSON.stringify({ status: "CHATGPT_TAB_EXISTS", title: hit.title, url: hit.url }));
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
await send("Target.createTarget", { url });
wsock.close();
console.log(JSON.stringify({ status: "OPENED_CHATGPT_TAB", url }));