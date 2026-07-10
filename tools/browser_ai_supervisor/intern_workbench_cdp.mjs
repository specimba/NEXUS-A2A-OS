#!/usr/bin/env node
/**
 * Intern-AI Shanghai workbench CDP controller.
 * Reuses multi-lane Chrome :9224 — navigate / map / start / enter / smoke (best-effort).
 *
 * Usage:
 *   node intern_workbench_cdp.mjs --port 9224 --phase map
 *   node intern_workbench_cdp.mjs --port 9224 --phase start --machine NEXUS-GPU-test1
 *   node intern_workbench_cdp.mjs --port 9224 --phase all --machine NEXUS-GPU-test1
 *   node intern_workbench_cdp.mjs --port 9224 --phase stop --machine NEXUS-GPU-test1
 *
 * Hardening: no Browser.close, no random Target.create if intern tab exists,
 * no auto-create machine, no dataset mounts.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.argv.find((a, i) => process.argv[i - 1] === "--port") ?? 9224);
const phase = process.argv.find((a, i) => process.argv[i - 1] === "--phase") ?? "map";
const machine =
  process.argv.find((a, i) => process.argv[i - 1] === "--machine") ?? "NEXUS-GPU-test1";
const machineIdHint =
  process.argv.find((a, i) => process.argv[i - 1] === "--id") ?? "2fc615787f57753d";
const outDir =
  process.argv.find((a, i) => process.argv[i - 1] === "--outDir") ??
  "C:/Users/speci.000/Downloads/NEXUSlogs";
const waitSec = Number(process.argv.find((a, i) => process.argv[i - 1] === "--wait") ?? 180);

const WORKBENCH_LIST = "https://d.intern-ai.org.cn/workbench";
const WORKBENCH_HOSTS = ["d.intern-ai.org.cn", "discovery.intern-ai.org.cn"];

const SMOKE_CMD = [
  "mkdir -p /data/NEXUS/{repo_sync,checkpoints,datasets,benches,logs,kv_cache_studies}",
  "nvidia-smi",
  'python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else None); open(\'/data/NEXUS/logs/smoke_gpu.txt\',\'w\').write(\'ok\\n\')"',
].join(" && ");

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function listPages() {
  const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
  return list.filter((x) => x.type === "page" && x.url);
}

function pickInternTab(pages) {
  // Prefer d.intern workbench over discovery notebook for machine control
  const wb = pages.find((p) => /d\.intern-ai\.org\.cn\/workbench/i.test(p.url));
  if (wb) return wb;
  const any = pages.find((p) => WORKBENCH_HOSTS.some((h) => p.url.includes(h)));
  return any || null;
}

async function activate(id) {
  try {
    await fetch(`http://127.0.0.1:${port}/json/activate/${id}`);
  } catch {
    /* ignore */
  }
  await sleep(600);
}

function connectWs(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const timer = setTimeout(() => reject(new Error("ws timeout")), 20000);
    ws.addEventListener("open", () => {
      clearTimeout(timer);
      resolve(ws);
    }, { once: true });
    ws.addEventListener("error", () => {
      clearTimeout(timer);
      reject(new Error("ws error"));
    }, { once: true });
  });
}

function makeSend(ws) {
  let id = 1;
  return (method, params = {}) =>
    new Promise((resolve, reject) => {
      const my = id++;
      const timer = setTimeout(() => reject(new Error(`timeout ${method}`)), 30000);
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
}

async function evalInPage(send, expression) {
  const r = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.exceptionDetails) {
    throw new Error(r.exceptionDetails.text || "eval exception");
  }
  return r.result?.value;
}

async function navigate(send, url) {
  await send("Page.enable").catch(() => {});
  await send("Network.enable").catch(() => {});
  await send("Page.navigate", { url });
  // SPA: poll until body has content or timeout
  const deadline = Date.now() + 25000;
  while (Date.now() < deadline) {
    await sleep(1500);
    try {
      const st = await evalInPage(
        send,
        `({
          ready: document.readyState,
          len: (document.body?.innerText || "").length,
          html: document.documentElement?.outerHTML?.length || 0,
          url: location.href,
        })`,
      );
      if (st && (st.len > 40 || st.html > 5000) && st.ready === "complete") break;
    } catch {
      /* keep waiting */
    }
  }
  await sleep(2000);
}

async function settle(send, ms = 8000) {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    await sleep(1200);
    try {
      const len = await evalInPage(send, "(document.body?.innerText || '').length");
      if (typeof len === "number" && len > 80) return len;
    } catch {
      /* */
    }
  }
  return 0;
}

