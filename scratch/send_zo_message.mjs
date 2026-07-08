import fs from "node:fs";

class Cdp {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
  }

  async open() {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP open timeout")), 5000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", (e) => {
        clearTimeout(timer);
        reject(e);
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
    const payload = JSON.stringify({ id, method, params });
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP call timeout: ${method}`));
        }
      }, 10000);
    });
    this.ws.send(payload);
    return promise;
  }

  close() {
    this.ws.close();
  }
}

async function run() {
  const promptFile = "C:\\Users\\speci.000\\Documents\\NEXUS\\scratch\\zo_judge_collab_v1.txt";
  const promptText = fs.readFileSync(promptFile, "utf8");

  const list = await fetch('http://127.0.0.1:9224/json/list').then(r => r.json());
  const zo = list.find(t => t.title.includes('Zo') || t.url.includes('zo.computer'));
  if (!zo) {
    console.error('Zo not found');
    return;
  }

  console.log('Connecting to Zo tab CDP...');
  const cdp = new Cdp(zo.webSocketDebuggerUrl);
  await cdp.open();
  await cdp.send("Runtime.enable");

  // Focus the correct input field (the last focused or visible contenteditable ProseMirror)
  console.log('Finding and focusing input...');
  const focusExpr = `(() => {
    const inputs = [...document.querySelectorAll("div[contenteditable='true']")];
    if (!inputs.length) return null;
    // Find the one that has ProseMirror-focused, or default to the last one
    const target = inputs.find(el => el.classList.contains("ProseMirror-focused")) || inputs[inputs.length - 1];
    target.focus();
    // Clear it
    target.textContent = "";
    const r = target.getBoundingClientRect();
    return {
      x: r.left + r.width / 2,
      y: r.top + r.height / 2
    };
  })()`;
  
  const focusRes = await cdp.send("Runtime.evaluate", { expression: focusExpr, returnByValue: true });
  const rect = focusRes.result.value;
  if (!rect) {
    console.error("Failed to find or focus input field");
    cdp.close();
    return;
  }

  // Simulate mouse click on the input field coordinates to ensure focus is registered by Chrome
  await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });

  // Clear any existing text using keyboard shortcuts
  console.log("Clearing input box...");
  await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 2 });
  await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 2 });
  await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });
  await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });

  // Type the text line by line using Shift+Enter for newlines
  console.log("Typing prompt...");
  const lines = promptText.split(/\n/);
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].length > 0) {
      await cdp.send("Input.insertText", { text: lines[i] });
    }
    if (i < lines.length - 1) {
      // Shift+Enter
      await cdp.send("Input.dispatchKeyEvent", { type: "rawKeyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, modifiers: 8 });
      await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, modifiers: 8 });
      await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, modifiers: 8 });
    }
  }

  // Brief pause
  await new Promise(r => setTimeout(r, 500));

  // Click the Send button via JavaScript
  console.log("Clicking Send button...");
  const clickRes = await cdp.send("Runtime.evaluate", {
    expression: `(() => {
      // Find the currently focused ProseMirror input field
      const activeInput = document.querySelector("div[contenteditable='true'].ProseMirror-focused") 
        || document.activeElement 
        || document.querySelector("div[contenteditable='true']");
      if (!activeInput) return "No input element found";
      
      // Traverse up to find the composer shell container
      const container = activeInput.closest(".composer-shell, form, div.relative");
      if (container) {
        const btn = container.querySelector("button[aria-label='Send message']");
        if (btn) {
          btn.click();
          return "Clicked Send message button inside composer container";
        }
      }
      
      // Fallback: Click all visible Send buttons
      const buttons = [...document.querySelectorAll("button[aria-label='Send message'], button")];
      const sendBtns = buttons.filter(b => b.getAttribute("aria-label") === "Send message" || b.textContent.trim() === "Send");
      if (sendBtns.length > 0) {
        sendBtns.forEach(btn => btn.click());
        return "Clicked all " + sendBtns.length + " Send buttons";
      }
      return "No send buttons found";
    })()`,
    returnByValue: true
  });
  
  console.log("Click result:", clickRes.result.value);
  cdp.close();
}

run().catch(console.error);
