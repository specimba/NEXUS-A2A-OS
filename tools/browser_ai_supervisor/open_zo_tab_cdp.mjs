#!/usr/bin/env node
/** Open Zo chat as a tab in the CDP lane Chrome (port 9224). */
import fs from "node:fs";

const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const zoUrl =
  process.env.NEXUS_ZO_CHAT_URL?.trim() ||
  "https://specimba.zo.computer/?chat=con_EL8I2vKUvldsLVJ6";

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => {
  if (!r.ok) throw new Error(`CDP list ${r.status}`);
  return r.json();
});
const existing = list.find((t) => t.type === "page" && /zo\.computer/i.test(t.url || ""));
if (existing) {
  console.log(JSON.stringify({ status: "ZO_TAB_EXISTS", title: existing.title, url: existing.url }, null, 2));
  process.exit(0);
}

const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
const ws = new WebSocket(ver.webSocketDebuggerUrl);
let id = 1;
const result = await new Promise((resolve, reject) => {
  const t = setTimeout(() => reject(new Error("timeout")), 10000);
  ws.onopen = () => {
    ws.send(JSON.stringify({ id: id++, method: "Target.createTarget", params: { url: zoUrl } }));
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id === 1) {
      clearTimeout(t);
      resolve(msg.result);
    }
  };
  ws.onerror = () => reject(new Error("ws error"));
});
ws.close();
console.log(JSON.stringify({ status: "ZO_TAB_OPENED", targetId: result.targetId, url: zoUrl }, null, 2));