#!/usr/bin/env node
/**
 * Qwen WebDev success probe — do NOT wait for chat essays.
 * Success = Preview / Code / Deploy / artifact UI present after a task.
 *
 * Selectors from ARCHIVIST/QWENdevbrowserALLpositionsREVEALED.md
 *
 * Usage:
 *   node qwen_preview_success_probe.mjs --port 9224
 *   node qwen_preview_success_probe.mjs --port 9224 --required a321e504
 *   node qwen_preview_success_probe.mjs --port 9224 --reload
 */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const required =
  process.argv.find((a, i) => process.argv[i - 1] === "--required") ?? "chat.qwen.ai";
const doReload = process.argv.includes("--reload");

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const t = list.find(
  (x) =>
    x.type === "page" &&
    x.url &&
    (x.url.includes(required) || (x.title || "").includes(required)),
);
if (!t) {
  console.log(JSON.stringify({ status: "NO_TARGET", required, port }, null, 2));
  process.exit(2);
}

// Wake sleeping tabs before CDP attach (Chrome debugger often times out otherwise)
try {
  await fetch(`http://127.0.0.1:${port}/json/activate/${t.id}`);
} catch {
  /* best-effort */
}
await new Promise((r) => setTimeout(r, 800));

const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => {
  const timer = setTimeout(() => rej(new Error("ws timeout")), 15000);
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
    const timer = setTimeout(() => reject(new Error(`timeout ${method}`)), 25000);
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
await send("Page.enable").catch(() => {});
await send("Page.bringToFront").catch(() => {});
if (doReload) {
  await send("Page.reload", { ignoreCache: false }).catch(() => {});
  await new Promise((r) => setTimeout(r, 3500));
  await send("Runtime.enable").catch(() => {});
}

const r = await send("Runtime.evaluate", {
  returnByValue: true,
  expression: `(() => {
    const visible = (el) => {
      if (!el) return false;
      const rect = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && s.display !== "none" && s.visibility !== "hidden";
    };
    const q = (sel) => {
      try { return [...document.querySelectorAll(sel)].filter(visible); } catch { return []; }
    };
    const previewBtns = q("button.qwen-chat-btn, .qwen-chat-btn, [class*='preview']")
      .filter((el) => /preview/i.test(el.innerText || "") || /preview/i.test(el.className || ""));
    const deployBtns = q("button, .qwen-chat-btn")
      .filter((el) => /deploy/i.test(el.innerText || "") || /deploy/i.test(el.className || ""));
    const codeTabs = q("button, [role='tab'], a")
      .filter((el) => /^(code|preview|deploy)$/i.test((el.innerText || "").trim()));
    const artifact = q(".artifact-wrapper, [class*='artifact'], .artifacts-body, [class*='artifacts-body']");
    const sendBtn = q(".message-input-right-button-send, .chat-prompt-send-button, button.send-button");
    const composer = q("textarea[placeholder*='web page'], textarea[placeholder*='Describe'], textarea, [contenteditable='true']");
    const signals = {
      preview_buttons: previewBtns.length,
      deploy_buttons: deployBtns.length,
      code_preview_tabs: codeTabs.map((el) => (el.innerText || "").trim()).slice(0, 8),
      artifact_nodes: artifact.length,
      send_controls: sendBtn.length,
      composers: composer.length,
      body_has_preview_word: /\\bpreview\\b/i.test(document.body?.innerText || ""),
    };
    const success =
      signals.preview_buttons > 0 ||
      signals.deploy_buttons > 0 ||
      signals.artifact_nodes > 0 ||
      signals.code_preview_tabs.some((t) => /preview|code|deploy/i.test(t));
    return {
      status: success ? "PREVIEW_SUCCESS" : "NO_PREVIEW_SIGNAL",
      success,
      signals,
      note: "Qwen WebDev: success = Code/Preview/Deploy UI, not chat essay length",
      title: document.title,
      url: location.href,
    };
  })()`,
});

ws.close();
const val = r.result?.value || { status: "EVAL_FAIL" };
console.log(JSON.stringify({
  port,
  required,
  activated: true,
  reloaded: doReload,
  target: { id: t.id, title: t.title, url: (t.url || "").replace(/\?.*/, "?REDACTED") },
  ...val,
}, null, 2));
process.exit(val.success ? 0 : 2);
