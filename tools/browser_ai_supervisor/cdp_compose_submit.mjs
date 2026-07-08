/** Zo/Grok composer: Shift+Enter = newline, Enter = send (no Send button). */
const SHIFT = 8;

export async function dispatchEnter(cdp, modifiers = 0) {
  const enter = {
    key: "Enter",
    code: "Enter",
    windowsVirtualKeyCode: 13,
    nativeVirtualKeyCode: 13,
  };
  const mod = modifiers ? { modifiers } : {};
  await cdp.send("Input.dispatchKeyEvent", { type: "rawKeyDown", ...enter, ...mod });
  await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", ...enter, ...mod });
  await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", ...enter, ...mod });
}

export async function dispatchShiftEnter(cdp) {
  await dispatchEnter(cdp, SHIFT);
}

/** Insert multiline prompt: newline chars become Shift+Enter, not literal \\n in one blob. */
export async function insertPromptText(cdp, text) {
  const lines = text.split(/\n/);
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i].length > 0) {
      await cdp.send("Input.insertText", { text: lines[i] });
    }
    if (i < lines.length - 1) {
      await dispatchShiftEnter(cdp);
    }
  }
}

export async function clearComposerShortcut(cdp) {
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyDown",
    key: "a",
    code: "KeyA",
    windowsVirtualKeyCode: 65,
    modifiers: 2,
  });
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyUp",
    key: "a",
    code: "KeyA",
    windowsVirtualKeyCode: 65,
    modifiers: 2,
  });
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyDown",
    key: "Backspace",
    code: "Backspace",
    windowsVirtualKeyCode: 8,
  });
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyUp",
    key: "Backspace",
    code: "Backspace",
    windowsVirtualKeyCode: 8,
  });
}

export async function submitPromptWithEnter(cdp, text) {
  await insertPromptText(cdp, text);
  await new Promise((resolve) => setTimeout(resolve, 400));
  await dispatchEnter(cdp, 0);
  const lineCount = text.split(/\n/).length;
  return { ok: true, method: "enter", lineCount, textLen: text.length };
}