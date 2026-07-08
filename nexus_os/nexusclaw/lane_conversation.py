"""Grok vs Zo CDP conversation pacing (Hermes operator hints)."""

from __future__ import annotations

GROK_LANE = "grok.com"
ZO_LANE = "zo.computer"

# Grok: short nudges, multi-turn same session
CHATGPT_LANE = "chatgpt.com"

GROK_NUDGE_PROMPTS: dict[str, str] = {
    "continue": "tools/browser_ai_supervisor/prompts/grok/nudge_continue.md",
    "proceed": "tools/browser_ai_supervisor/prompts/grok/nudge_proceed.md",
    "goon": "tools/browser_ai_supervisor/prompts/grok/nudge_go_on.md",
    "2": "tools/browser_ai_supervisor/prompts/grok/nudge_pick_2.md",
    "B": "tools/browser_ai_supervisor/prompts/grok/nudge_pick_B.md",
}

CHATGPT_NUDGE_PROMPTS: dict[str, str] = {
    "continue": "tools/browser_ai_supervisor/prompts/chatgpt/nudge_continue.md",
}

# ChatGPT: senior reviewer — 2-4 turns, not Zo-long
CHATGPT_POST_SEND_PAUSE_SEC = 8
ZO_DEFAULT_IDLE_WAIT_SEC = 900
GROK_POST_SEND_PAUSE_SEC = 3

GROK_THINKING_MARKERS: tuple[str, ...] = ()  # Grok rarely blocks on long think
ZO_THINKING_MARKERS: tuple[str, ...] = ("Zo is thinking", "Press Esc to stop")