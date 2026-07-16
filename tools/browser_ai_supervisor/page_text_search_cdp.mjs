#!/usr/bin/env node
/** Search visible page text on a CDP target for proof tokens. */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const required = process.argv.find((a, i) => process.argv[i - 1] === "--required") ?? "grok.com";
const needles = (process.argv.find((a, i) => process.argv[i - 1] === "--needles") ?? "NEXUS_PROOF_OK,NEXUS CDP proof ping")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const t = list.find(
  (x) =>
    x.type === "page" &&
    x.url &&
    (x.url.includes(required) || (x.title || "").includes(required)),
);
if (!t) {
  console.log(JSON.stringify({ status: "NO_TARGET", port, required }, null, 2));
  process.exit(2);
}

const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => {
  const timer = setTimeout(() => rej(new Error("ws timeout")), 8000);
  ws.addEventListener("open", () => {
    clearTimeout(timer);
    res();
  }, { once: true });
  ws.addEventListener("error", () => {
    clearTimeout(timer);
    rej(new Error("ws error"));
  }, { once: true });
});

let id = 1;
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const my = id++;
    const timer = setTimeout(() => reject(new Error(`timeout ${method}`)), 20000);
    const h = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id === my) {
        clearTimeout(timer);
        ws.removeEventListener("message", h);
        if (m.error) reject(m.error);
        else resolve(m.result);
      }
    };
    ws.addEventListener("message", h);
    ws.send(JSON.stringify({ id: my, method, params }));
  });

await send("Runtime.enable");
const expr = `(() => {
  // Prefer lane-specific content roots (DeepSeek shell body is ~title only).
  const roots = [];
  const assistantRoots = [];
  const pickAssistant = (sel) => {
    try {
      document.querySelectorAll(sel).forEach((el) => {
        roots.push(el);
        assistantRoots.push(el);
      });
    } catch {}
  };
  const pick = (sel) => {
    try {
      document.querySelectorAll(sel).forEach((el) => roots.push(el));
    } catch {}
  };
  pickAssistant(".ds-markdown.ds-assistant-message-main-content");
  pickAssistant(".ds-assistant-message-main-content");
  pickAssistant("[class*='assistant-message']");
  pick(".qwen-chat-message");
  pick(".artifacts-body");
  pick("main");
  let body = "";
  if (roots.length) {
    body = roots.map((el) => el.innerText || "").join("\\n");
  }
  if (!body || body.length < 40) {
    body = (document.body && document.body.innerText) || "";
  }
  const assistantText = assistantRoots.map((el) => el.innerText || "").join("\n");
  const needles = ${JSON.stringify(needles)};
  const hits = {};
  for (const n of needles) hits[n] = body.includes(n);
  return {
    hits,
    len: body.length,
    last1500: body.slice(-1500),
    assistantLen: assistantText.length,
    assistantLast1500: assistantText.slice(-1500),
    title: document.title,
    url: location.href,
    rootCount: roots.length,
  };
})()`;
const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: false });
ws.close();
console.log(
  JSON.stringify(
    {
      status: "SEARCHED",
      target: { id: t.id, title: t.title, url: (t.url || "").replace(/\?.*$/, "?REDACTED") },
      result: r.result?.value || r.result,
    },
    null,
    2,
  ),
);