const MAP_EXPR = `(() => {
  const visible = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden";
  };
  const textOf = (el) => (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
  const nodes = [...document.querySelectorAll("button, a, [role='button'], div, span, li, tr")];
  const interesting = [];
  const re = /start|stop|enter|启动|停止|进入|running|stopped|suspended|运行|停止|NEXUS|GPU|workbench|dev-machine|notebook|create|资源/i;
  for (const el of nodes) {
    if (!visible(el)) continue;
    const t = textOf(el);
    if (!t || t.length > 200) continue;
    if (!re.test(t) && !re.test(el.getAttribute("aria-label") || "")) continue;
    const r = el.getBoundingClientRect();
    interesting.push({
      tag: el.tagName,
      text: t.slice(0, 120),
      aria: el.getAttribute("aria-label"),
      role: el.getAttribute("role"),
      href: el.href || null,
      cls: (typeof el.className === "string" ? el.className : "").slice(0, 80),
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
    });
    if (interesting.length >= 80) break;
  }
  const bodyText = (document.body?.innerText || "").slice(0, 4000);
  const hasMachine = /NEXUS-GPU-test1|2fc615787f57753d|nb-2fc615/i.test(bodyText);
  const countMatch = bodyText.match(/共\\s*(\\d+)\\s*个/);
  const machineCount = countMatch ? Number(countMatch[1]) : null;
  const pointsMatch = bodyText.match(/算力余额[：:]\\s*(\\d+)/) || bodyText.match(/(\\d+)\\s*算力点/);
  const points = pointsMatch ? Number(pointsMatch[1]) : null;
  const skeletonOnly = /_cardSkeleton|未知\\s*GPU/i.test(document.body?.innerHTML || "") && machineCount === 0;
  const statusHints = {
    stopped: /stopped|suspended|已停止|已挂起|已暂停/i.test(bodyText),
    running: /running|运行中|使用中/i.test(bodyText),
    login: /login|sign in|登录|鉴权|password/i.test(bodyText) && !hasMachine,
    emptyList: machineCount === 0,
    skeletonOnly,
  };
  return {
    url: location.href,
    title: document.title,
    hasMachineName: hasMachine,
    machineCount,
    points,
    statusHints,
    interesting,
    bodySnippet: bodyText.slice(0, 1500),
    selectors: {
      card: "._devMachineCard_imvaq_9, [class*='devMachineCard']",
      enterBtn: "button._enterBtn_imvaq_206, button[class*='enterBtn']",
      actionBtn: "button._actionBtn_imvaq_180, button[class*='actionBtn']",
      navDevMachines: "我的开发机",
      createHint: "创建|新建|create",
    },
  };
})()`;

function clickExpr(machineName, machineId, actionReSource) {
  return `(() => {
    const actionRe = ${actionReSource};
    const machineRe = /${machineName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}|${machineId}/i;
    const visible = (el) => {
      if (!el) return false;
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden";
    };
    const textOf = (el) => (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();

    // Prefer button/link near machine text
    const cards = [...document.querySelectorAll("div, li, tr, section, article")].filter(visible);
    let bestBtn = null;
    let bestScore = -1;
    let context = "";

    for (const card of cards) {
      const ct = textOf(card);
      if (!machineRe.test(ct)) continue;
      if (ct.length > 2500) continue; // too big, not a card
      const btns = [...card.querySelectorAll("button, a, [role='button']")].filter(visible);
      for (const b of btns) {
        const t = textOf(b) + " " + (b.getAttribute("aria-label") || "");
        if (!actionRe.test(t)) continue;
        const score = 100 - Math.min(ct.length / 20, 50);
        if (score > bestScore) {
          bestScore = score;
          bestBtn = b;
          context = ct.slice(0, 200);
        }
      }
    }

    // Global fallback: any matching action button if machine visible on page
    if (!bestBtn && machineRe.test(document.body.innerText || "")) {
      const all = [...document.querySelectorAll("button, a, [role='button']")].filter(visible);
      bestBtn = all.find((b) => actionRe.test(textOf(b) + " " + (b.getAttribute("aria-label") || ""))) || null;
      context = "global_fallback";
    }

    if (!bestBtn) {
      return { clicked: false, reason: "no_matching_control", machineVisible: machineRe.test(document.body.innerText || "") };
    }
    bestBtn.scrollIntoView({ block: "center", inline: "center" });
    bestBtn.click();
    return {
      clicked: true,
      text: textOf(bestBtn).slice(0, 80),
      tag: bestBtn.tagName,
      context,
    };
  })()`;
}

