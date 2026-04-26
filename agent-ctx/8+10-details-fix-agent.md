# Task 8+10: Details Fix Agent — Work Record

## Task
Fix two issues:
1. ISC Test Runs need conversation details dialog
2. Vault tab UX onboarding for user understanding

## Changes Made

### stresslab-tab.tsx
- Added `RunConversation` interface (systemPrompt, userPrompt, modelResponse, verdict, promptTokens, completionTokens)
- Added `conversation` and `durationMs` to `UIRun` interface
- Created `generateMockConversation()` with domain-specific system prompts and template-specific adversarial user prompts for all 12 ISC templates
- Added "View" button column to Recent Test Runs table + clickable rows
- Created Test Run Detail Dialog with: result summary, token breakdown, system prompt, user prompt, model response, verdict, copy buttons
- Added state: selectedRun, runDetailOpen
- Added lucide imports: Eye, MessageSquare, Copy, Timer, Hash

### vault-tab.tsx
- Added dismissible onboarding card at top with:
  - "Vault — 5-Track Memory Plane" title
  - 5 track explanation cards with descriptions
  - VAP Proof Chain explanation
  - "How to Use" tips (4 items)
- Added showOnboarding state (default: true)
- Added lucide imports: Info, Lightbulb, MousePointerClick, BookOpen

## Verification
- Lint: PASS (zero errors)
- Dev server: running cleanly on port 3000
