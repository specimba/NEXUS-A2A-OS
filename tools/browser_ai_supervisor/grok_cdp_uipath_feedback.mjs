#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";

const FORM_HOST = "forms.office.com";
const FORM_TITLE_MARKER = "UiPath AgentHack (2026)";
const EXPECTED_QUESTION_COUNT = 14;
const FILL_CONFIRMATION = "FILL_REVIEW_DRAFT";
const SUBMIT_CONFIRMATION = "SUBMIT_UIPATH_FEEDBACK";
const DEFAULT_FORM_URL = "https://forms.office.com/pages/responsepage.aspx?id=Kj012FOxF02IJ5AsUfcjV2DuA8jhyPdHtqffCeWlM-pUOUJUM1c4RzhLUkJGR0FQVUhSNk1ZQlMzSi4u&route=shorturl";
const args = parseArgs(process.argv.slice(2));
const port = Number(args.port ?? 9224);

function parseArgs(argv) {
  const out = {};
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) out[key] = true;
    else { out[key] = next; index += 1; }
  }
  return out;
}

function print(value, exitCode = 0) {
  console.log(JSON.stringify(value, null, 2));
  process.exitCode = exitCode;
}

function redactUrl(raw) {
  if (!raw) return raw;
  try {
    const url = new URL(raw);
    return `${url.origin}${url.pathname}${url.search ? "?REDACTED" : ""}`;
  } catch { return String(raw).replace(/\?.*$/, "?REDACTED"); }
}

function readAnswers(path) {
  if (!path) throw new Error("--answers is required for --fill");
  const parsed = JSON.parse(fs.readFileSync(path, "utf8"));
  const answers = parsed.answers ?? parsed;
  const missing = Array.from({ length: EXPECTED_QUESTION_COUNT }, (_, i) => String(i + 1))
    .filter((key) => typeof answers[key] !== "string" || !answers[key].trim());
  if (missing.length) throw new Error(`answer file is missing questions: ${missing.join(", ")}`);
  const placeholders = Object.entries(answers).filter(([, value]) => value.startsWith("REPLACE_"));
  if (placeholders.length) throw new Error(`answer file contains placeholders: ${placeholders.map(([key]) => key).join(", ")}`);
  return answers;
}

async function getTargets() {
  const response = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!response.ok) throw new Error(`CDP target list failed: ${response.status}`);
  return response.json();
}

async function openTarget() {
  const formUrl = args.url ?? DEFAULT_FORM_URL;
  const endpoint = `http://127.0.0.1:${port}/json/new?${encodeURIComponent(formUrl)}`;
  const response = await fetch(endpoint, { method: "PUT" });
  if (!response.ok) throw new Error(`CDP tab creation failed: ${response.status}`);
  const opened = await response.json();
  await new Promise((resolve) => setTimeout(resolve, 6000));
  return opened;
}

class Cdp {
  constructor(wsUrl) { this.ws = new WebSocket(wsUrl); this.nextId = 1; this.pending = new Map(); }
  async open() {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP websocket open timeout")), 5000);
      this.ws.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
      this.ws.addEventListener("error", () => { clearTimeout(timer); reject(new Error("CDP websocket error")); }, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject, timer } = this.pending.get(message.id);
      this.pending.delete(message.id);
        clearTimeout(timer);
        if (message.error) reject(new Error(JSON.stringify(message.error))); else resolve(message.result);
    });
  }
  send(method, params = {}) {
    const id = this.nextId++;
    const promise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (!this.pending.has(id)) return;
        this.pending.delete(id);
        reject(new Error(`CDP call timeout: ${method}`));
      }, 15000);
      this.pending.set(id, { resolve, reject, timer });
    });
    this.ws.send(JSON.stringify({ id, method, params }));
    return promise;
  }
  close() { this.ws.close(); }
}

function requireMutationApproval() {
  if (!args.fill) return;
  if (args["confirm-fill"] !== FILL_CONFIRMATION) throw new Error(`--fill requires --confirm-fill ${FILL_CONFIRMATION}`);
  if (args.submit && args["confirm-submit"] !== SUBMIT_CONFIRMATION) throw new Error(`--submit requires --confirm-submit ${SUBMIT_CONFIRMATION}`);
}

async function inspectForm(cdp) {
  const expression = `(() => {
    const titles = [...document.querySelectorAll('[id^="QuestionId_"]')]
      .map((el) => (el.innerText || el.textContent || "").trim()).filter(Boolean);
    const submitVisible = [...document.querySelectorAll('button, [role="button"]')].some((el) => {
      const rect = el.getBoundingClientRect();
      return (el.innerText || el.textContent || "").trim() === "Submit" && rect.width > 0 && rect.height > 0;
    });
    return { title: document.title, host: location.host, readyState: document.readyState,
      questionCount: titles.length, questionMarkers: titles.map((text) => text.slice(0, 80)), submitVisible };
  })()`;
  const result = await cdp.send("Runtime.evaluate", { expression, returnByValue: true });
  return result.result.value;
}