async function waitStatus(send, wantRunning, timeoutSec) {
  const deadline = Date.now() + timeoutSec * 1000;
  while (Date.now() < deadline) {
    const st = await evalInPage(
      send,
      `(() => {
        const t = document.body?.innerText || "";
        return {
          running: /running|运行中|使用中/i.test(t) && /NEXUS-GPU-test1|2fc615/i.test(t),
          stopped: /stopped|suspended|已停止|已挂起/i.test(t) && /NEXUS-GPU-test1|2fc615/i.test(t),
          snippet: t.match(/.{0,40}NEXUS-GPU-test1.{0,80}/)?.[0] || t.slice(0, 200),
        };
      })()`,
    );
    if (wantRunning && st.running) return { ok: true, ...st };
    if (!wantRunning && st.stopped) return { ok: true, ...st };
    await sleep(4000);
  }
  return { ok: false, timeout: true };
}

async function trySmoke(send) {
  // Best-effort: open terminal shortcut and type via Input.insertText
  await send("Input.dispatchKeyEvent", {
    type: "keyDown",
    modifiers: 2, // ctrl
    windowsVirtualKeyCode: 192,
    code: "Backquote",
    key: "`",
  }).catch(() => {});
  await send("Input.dispatchKeyEvent", {
    type: "keyUp",
    modifiers: 2,
    windowsVirtualKeyCode: 192,
    code: "Backquote",
    key: "`",
  }).catch(() => {});
  await sleep(1200);

  // Clipboard path via evaluate
  const injected = await evalInPage(
    send,
    `(() => {
      const cmd = ${JSON.stringify(SMOKE_CMD)};
      const ta = document.querySelector("textarea.xterm-helper-textarea, .xterm-helper-textarea, textarea");
      if (ta) {
        ta.focus();
        return { mode: "textarea_focus", hasTerminal: true };
      }
      // code-server / vscode
      const term = document.querySelector(".xterm, .terminal, [class*='terminal']");
      return { mode: term ? "xterm_present" : "no_terminal", hasTerminal: !!term, cmdReady: cmd.slice(0, 80) };
    })()`,
  );

  if (injected?.hasTerminal) {
    // Type command slowly via insertText
    await send("Input.insertText", { text: SMOKE_CMD }).catch(() => {});
    await sleep(300);
    await send("Input.dispatchKeyEvent", {
      type: "keyDown",
      windowsVirtualKeyCode: 13,
      code: "Enter",
      key: "Enter",
      text: "\r",
    }).catch(() => {});
    await send("Input.dispatchKeyEvent", {
      type: "keyUp",
      windowsVirtualKeyCode: 13,
      code: "Enter",
      key: "Enter",
    }).catch(() => {});
    return { status: "SMOKE_TYPED", ...injected, cmd: SMOKE_CMD };
  }

  // Put command on page dataset for operator / copy
  await evalInPage(
    send,
    `(() => {
      window.__NEXUS_SMOKE_CMD = ${JSON.stringify(SMOKE_CMD)};
      try { navigator.clipboard.writeText(window.__NEXUS_SMOKE_CMD); } catch(e) {}
      return true;
    })()`,
  ).catch(() => {});

  return {
    status: "SMOKE_MANUAL",
    note: "Terminal not automatable; smoke command in clipboard / window.__NEXUS_SMOKE_CMD",
    cmd: SMOKE_CMD,
    ...injected,
  };
}

