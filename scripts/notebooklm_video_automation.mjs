#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);
const promptText = args.promptFile ? fs.readFileSync(args.promptFile, "utf8").trim() : (args.prompt ?? "").trim();
const dryRun = Boolean(args.dryRun);

if (!promptText && !dryRun) {
  console.error("Error: --prompt or --promptFile is required unless running in --dryRun mode.");
  process.exit(1);
}

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

class Cdp {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
  }
  async open() {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP open timeout")), 10000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", () => {
        clearTimeout(timer);
        reject(new Error("CDP websocket connection error"));
      }, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    });
  }
  send(method, params = {}) {
    const id = this.nextId++;
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP call timeout: ${method}`));
        }
      }, 60000);
    });
    this.ws.send(JSON.stringify({ id, method, params }));
    return promise;
  }
  close() {
    this.ws.close();
  }
}

async function run() {
  console.log(`Connecting to Chrome on port ${port}...`);
  const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
  let tab = list.find((t) => t.type === "page" && t.url && t.url.includes("notebooklm.google.com"));

  if (tab) {
    console.log(`Found existing NotebookLM tab: ID ${tab.id}, Title: "${tab.title}"`);
  } else {
    console.log("No NotebookLM tab found. Opening a new tab...");
    const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
    const browserCdp = new Cdp(ver.webSocketDebuggerUrl);
    await browserCdp.open();
    const createRes = await browserCdp.send("Target.createTarget", {
      url: "https://notebooklm.google.com/notebook/b4c00b6e-6d93-435b-86f7-a8ab0676d596?pli=1"
    });
    console.log("Created target:", createRes);
    browserCdp.close();

    // Wait for the new tab to appear in the list
    await new Promise((r) => setTimeout(r, 4000));
    const newList = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
    tab = newList.find((t) => t.id === createRes.targetId);
  }

  if (!tab) {
    console.error("Error: Failed to find or create NotebookLM tab.");
    process.exit(1);
  }

  // Activate target via browser CDP session
  try {
    const ver = await fetch(`http://127.0.0.1:${port}/json/version`).then((r) => r.json());
    const browserCdp = new Cdp(ver.webSocketDebuggerUrl);
    await browserCdp.open();
    await browserCdp.send("Target.activateTarget", { targetId: tab.id });
    browserCdp.close();
    console.log("NotebookLM tab focused and activated.");
  } catch (e) {
    console.warn("Warning: Could not activate target window:", e.message);
  }

  const tabCdp = new Cdp(tab.webSocketDebuggerUrl);
  await tabCdp.open();
  await tabCdp.send("Page.enable");
  await tabCdp.send("Runtime.enable");
  await tabCdp.send("Page.setDownloadBehavior", {
    behavior: "allow",
    downloadPath: "C:\\Users\\speci.000\\Downloads"
  });

  console.log("Waiting for page stability (5s)...");
  await new Promise((r) => setTimeout(r, 5000));

  // Step 1: Click the Studio tab
  console.log("Navigating to Studio tab...");
  const studioClick = await tabCdp.send("Runtime.evaluate", {
    expression: `(() => {
      const tabs = [...document.querySelectorAll(".mdc-tab, button, span, div")];
      const studioTab = tabs.find(el => el.textContent.trim() === "Studio");
      if (!studioTab) return { ok: false, reason: "STUDIO_TAB_NOT_FOUND" };
      const clickTarget = studioTab.closest(".mdc-tab") || studioTab;
      clickTarget.click();
      return { ok: true };
    })()`,
    returnByValue: true
  });

  if (!studioClick.result.value || !studioClick.result.value.ok) {
    console.error("Error: Failed to click Studio tab.", studioClick.result.value);
    process.exit(1);
  }
  console.log("Studio tab clicked. Waiting for tab content (3s)...");
  await new Promise((r) => setTimeout(r, 3000));

  if (dryRun) {
    console.log("Dry run check passed. Exiting before triggering dialog.");
    tabCdp.close();
    process.exit(0);
  }

  // Step 2: Open Video Overview Customize dialog
  console.log("Opening Customize Video Overview dialog...");
  const openDialog = await tabCdp.send("Runtime.evaluate", {
    expression: `(() => {
      const cards = [...document.querySelectorAll("basic-create-artifact-button, BASIC-CREATE-ARTIFACT-BUTTON")];
      const videoCard = cards.find(c => c.innerText.includes("Video Overview"));
      if (!videoCard) return { ok: false, reason: "VIDEO_OVERVIEW_CARD_NOT_FOUND" };
      const btn = videoCard.querySelector('.edit-icon, .option-icon');
      if (!btn) return { ok: false, reason: "CUSTOMIZE_BUTTON_NOT_FOUND" };
      btn.click();
      return { ok: true };
    })()`,
    returnByValue: true
  });

  let isAlreadyGenerating = false;
  if (!openDialog.result.value || !openDialog.result.value.ok) {
    console.log("Could not open Customize dialog (perhaps it is already generating?). Checking active progress...");
    // Check if there is an active progress card in Studio panel
    const checkProgress = await tabCdp.send("Runtime.evaluate", {
      expression: `(() => {
        const studio = document.querySelector("STUDIO-PANEL");
        if (!studio) return false;
        const cards = [...studio.querySelectorAll("artifact-library-item, ARTIFACT-LIBRARY-ITEM")];
        return !!cards.find(c => c.innerText.includes("Generating"));
      })()`,
      returnByValue: true
    });
    if (checkProgress.result.value) {
      console.log("Active generation detected in Studio panel! Skipping trigger and proceeding directly to monitoring loop.");
      isAlreadyGenerating = true;
    } else {
      console.error("Error: Failed to open Customize Video Overview dialog and no active generation found.", openDialog.result.value);
      process.exit(1);
    }
  }

  if (!isAlreadyGenerating) {
    console.log("Clicked Video Overview customize button. Waiting for dialog (3s)...");
    await new Promise((r) => setTimeout(r, 3000));

    // Step 3: Select "Short" format, enable Custom topic, and enter prompt
    console.log("Selecting 'Short' format and entering steering prompt...");
    const populateRes = await tabCdp.send("Runtime.evaluate", {
      expression: `(() => {
        // Find the Short mat-radio-button and click its native input
        const shortMBtn = [...document.querySelectorAll("mat-radio-button")].find(btn => btn.innerText.includes("Short"));
        if (!shortMBtn) return { ok: false, reason: "SHORT_MAT_RADIO_BUTTON_NOT_FOUND" };
        const shortInput = shortMBtn.querySelector("input[type='radio']");
        if (!shortInput) return { ok: false, reason: "SHORT_INPUT_NOT_FOUND" };
        shortInput.click();

        // Click the "Custom topic" header button to activate custom prompt mode
        const customTopicBtn = document.querySelector('button[aria-label="Custom topic"]');
        if (customTopicBtn) {
          customTopicBtn.click();
        }

        // Find the custom topic textarea and input the prompt
        const tx = document.querySelector("textarea[aria-label='What should the video focus on?']") || document.querySelector("textarea");
        if (!tx) return { ok: false, reason: "PROMPT_TEXTAREA_NOT_FOUND" };
        
        tx.value = ${JSON.stringify(promptText)};
        tx.dispatchEvent(new Event('input', { bubbles: true }));
        tx.dispatchEvent(new Event('change', { bubbles: true }));

        return { ok: true };
      })()`,
      returnByValue: true
    });

    if (!populateRes.result.value || !populateRes.result.value.ok) {
      console.error("Error: Failed to populate dialog settings.", populateRes.result.value);
      process.exit(1);
    }
    console.log("Short format selected, Custom topic activated, and steering prompt entered.");

    // Step 4: Click Generate inside the dialog
    console.log("Triggering Video Generation...");
    const generateRes = await tabCdp.send("Runtime.evaluate", {
      expression: `(() => {
        const genBtn = [...document.querySelectorAll(".mat-mdc-dialog-actions button, button")].find(b => b.innerText.includes("Generate"));
        if (!genBtn) return { ok: false, reason: "GENERATE_BUTTON_NOT_FOUND" };
        if (genBtn.disabled) return { ok: false, reason: "GENERATE_BUTTON_DISABLED" };
        genBtn.click();
        return { ok: true };
      })()`,
      returnByValue: true
    });

    if (!generateRes.result.value || !generateRes.result.value.ok) {
      console.error("Error: Failed to click Generate button.", generateRes.result.value);
      process.exit(1);
    }
    console.log("Generation started successfully.");
  }

  // Step 5: Progress Monitoring Loop (Studio Panel Curation)
  console.log("Waiting 15 seconds for generation status to register in UI...");
  await new Promise((r) => setTimeout(r, 15000));

  let attempts = 0;
  const maxAttempts = 90; // 15 minutes max
  console.log("Beginning progress monitoring loop...");

  while (attempts < maxAttempts) {
    attempts += 1;
    
    // Ensure Studio tab is open
    const checkGen = await tabCdp.send("Runtime.evaluate", {
      expression: `(() => {
        const studio = document.querySelector("STUDIO-PANEL");
        if (!studio) return { state: "NOT_FOUND" };
        const cards = [...studio.querySelectorAll("artifact-library-item, ARTIFACT-LIBRARY-ITEM")];
        const genCard = cards.find(c => c.innerText.includes("Generating"));
        if (genCard) return { state: "GENERATING" };
        return { state: "DONE" };
      })()`,
      returnByValue: true
    });

    if (checkGen.result.value && checkGen.result.value.state === "DONE") {
      console.log("Generation complete!");
      break;
    }
    console.log(`Polling: Attempt ${attempts}/${maxAttempts}...`);
    await new Promise((r) => setTimeout(r, 10000)); // Poll every 10 seconds
  }

  console.log("Opening player page to download...");
  
  // Open Studio panel again to make sure it's visible
  await tabCdp.send("Runtime.evaluate", {
    expression: `(() => {
      const tabs = [...document.querySelectorAll(".mdc-tab, button, span, div")];
      const studioTab = tabs.find(el => el.textContent.trim() === "Studio");
      if (studioTab) {
        const clickTarget = studioTab.closest(".mdc-tab") || studioTab;
        clickTarget.click();
      }
    })()`
  });
  await new Promise((r) => setTimeout(r, 2000));

  // Click the completed card
  const downloadRes = await tabCdp.send("Runtime.evaluate", {
    expression: `(() => {
      const studio = document.querySelector("STUDIO-PANEL");
      if (!studio) return { ok: false, error: "STUDIO_PANEL_CLOSED" };

      const cards = [...studio.querySelectorAll("artifact-library-item, ARTIFACT-LIBRARY-ITEM")];
      const completedCard = cards.find(c => c.innerText.includes("Short"));
      if (!completedCard) return { ok: false, error: "COMPLETED_CARD_NOT_FOUND" };

      const clickTarget = completedCard.querySelector(".artifact-item-button, .artifact-button-content") || completedCard;
      clickTarget.click();
      return { ok: true };
    })()`,
    returnByValue: true
  });

  console.log("Player page open command output:", downloadRes.result.value);
  console.log("Waiting 5 seconds for player page to load...");
  await new Promise((r) => setTimeout(r, 5000));

  // Click Download button on player page
  const clickDownload = await tabCdp.send("Runtime.evaluate", {
    expression: `(() => {
      const downloadBtn = document.querySelector('button[aria-label*="Download"], [data-testid*="download"], [aria-label*="download"]');
      if (!downloadBtn) return { ok: false, error: "DOWNLOAD_BUTTON_NOT_FOUND" };
      downloadBtn.click();
      return { ok: true };
    })()`,
    returnByValue: true
  });

  console.log("Download action click result:", clickDownload.result.value);
  if (clickDownload.result.value && clickDownload.result.value.ok) {
    console.log("Waiting 15 seconds for download to initialize...");
    await new Promise((r) => setTimeout(r, 15000));
  } else {
    console.error("Error: Download button not found on player page.");
  }

  tabCdp.close();
  console.log("CDP automation finished.");
}

run().catch((err) => {
  console.error("Fatal Error running automation:", err);
  process.exit(1);
});
