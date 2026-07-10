#!/usr/bin/env node
/**
 * If a lane composer still holds draft text, try Enter + best Send click.
 * Usage: node lane_submit_flush_cdp.mjs --port 9224 --required deepseek.com
 */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const required = process.argv.find((a, i) => process.argv[i - 1] === "--required") ?? "deepseek.com";

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const t = list.find(
  (x) =>
    x.type === "page" &&
    x.url &&
    (x.url.includes(required) || (x.title || "").includes(required)),
);
if (!t) {
  console.log(JSON.stringify({ status: "NO_TARGET", required }, null, 2));
  process.exit(2);
}

const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => {
  const timer = setTimeout(() => rej(new Error("ws timeout")), 10000);
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
try {
  await send("Page.bringToFront");
} catch {
  /* ignore */
}

const mapExpr = `(() => {
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
  };
  const composers = [...document.querySelectorAll("textarea, [contenteditable='true'], [role='textbox']")]
    .filter(isVisible)
    .map((el, i) => ({
      i,
      tag: el.tagName,
      aria: el.getAttribute("aria-label"),
      placeholder: el.getAttribute("placeholder"),
      len: (el.innerText || el.value || "").length,
      preview: (el.innerText || el.value || "").slice(0, 60),
    }));
  const controls = [...document.querySelectorAll("button, [role='button'], div[class*='send'], span[class*='send'], [data-testid]")]
    .filter(isVisible)
    .slice(0, 80)
    .map((el, i) => ({
      i,
      tag: el.tagName,
      aria: el.getAttribute("aria-label"),
      title: el.getAttribute("title"),
      testid: el.getAttribute("data-testid"),
      cls: (el.className || "").toString().slice(0, 80),
      text: (el.innerText || "").trim().slice(0, 40),
      disabled: !!el.disabled,
    }));
  return { composers, controls };
})()`;

const mapped = await send("Runtime.evaluate", { expression: mapExpr, returnByValue: true });
const map = mapped.result?.value;

// Try Enter on focused composer
await send("Input.dispatchKeyEvent", {
  type: "rawKeyDown",
  key: "Enter",
  code: "Enter",
  windowsVirtualKeyCode: 13,
  nativeVirtualKeyCode: 13,
});
await send("Input.dispatchKeyEvent", {
  type: "keyDown",
  key: "Enter",
  code: "Enter",
  windowsVirtualKeyCode: 13,
  nativeVirtualKeyCode: 13,
});
await send("Input.dispatchKeyEvent", {
  type: "keyUp",
  key: "Enter",
  code: "Enter",
  windowsVirtualKeyCode: 13,
  nativeVirtualKeyCode: 13,
});

const clickExpr = `(() => {
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && !el.disabled;
  };
  const nodes = [...document.querySelectorAll("button, [role='button'], div, span")].filter(isVisible);
  const score = (el) => {
    const aria = (el.getAttribute("aria-label") || "").toLowerCase();
    const title = (el.getAttribute("title") || "").toLowerCase();
    const testid = (el.getAttribute("data-testid") || "").toLowerCase();
    const cls = (el.className || "").toString().toLowerCase();
    const text = (el.innerText || "").trim().toLowerCase();
    const r = el.getBoundingClientRect();
    let s = 0;
    if (aria === "send" || title === "send" || text === "send") s += 100;
    if (/send/.test(aria) || /send/.test(title) || /send/.test(testid) || /send/.test(cls)) s += 40;
    if (/submit/.test(aria)) s += 30;
    // DeepSeek: primary filled circle icon button next to composer
    if (cls.includes("ds-button--primary") && cls.includes("ds-button--circle")) s += 90;
    if (cls.includes("ds-button--primary") && cls.includes("ds-button--filled")) s += 50;
    if (cls.includes("ds-button") && r.bottom > window.innerHeight * 0.75 && r.width <= 64 && r.height <= 64) s += 25;
    // icon-only near bottom (composer row)
    if (r.bottom > window.innerHeight * 0.7 && r.width < 80 && r.height < 80) s += 5;
    return s;
  };
  const ranked = nodes.map((el) => ({ el, s: score(el) })).filter((x) => x.s >= 40).sort((a, b) => b.s - a.s);
  if (!ranked.length) return { clicked: false, reason: "NO_SEND_CANDIDATE", scored: 0, topScores: [] };
  const top = ranked[0].el;
  top.click();
  return {
    clicked: true,
    score: ranked[0].s,
    aria: top.getAttribute("aria-label"),
    title: top.getAttribute("title"),
    text: (top.innerText || "").trim().slice(0, 40),
    cls: (top.className || "").toString().slice(0, 80),
    topScores: ranked.slice(0, 3).map((x) => ({ s: x.s, cls: (x.el.className || "").toString().slice(0, 50) })),
  };
})()`;

const clicked = await send("Runtime.evaluate", { expression: clickExpr, returnByValue: true });
await new Promise((r) => setTimeout(r, 800));

const after = await send("Runtime.evaluate", {
  expression: `(() => {
    const isVisible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const composers = [...document.querySelectorAll("textarea, [contenteditable='true'], [role='textbox']")].filter(isVisible);
    const c = composers[composers.length - 1];
    return {
      composerLen: c ? (c.innerText || c.value || "").length : -1,
      bodyLen: (document.body && document.body.innerText || "").length,
    };
  })()`,
  returnByValue: true,
});

ws.close();
console.log(
  JSON.stringify(
    {
      status: "FLUSH_ATTEMPTED",
      target: { title: t.title, url: (t.url || "").replace(/\?.*$/, "?REDACTED") },
      map,
      click: clicked.result?.value,
      after: after.result?.value,
    },
    null,
    2,
  ),
);
