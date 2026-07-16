/**
 * screenshot_lane.mjs — Capture a screenshot of a specific CDP lane tab.
 * 
 * Usage:
 *   node tools/browser_ai_supervisor/screenshot_lane.mjs --port 9224 --required grok.com
 *   node tools/browser_ai_supervisor/screenshot_lane.mjs --port 9224 --required deepseek.com --output C:\screenshots\deepseek.png
 * 
 * Output:
 *   Saves PNG to scratch/screenshots/<host>_<timestamp>.png
 *   Prints JSON: {"path": "...", "width": N, "height": N, "timestamp": "..."}
 */

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "..", "..");
const SCRATCH = path.join(REPO, "scratch", "screenshots");
fs.mkdirSync(SCRATCH, { recursive: true });

// Parse args
const args = process.argv.slice(2);
let port = 9224;
let required = "";
let output = "";

for (let i = 0; i < args.length; i++) {
  if (args[i] === "--port" && args[i + 1]) port = parseInt(args[++i]);
  if (args[i] === "--required" && args[i + 1]) required = args[++i].toLowerCase();
  if (args[i] === "--output" && args[i + 1]) output = args[++i];
}

if (!required) {
  console.error("Usage: node screenshot_lane.mjs --port 9224 --required <host> [--output <path>]");
  process.exit(1);
}

// Get CDP targets
async function getTargets() {
  return new Promise((resolve, reject) => {
    http.get(`http://127.0.0.1:${port}/json/list`, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error("invalid JSON from CDP")); }
      });
    }).on("error", reject);
  });
}

// Screenshot via CDP
async function screenshot(wsUrl) {
  // Dynamic import for ws if available, otherwise use built-in
  let WS;
  try {
    WS = (await import("ws")).default;
  } catch {
    // Built-in WebSocket (Node 22+)
    WS = globalThis.WebSocket;
  }

  return new Promise((resolve, reject) => {
    const ws = new WS(wsUrl);
    
    const setupHandler = (eventName, handler) => {
      if (typeof ws.on === "function") {
        ws.on(eventName, handler);
      } else {
        ws[`on${eventName}`] = (event) => {
          const data = event.data !== undefined ? event.data : event;
          handler(data);
        };
      }
    };

    setupHandler("open", () => {
      // Bring tab to front first so Chrome renders it
      ws.send(JSON.stringify({
        id: 1,
        method: "Page.bringToFront"
      }));
    });

    setupHandler("message", (raw) => {
      try {
        const msg = JSON.parse(raw.toString());
        if (msg.id === 1) {
          // Capture screenshot now that tab is active
          ws.send(JSON.stringify({
            id: 2,
            method: "Page.captureScreenshot",
            params: { format: "png", fromSurface: true },
          }));
        } else if (msg.id === 2) {
          if (typeof ws.close === "function") ws.close();
          if (msg.result && msg.result.data) {
            resolve(Buffer.from(msg.result.data, "base64"));
          } else {
            reject(new Error("no screenshot data"));
          }
        }
      } catch (e) {
        reject(e);
      }
    });

    if (typeof ws.on === "function") {
      ws.on("error", reject);
    } else {
      ws.onerror = reject;
    }

    setTimeout(() => { 
      if (typeof ws.close === "function") ws.close(); 
      reject(new Error("screenshot timeout")); 
    }, 30000);
  });
}

async function main() {
  const targets = await getTargets();
  const page = targets.find(
    (t) => t.type === "page" && t.url.toLowerCase().includes(required)
  );

  if (!page) {
    console.error(`No tab found matching "${required}"`);
    process.exit(2);
  }

  const img = await screenshot(page.webSocketDebuggerUrl);
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = output || path.join(SCRATCH, `${required.replace(/\./g, "_")}_${ts}.png`);
  fs.writeFileSync(filename, img);

  console.log(JSON.stringify({
    path: filename,
    width: 0,  // PNG parse omitted for brevity
    height: 0,
    timestamp: ts,
    url: page.url,
    title: page.title,
  }));
}

main().catch((e) => {
  console.error("ERROR:", e.message);
  process.exit(3);
});
