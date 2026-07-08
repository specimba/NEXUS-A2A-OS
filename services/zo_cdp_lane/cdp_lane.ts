/**
 * Zo CDP lane — connect to Windows Grok Chrome via tunnel (phase 2).
 * Run on Zo: bun run services/zo_cdp_lane/cdp_lane.ts probe
 */
import { chromium } from "playwright";

const tunnel =
  process.env.NEXUS_ZO_CDP_TUNNEL_URL?.trim() || "http://127.0.0.1:9224";

async function probe(): Promise<void> {
  const browser = await chromium.connectOverCDP(tunnel);
  const contexts = browser.contexts();
  const pages = contexts.flatMap((c) => c.pages());
  const grok = pages.find((p) => /grok/i.test(p.url()));
  const target = grok ?? pages[0];
  if (!target) {
    console.log(JSON.stringify({ status: "NOTIFY_SETUP_REQUIRED", blocker: "no_pages" }));
    process.exit(2);
  }
  const title = await target.title();
  const url = target.url();
  console.log(
    JSON.stringify({
      status: "READY",
      tunnel,
      title,
      url: url.replace(/([?&]token=)[^&]+/gi, "$1[REDACTED]"),
      pageCount: pages.length,
    })
  );
  await browser.close();
}

const cmd = process.argv[2] ?? "probe";
if (cmd === "probe") {
  probe().catch((e) => {
    console.log(JSON.stringify({ status: "error", message: String(e) }));
    process.exit(1);
  });
} else {
  console.error("usage: bun run cdp_lane.ts probe");
  process.exit(1);
}