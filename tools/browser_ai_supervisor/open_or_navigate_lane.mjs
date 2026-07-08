#!/usr/bin/env node
/**
 * Navigate registry lanes to canonical sessions — reuse tabs, never spawn landing/new-chat pages.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../..");
const REGISTRY = path.join(REPO, "nexus_os/nexusclaw/browser_lane_registry.json");

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) out[key] = true;
    else {
      out[key] = next;
      i += 1;
    }
  }
  return out;
}

const ENV_MAP = {
  grok: ["NEXUS_GROK_PROJECT_CHAT_URL", "NEXUS_GROK_PROJECT_URL"],
  zo: ["NEXUS_ZO_CHAT_URL"],
  chatgpt_gpt55: ["NEXUS_CHATGPT_CHAT_URL", "NEXUS_OPENAI_CHAT_URL"],
  meta_muse_spark: ["NEXUS_META_MUSE_URL"],
  mimo_chat: ["NEXUS_MIMO_CHAT_URL"],
  mimo_claw: ["NEXUS_MIMO_CLAW_URL"],
  qwen_webdev: ["NEXUS_QWEN_WEBDEV_URL"],
  qwen_deep_research: ["NEXUS_QWEN_DEEP_RESEARCH_URL"],
  glm_5_2: ["NEXUS_GLM_CHAT_URL", "NEXUS_Z_AI_CHAT_URL"],
  deepseek_expert: ["NEXUS_DEEPSEEK_CHAT_URL"],
  gemini_app: ["NEXUS_GEMINI_APP_URL", "NEXUS_GEMINI_NOTEBOOK_URL"],
  mistral_work: ["NEXUS_MISTRAL_PROJECT_URL"],
  minimax_agent: ["NEXUS_MINIMAX_CHAT_URL"],
  alphaxiv_assistant: ["NEXUS_ALPHAXIV_URL"],
  gmicloud_playground: ["NEXUS_GMICLOUD_PLAYGROUND_URL"],
  gmicloud_hub: ["NEXUS_GMICLOUD_HUB_URL"],
  apodex_discover: ["NEXUS_APODEX_URL"],
};

function laneUrl(lane) {
  for (const key of ENV_MAP[lane.id] || []) {
    const v = (process.env[key] || "").trim();
    if (v) return v;
  }
  return lane.canonical_url;
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function pageHost(url) {
  return hostOf(url);
}

function hostMatches(pageUrl, lane) {
  const h = pageHost(pageUrl);
  const want = (lane.host || lane.required_probe || "").replace(/^www\./, "");
  return h === want || h.endsWith(`.${want}`) || h.includes(want.split(".")[0]);
}

function hasKey(pageUrl, key) {
  if (!key || /tbd|home$/i.test(key)) return false;
  return pageUrl.includes(key);
}

function isDisposableTab(url) {
  if (!url) return true;
  const u = url.trim();
  return (
    u === "about:blank" ||
    u.startsWith("chrome://newtab") ||
    u === "https://chatgpt.com/" ||
    u === "https://chatgpt.com" ||
    u === "https://grok.com/" ||
    u === "https://chat.qwen.ai/" ||
    u === "https://aistudio.xiaomimimo.com/#/" ||
    u === "https://aistudio.xiaomimimo.com/"
  );
}

class Cdp {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
  }
  async open() {
    await new Promise((res, rej) => {
      this.ws.addEventListener("open", res, { once: true });
      this.ws.addEventListener("error", rej, { once: true });
    });
    this.ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    });
  }
  send(method, params = {}) {
    const my = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(my, { resolve, reject });
      this.ws.send(JSON.stringify({ id: my, method, params }));
    });
  }
  close() {
    this.ws.close();
  }
}

async function navigateTab(page, url) {
  const tab = new Cdp(page.webSocketDebuggerUrl);
  await tab.open();
  await tab.send("Page.navigate", { url });
  tab.close();
}

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const laneId = args.lane;
const all = Boolean(args.all);

const registry = JSON.parse(fs.readFileSync(REGISTRY, "utf8"));
let lanes = all
  ? [...registry.lanes].sort((a, b) => (a.priority || 9) - (b.priority || 9))
  : registry.lanes.filter((l) => l.id === laneId);
if (!lanes.length) {
  console.log(JSON.stringify({ status: "LANE_NOT_FOUND", laneId }));
  process.exit(2);
}

let list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
const browser = new Cdp(ver.webSocketDebuggerUrl);
await browser.open();

const claimed = new Set();
const results = [];

for (const lane of lanes) {
  const targetUrl = laneUrl(lane);
  const pages = list.filter((t) => t.type === "page" && hostMatches(t.url, lane));

  const exact = pages.find((p) => !claimed.has(p.id) && hasKey(p.url, lane.conversation_key));
  if (exact) {
    claimed.add(exact.id);
    if (exact.url === targetUrl || exact.url.split("#")[0] === targetUrl.split("#")[0]) {
      results.push({ lane: lane.id, status: "LANE_OK", url: exact.url, tabId: exact.id });
      continue;
    }
    await navigateTab(exact, targetUrl);
    results.push({ lane: lane.id, status: "NAVIGATED", url: targetUrl, tabId: exact.id });
    continue;
  }

  if (lane.no_duplicate_tab && pages.length >= 1) {
    const pick = pages.find((p) => !claimed.has(p.id)) || pages[0];
    claimed.add(pick.id);
    if (!hasKey(pick.url, lane.conversation_key)) {
      await navigateTab(pick, targetUrl);
      results.push({ lane: lane.id, status: "GROK_NAVIGATED", url: targetUrl, tabId: pick.id });
    } else {
      results.push({ lane: lane.id, status: "GROK_TAB_EXISTS", url: pick.url, tabId: pick.id });
    }
    continue;
  }

  const reusable = pages.find((p) => !claimed.has(p.id) && isDisposableTab(p.url));
  if (reusable) {
    claimed.add(reusable.id);
    await navigateTab(reusable, targetUrl);
    results.push({ lane: lane.id, status: "REUSED_BLANK_TAB", url: targetUrl, tabId: reusable.id });
    continue;
  }

  const spare = pages.find((p) => !claimed.has(p.id));
  if (spare && pages.length === 1) {
    claimed.add(spare.id);
    await navigateTab(spare, targetUrl);
    results.push({ lane: lane.id, status: "NAVIGATED_SINGLE_HOST_TAB", url: targetUrl, tabId: spare.id });
    continue;
  }

  const unclaimed = pages.filter((p) => !claimed.has(p.id));
  if (unclaimed.length === 0) {
    await browser.send("Target.createTarget", { url: targetUrl, background: true });
    results.push({ lane: lane.id, status: "OPENED_TAB_BACKGROUND", url: targetUrl });
    list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
    continue;
  }

  const pick = unclaimed[0];
  claimed.add(pick.id);
  await navigateTab(pick, targetUrl);
  results.push({ lane: lane.id, status: "NAVIGATED_CLAIMED", url: targetUrl, tabId: pick.id });
}

browser.close();
console.log(JSON.stringify({ status: "LANE_REGISTRY_DONE", port, results }, null, 2));