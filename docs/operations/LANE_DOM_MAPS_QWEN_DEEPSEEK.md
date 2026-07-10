# Lane DOM maps — Qwen WebDev + DeepSeek (from ARCHIVIST DevTools exports 2026-07-09)

Sources:
- `ARCHIVIST/QWENdevbrowserALLpositionsREVEALED.md`
- `ARCHIVIST/DEEPSEEKbrowserALLpositionsREVEALED.md`

Viewport reference ~1056×911 (scale if different).

## Qwen WebDev (chat.qwen.ai — NEXUS-OS project)

### Success semantics
**Do not wait for long chat prose.** Success = Code / Preview / Deploy UI change.

### Key selectors
| Action | Selector / notes | Coords (ref) |
|--------|------------------|--------------|
| Preview (header) | `.qwen-chat-btn.brandsecondary.round.small.circle...` | ~92, 11 |
| Preview (inline) | same class family | ~92, 734 |
| Deploy | `button.chat-artifact-header-deploy` / deploy-dropdown | ~914, 12 |
| Artifact preview switch | `.artifacts-body-header-switch-active` | ~769, 69 |
| Send | `.message-input-right-button-send` or `.chat-prompt-send-button` or `button.send-button` | bottom ~80px |
| Voice | `button.record-btn` | bottom area |
| Help | `.qwen-chat-layout-help` fixed | ~1020, 875 |
| Thinking mode | `.qwen-select-thinking-label` | ~307, 829 |
| Composer | textarea placeholder *Describe the web page you want to generate.* | bottom |

### Shadow noise
Monica / ChatGPT-sidebar / DeepL hosts — ignore for NEXUS automation.

### Automation policy
1. Send task.  
2. Poll **Preview/Code/Deploy** DOM or artifact header, not `body.innerText` length alone.  
3. Evidence: screenshot path or preview HTML hash via MCP `evidence_capture`.

## DeepSeek (chat.deepseek.com)

### Layout shell
| Region | Class / notes | Rect (ref) |
|--------|---------------|------------|
| Sidebar | `.dc04ec1d` | left 0, width ~261, full height |
| Main | `._7780f2e` | left ~261, width ~795 |
| Overlay fixed | `._4cbcd96` | full viewport fixed |
| Assistant content | `.ds-markdown.ds-assistant-message-main-content` | main column |
| Notifications | `.ds-notification-container` | fixed corners |
| Floating | `.ds-floating-container` | full fixed z |

### Composer / send
| Control | Selector | Notes |
|---------|----------|-------|
| Composer | `textarea[placeholder="Message DeepSeek"]` | fill here |
| Send | `div.ds-button.ds-button--primary.ds-button--filled.ds-button--circle` | icon-only |
| Tertiary icons | `div.ds-button.ds-button--iconLabelTertiary...` | not send |

### Evidence pitfall
`document.body.innerText` can stay ~shell (title/Expert/DeepThink) even after send.  
Prefer:
- `.ds-assistant-message-main-content` text length growth  
- or composer cleared **and** new `.ds-markdown` node  
- operator visual confirm while keep-visible daemon runs

### Automation policy
1. Fill textarea.  
2. Click primary circle (not tertiary icons).  
3. Wait on **assistant markdown nodes**, not full body.