function verifyForm(form) {
  const failures = [];
  if (form.host !== FORM_HOST) failures.push("unexpected_host");
  if (!form.title.includes(FORM_TITLE_MARKER)) failures.push("unexpected_title");
  if (form.questionCount !== EXPECTED_QUESTION_COUNT) failures.push("unexpected_question_count");
  if (!form.submitVisible) failures.push("submit_control_not_visible");
  return failures;
}

async function fillForm(cdp, answers, submit) {
  const expression = `((answers, submit) => {
    const results = [];
    const titles = [...document.querySelectorAll('[id^="QuestionId_"]')];
    const findContainer = (number) => {
      const title = titles.find((el) => { const text = (el.innerText || el.textContent || "").trim(); return text.startsWith(number + ".") || text.startsWith(number + "\\n"); });
      let parent = title;
      while (parent && parent.tagName !== "BODY") {
        if (parent.querySelectorAll('input, textarea, [role="radio"]').length > 0 && parent.querySelectorAll('[id^="QuestionId_"]').length === 1) return parent;
        parent = parent.parentElement;
      }
      return null;
    };
    const setValue = (control, value) => {
      const proto = control.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (!setter) throw new Error("native value setter unavailable");
      setter.call(control, value);
      for (const type of ["input", "change", "blur"]) control.dispatchEvent(new Event(type, { bubbles: true }));
    };
    for (const [number, answer] of Object.entries(answers)) {
      const container = findContainer(Number(number));
      if (!container) { results.push({ question: number, status: "ERROR", reason: "container_not_found" }); continue; }
      const radios = [...container.querySelectorAll('input[type="radio"], [role="radio"]')];
      if (radios.length) {
        const match = radios.find((radio) => {
          const label = radio.getAttribute("aria-labelledby") ? document.getElementById(radio.getAttribute("aria-labelledby")) : null;
          const text = (label?.innerText || radio.getAttribute("aria-label") || radio.parentElement?.innerText || "").trim();
          return text.toLowerCase().includes(answer.toLowerCase());
        });
        if (!match) { results.push({ question: number, status: "ERROR", reason: "option_not_found" }); continue; }
        match.click();
      } else {
        const control = container.querySelector("input, textarea");
        if (!control) { results.push({ question: number, status: "ERROR", reason: "control_not_found" }); continue; }
        setValue(control, answer);
      }
      results.push({ question: number, status: "FILLED" });
    }
    if (submit) {
      const button = [...document.querySelectorAll('button, [role="button"]')]
        .find((el) => (el.innerText || el.textContent || "").trim() === "Submit");
      if (!button) throw new Error("submit button unavailable after fingerprint check");
      button.click();
    }
    return { results, submitted: submit };
  })(${JSON.stringify(answers)}, ${JSON.stringify(submit)})`;
  const result = await cdp.send("Runtime.evaluate", { expression, returnByValue: true });
  return result.result.value;
}

async function main() {
  if (args.help) {
    print({ default: "read-only probe of an already-open feedback form", open: "--open creates the form tab only when none exists",
      fill: `--answers <json> --fill --confirm-fill ${FILL_CONFIRMATION}`,
      submit: `add --submit --confirm-submit ${SUBMIT_CONFIRMATION}`,
      safety: "submission is blocked unless host, title, question count, and submit control match" });
    return;
  }
  requireMutationApproval();
  const answers = args.fill ? readAnswers(args.answers) : null;
  let targets = await getTargets();
  let target = targets.filter((item) => item.type === "page")
    .find((item) => item.url.includes(FORM_HOST) || item.title.includes(FORM_TITLE_MARKER));
  if (!target && args.open) {
    const opened = await openTarget();
    targets = await getTargets();
    target = targets.find((item) => item.id === opened.id) ?? opened;
  }
  if (!target) {
    print({ status: "BLOCKED_SETUP", reason: "no_matching_form_tab", port,
      hint: "Open the survey in the isolated CDP profile or rerun with --open." }, 2);
    return;
  }
  const cdp = new Cdp(target.webSocketDebuggerUrl);
  await cdp.open();
  await cdp.send("Runtime.enable");
  const form = await inspectForm(cdp);
  const fingerprint = crypto.createHash("sha256").update(JSON.stringify(form)).digest("hex");
  const failures = verifyForm(form);
  if (failures.length) {
    cdp.close();
    print({ status: "BLOCKED_FORM_DRIFT", target: { title: target.title, url: redactUrl(target.url) }, fingerprint, failures, form }, 3);
    return;
  }
  if (!args.fill) {
    cdp.close();
    print({ status: "READY_REVIEW", target: { title: target.title, url: redactUrl(target.url) }, fingerprint, form, mutated: false, submitted: false });
    return;
  }
  const outcome = await fillForm(cdp, answers, Boolean(args.submit));
  cdp.close();
  print({ status: args.submit ? "SUBMIT_ATTEMPTED" : "DRAFT_FILLED", target: { title: target.title, url: redactUrl(target.url) }, fingerprint,
    answersHash: crypto.createHash("sha256").update(JSON.stringify(answers)).digest("hex"), outcome });
}

main().catch((error) => print({ status: "ERROR", error: error.message }, 1));
