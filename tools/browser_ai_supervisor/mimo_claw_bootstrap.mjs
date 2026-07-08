#!/usr/bin/env node
/** MiMo Studio: open home and click Create Now for Claw sandbox (1–5 min). */
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const home = (process.env.NEXUS_MIMO_CLAW_URL || "https://aistudio.xiaomimimo.com/#/").trim();
const maxWaitSec = Number(process.argv.find((a, i) => process.argv[i - 1] === "--waitSec") ?? 300);

const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
let page = list.find((t) => t.type === "page" && /xiaomimimo\.com/i.test(t.url || ""));
if (!page) {
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
  await send("Target.createTarget", { url: home });
  ws.close();
  await new Promise((r) => setTimeout(r, 4000));
  const list2 = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
  page = list2.find((t) => t.type === "page" && /xiaomimimo\.com/i.test(t.url || ""));
}

if (!page) {
  console.log(JSON.stringify({ status: "MIMO_TAB_MISSING" }));
  process.exit(2);
}

const cdp = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r, j) => {
  cdp.addEventListener("open", r, { once: true });
  cdp.addEventListener("error", j, { once: true });
});
let nid = 1;
const csend = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const my = nid++;
    const h = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id === my) {
        cdp.removeEventListener("message", h);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
    cdp.addEventListener("message", h);
    cdp.send(JSON.stringify({ id: my, method, params }));
  });

await csend("Runtime.enable");
await csend("Page.navigate", { url: home });
await new Promise((r) => setTimeout(r, 5000));

const clickExpr = `(() => {
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 8 && r.height > 8 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const label = (el) => (el.innerText || el.textContent || el.getAttribute('aria-label') || '').replace(/\\s+/g,' ').trim();
  const nodes = [...document.querySelectorAll('button,a,[role=button],div,span')].filter(isVisible);
  const hit = nodes.find((el) => /create\\s*now|创建|新建.*claw|mimo\\s*claw/i.test(label(el)));
  if (!hit) return { clicked: false, samples: nodes.slice(0, 30).map(label).filter(Boolean).slice(0, 12) };
  hit.click();
  return { clicked: true, label: label(hit).slice(0, 120) };
})()`;

const clickRes = await csend("Runtime.evaluate", { expression: clickExpr, returnByValue: true });
const clicked = clickRes.result?.value || { clicked: false };

const started = Date.now();
let sandbox = false;
while ((Date.now() - started) / 1000 < maxWaitSec) {
  const probe = await csend("Runtime.evaluate", {
    expression: `(() => {
      const t = (document.body?.innerText || '').slice(0, 8000);
      return {
        hasSandbox: /sandbox|沙箱|project logs|claw/i.test(t),
        trial: (t.match(/(\\d+)\\s*h(?:our)?/i) || [])[0] || '',
        snippet: t.slice(-600),
      };
    })()`,
    returnByValue: true,
  });
  const v = probe.result?.value || {};
  if (v.hasSandbox) {
    sandbox = true;
    console.log(JSON.stringify({ status: "MIMO_CLAW_SANDBOX_VISIBLE", clicked, probe: v }, null, 2));
    cdp.close();
    process.exit(0);
  }
  await new Promise((r) => setTimeout(r, 8000));
}

console.log(JSON.stringify({ status: "MIMO_CLAW_WAIT_TIMEOUT", clicked, maxWaitSec }, null, 2));
cdp.close();
process.exit(1);