function appendContinuity(row) {
  const ledger = path.join(outDir, "NEXUScontinuity_runs.jsonl");
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    agent: "intern_workbench_cdp",
    ...row,
  });
  try {
    fs.appendFileSync(ledger, line + "\n", "utf8");
  } catch (e) {
    return { ledgerError: String(e) };
  }
  return { ledgerOk: true };
}

async function main() {
  const report = {
    port,
    phase,
    machine,
    machineIdHint,
    started_at: new Date().toISOString(),
    levels: { L0: false, L1: false, L2: false, L3: false },
  };

  let pages = await listPages();
  let tab = pickInternTab(pages);

  // If no intern tab, open workbench via first page navigate is safer than createTarget denylist —
  // use new tab only if zero intern hosts (operator multi-lane already has intern often)
  if (!tab) {
    // Prefer navigate an existing about:blank or last page — avoid createTarget
    const blank = pages.find((p) => p.url === "about:blank" || p.url.startsWith("chrome://"));
    tab = blank || pages[0];
    if (!tab) {
      console.log(JSON.stringify({ status: "NO_CDP_PAGES", port }, null, 2));
      process.exit(2);
    }
    report.openedVia = "reuse_non_intern_tab";
  } else {
    report.openedVia = "existing_intern_tab";
  }

  await activate(tab.id);
  // refresh target after activate (ws url stable usually)
  pages = await listPages();
  tab = pages.find((p) => p.id === tab.id) || pickInternTab(pages) || tab;

  const ws = await connectWs(tab.webSocketDebuggerUrl);
  const send = makeSend(ws);
  await send("Runtime.enable");
  await send("Page.enable").catch(() => {});
  await send("Page.bringToFront").catch(() => {});

  const needWorkbenchList =
    phase === "map" ||
    phase === "start" ||
    phase === "stop" ||
    phase === "all" ||
    phase === "enter";

  if (needWorkbenchList) {
    const cur = await evalInPage(send, "location.href");
    if (!/d\.intern-ai\.org\.cn\/workbench/i.test(cur) || /dataset\/create|create$/i.test(cur)) {
      await navigate(send, WORKBENCH_LIST);
      report.navigatedTo = WORKBENCH_LIST;
    } else {
      // soft reload to wake SPA
      await send("Page.reload", { ignoreCache: false }).catch(() => {});
      await settle(send, 12000);
      report.reloaded = true;
    }
  }

  report.bodyLenAfterNav = await settle(send, 10000);

  // MAP
  let map = await evalInPage(send, MAP_EXPR);
  // If empty, try common workbench subpaths
  if (!map?.bodySnippet && !map?.interesting?.length) {
    for (const sub of [
      "https://d.intern-ai.org.cn/workbench/dev-machine",
      "https://d.intern-ai.org.cn/workbench/dev-machine/list",
      "https://d.intern-ai.org.cn/workbench",
    ]) {
      await navigate(send, sub);
      await settle(send, 8000);
      map = await evalInPage(send, MAP_EXPR);
      report.triedSub = sub;
      if (map?.bodySnippet || map?.interesting?.length) break;
    }
  }
  report.map = map;
  report.levels.L0 = true;
  const mapPath = path.join(outDir, "intern_workbench_dom_map.json");
  fs.writeFileSync(mapPath, JSON.stringify({ ...report, map }, null, 2), "utf8");
  report.mapPath = mapPath;

  if (map?.statusHints?.login && !map?.hasMachineName) {
    report.status = "AUTH_REQUIRED";
    appendContinuity({ kind: "intern_cdp_map", status: report.status, url: map.url });
    console.log(JSON.stringify(report, null, 2));
    ws.close();
    process.exit(3);
  }

  if (phase === "map") {
    if (map?.machineCount === 0) {
      report.status = "MAP_OK_EMPTY_LIST";
      report.next = "Machine list is empty (共 0 个). Recreate NEXUS-GPU-test1 via UI or --phase create --confirm. Then re-run --phase start.";
    } else {
      report.status = map?.hasMachineName ? "MAP_OK_MACHINE_VISIBLE" : "MAP_OK_MACHINE_NOT_IN_VIEW";
    }
    appendContinuity({
      kind: "intern_cdp_map",
      status: report.status,
      hasMachine: !!map?.hasMachineName,
      machineCount: map?.machineCount,
      points: map?.points,
    });
    console.log(JSON.stringify(report, null, 2));
    ws.close();
    process.exit(map?.hasMachineName ? 0 : map?.machineCount === 0 ? 6 : 1);
  }

  // Empty list guard for start/all
  if ((phase === "start" || phase === "all") && map?.machineCount === 0) {
    report.status = "NO_MACHINES_RECREATE_REQUIRED";
    report.next =
      "Workbench shows 共 0 个. NEXUS-GPU-test1 is not present (released/expired). Operator or --phase create --confirm required.";
    appendContinuity({ kind: "intern_cdp_start", status: report.status, points: map?.points });
    console.log(JSON.stringify(report, null, 2));
    ws.close();
    process.exit(6);
  }

  // CREATE (gated) — navigates form only unless --confirm
  if (phase === "create") {
    const confirm = process.argv.includes("--confirm");
    await navigate(send, "https://d.intern-ai.org.cn/workbench/dev-machine/create");
    await settle(send, 12000);
    const formMap = await evalInPage(send, MAP_EXPR);
    report.createForm = formMap;
    if (!confirm) {
      report.status = "CREATE_FORM_MAPPED_NO_SUBMIT";
      report.note = "Refusing to spend points without --confirm. Review create form map, then re-run with --confirm.";
      appendContinuity({ kind: "intern_cdp_create", status: report.status });
      console.log(JSON.stringify(report, null, 2));
      ws.close();
      process.exit(0);
    }
    // Fill name best-effort
    await evalInPage(
      send,
      `(() => {
        const name = ${JSON.stringify(machine)};
        const inputs = [...document.querySelectorAll("input")].filter((el) => {
          const r = el.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        });
        const target = inputs.find((i) => /name|名称|machine/i.test(i.placeholder || i.name || i.id || "")) || inputs[0];
        if (!target) return { filled: false };
        target.focus();
        target.value = name;
        target.dispatchEvent(new Event("input", { bubbles: true }));
        target.dispatchEvent(new Event("change", { bubbles: true }));
        return { filled: true, placeholder: target.placeholder };
      })()`,
    );
    // Select A100-1 if radio/card visible
    await evalInPage(
      send,
      `(() => {
        const nodes = [...document.querySelectorAll("div, label, tr, button, span")];
        const hit = nodes.find((el) => /A100-1-80G|A100 \\* 1|Nvidia A100 \\* 1/i.test(el.innerText || ""));
        if (hit) { hit.click(); return { selected: (hit.innerText || "").slice(0, 80) }; }
        return { selected: null };
      })()`,
    );
    // Submit create
    const submitted = await evalInPage(
      send,
      `(() => {
        const btns = [...document.querySelectorAll("button")];
        const b = btns.find((x) => /创建|确认|submit|create|确定/i.test((x.innerText || "") + (x.getAttribute("aria-label") || "")));
        if (!b) return { submitted: false };
        b.click();
        return { submitted: true, text: (b.innerText || "").slice(0, 40) };
      })()`,
    );
    report.createSubmit = submitted;
    report.status = submitted?.submitted ? "CREATE_SUBMITTED" : "CREATE_SUBMIT_NOT_FOUND";
    appendContinuity({ kind: "intern_cdp_create", status: report.status, submitted });
    console.log(JSON.stringify(report, null, 2));
    ws.close();
    process.exit(submitted?.submitted ? 0 : 7);
  }

  // START
  if (phase === "start" || phase === "all") {
    const clickStart = await evalInPage(
      send,
      clickExpr(machine, machineIdHint, "/start\\s*up|start|启动|开机/i"),
    );
    report.startClick = clickStart;
    if (!clickStart?.clicked) {
      // try navigating list again / search
      await navigate(send, WORKBENCH_LIST);
      await sleep(2000);
      const retry = await evalInPage(
        send,
        clickExpr(machine, machineIdHint, "/start\\s*up|start|启动|开机/i"),
      );
      report.startClickRetry = retry;
      if (!retry?.clicked) {
        report.status = "START_CONTROL_NOT_FOUND";
        appendContinuity({ kind: "intern_cdp_start", status: report.status, mapHints: map?.interesting?.slice(0, 15) });
        console.log(JSON.stringify(report, null, 2));
        ws.close();
        process.exit(4);
      }
    }
    const waited = await waitStatus(send, true, waitSec);
    report.startWait = waited;
    report.levels.L1 = !!waited.ok;
    appendContinuity({ kind: "intern_cdp_start", status: waited.ok ? "RUNNING" : "START_TIMEOUT", waited });
    if (!waited.ok && phase === "start") {
      report.status = "START_TIMEOUT";
      console.log(JSON.stringify(report, null, 2));
      ws.close();
      process.exit(5);
    }
  }

  // ENTER
  if (phase === "enter" || phase === "all") {
    const clickEnter = await evalInPage(
      send,
      clickExpr(machine, machineIdHint, "/enter|open|进入|打开|进入开发机/i"),
    );
    report.enterClick = clickEnter;
    await sleep(5000);
    const ide = await evalInPage(
      send,
      `(() => {
        const t = document.body?.innerText || "";
        const hasIde = !!(document.querySelector(".monaco-workbench, .xterm, [class*='activitybar'], .monaco-editor"));
        return { url: location.href, title: document.title, hasIde, snippet: t.slice(0, 300) };
      })()`,
    );
    report.ide = ide;
    report.levels.L2 = !!ide?.hasIde || /code|vscode|jupyter|terminal/i.test(ide?.title || "");
    appendContinuity({ kind: "intern_cdp_enter", status: report.levels.L2 ? "IDE" : "ENTER_UNCLEAR", ide });
  }

  // SMOKE
  if (phase === "smoke" || phase === "all") {
    if (!report.levels.L2 && phase === "all") {
      // try enter first if not done
      const clickEnter = await evalInPage(
        send,
        clickExpr(machine, machineIdHint, "/enter|open|进入|打开/i"),
      );
      report.enterClickLate = clickEnter;
      await sleep(4000);
    }
    const smoke = await trySmoke(send);
    report.smoke = smoke;
    report.levels.L3 = smoke.status === "SMOKE_TYPED";
    appendContinuity({ kind: "intern_cdp_smoke", status: smoke.status, cmd: SMOKE_CMD.slice(0, 200) });
  }

  // STOP
  if (phase === "stop") {
    await navigate(send, WORKBENCH_LIST);
    await sleep(2000);
    const clickStop = await evalInPage(
      send,
      clickExpr(machine, machineIdHint, "/stop|停止|关机|shutdown/i"),
    );
    report.stopClick = clickStop;
    const waited = await waitStatus(send, false, Math.min(waitSec, 120));
    report.stopWait = waited;
    appendContinuity({ kind: "intern_cdp_stop", status: waited.ok ? "STOPPED" : "STOP_UNCLEAR" });
  }

  report.status =
    phase === "all"
      ? report.levels.L1
        ? report.levels.L3
          ? "ALL_L3_SMOKE_TYPED"
          : report.levels.L2
            ? "ALL_L2_IDE"
            : "ALL_L1_RUNNING"
        : "ALL_PARTIAL"
      : "OK";
  report.finished_at = new Date().toISOString();

  const outPath = path.join(outDir, `intern_workbench_${phase}_result.json`);
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2), "utf8");
  report.outPath = outPath;
  console.log(JSON.stringify(report, null, 2));
  ws.close();

  const ok =
    phase === "map"
      ? report.map?.hasMachineName
      : phase === "start"
        ? report.levels.L1
        : phase === "all"
          ? report.levels.L1
          : true;
  process.exit(ok ? 0 : 1);
}

main().catch((e) => {
  console.log(JSON.stringify({ status: "FATAL", error: String(e?.message || e) }, null, 2));
  process.exit(9);
});
