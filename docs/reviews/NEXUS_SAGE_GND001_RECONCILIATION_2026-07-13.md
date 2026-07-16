# NEXUS SAGE GND-001 Reconciliation

**Date:** 2026-07-13  
**Scope:** full stored-content read of the latest antiGRAV, FABLE5, and Kilo orchestration logs, reconciled against the current SAGE checkout and live observe-only probes  
**Status:** evidence input and contradiction ledger; not a completion or canonical-state claim

## Coverage ledger

Every stored line of the following four files was read. Literal truncation markers already present inside the transcripts remain unrecoverable; there were no unreadable filesystem regions.

| Source | Lines | Bytes | SHA-256 |
|---|---:|---:|---|
| `NEXUSantiGRAVnexlog-12.txt` | 2,138 | 160,140 | `27B586876A91FE4A202B5EFD219778FE155100CB6FD02B8A9B30BD650ECAEDD3` |
| `NEXUSgeneralFABLE5advisorylogs-04.txt` | 2,466 | 215,340 | `DA0D8591289CD73AA499AF366AEB9C5E7E6288A492A664C871CFEF0B09EF478B` |
| `NEXUSkilocodeORCHESTRATORagentlogs-07.txt` | 2,058 | 136,671 | `1B351859D52FAC81376E981ECD8388A2F56A16BEE841C1AB79AE7078482506B3` |
| `NEXUSkilocodeORCHESTRATORagentlogs-06.txt` | 1,839 | 106,342 | `E62AF98E1C7F69915625169F8C636048F453ADDD8AA8635AD5A6DFE9718022EC` |

## Reconciliation rule

Downloaded logs are evidence inputs, not runtime authority. A log statement is accepted only at the level its reproduced artifact, test, or live probe supports. Later filesystem state and current claim gates supersede inherited session summaries.

## SAGE truth

- antiGRAV ends with the operator starting the SAGE task and contains no subsequent SAGE implementation (`NEXUSantiGRAVnexlog-12.txt:2134-2138`).
- Kilo07 cites the convergence plan as input (`NEXUSkilocodeORCHESTRATORagentlogs-07.txt:1272-1287`), but its later “SAGE gateway live” wording is a summary without a reproduced route probe (`:1821-1837`).
- Those logs establish SAGE priority, not SAGE runtime proof.

Current proof is therefore sourced from this checkout and the 2026-07-13 coordinator gates:

- focused SAGE suite: `166 passed`;
- Brain `127.0.0.1:7352`: listener PID `24072`, supervisor PID `92684`;
- Brain, loopback edge, and host-pinned public-preview verifiers: `ok=true`, `mode=observe_only`, six operations, `secret_emitted=false`;
- retention: canonical live database reached in `dry_run`, `state=complete`, `applied=false`;
- public model-card projection: recursively reconstructed from typed allowlists and independently revalidated;
- ChatGPT project remains a private unpublished Draft; no proposal write or execution authority is claimed.

## ModelRelay dependency truth

The logs establish the defect history, not current provider health:

- registry/runtime/scorer catalogues were fragmented and GLM-5.2 propagation was incomplete (`NEXUSantiGRAVnexlog-12.txt:371-383`);
- FABLE observed 237 relay rows with 83 synthetic `0.45` intelligence values (`NEXUSgeneralFABLE5advisorylogs-04.txt:1372-1405`);
- the approved hardening design required a repo-owned runtime, loopback/CORS/config containment, provider-level health probes, a bounded NIM governor, generated evidence scoring, and CLI synchronization (`NEXUSgeneralFABLE5advisorylogs-04.txt:1523-1573`);
- seven landing commits reportedly passed 577 Python and 13 Node tests, but the transcript explicitly says the live `7350` launcher cutover did not occur (`NEXUSgeneralFABLE5advisorylogs-04.txt:2356-2379`);
- the same transcript keeps launcher cutover, NIM 8-RPM/cooldown behavior, score unification, catalogue correction, and HERMES live-write work open (`:2411-2458`).

SAGE must therefore expose catalogue presence, CLI visibility, authenticated health, benchmark evidence, and policy priors as separate facts. `UNSCORED` remains the correct state when compatible evidence is absent. SAGE may not convert catalogue metadata, registry tiers, fixtures, or an inherited 45% default into benchmark proof.

## A2A and Agent Client Protocol boundary

The integrated path is one governed envelope, not four unrelated authorities:

```text
ACP/IDE client or A2A peer
  -> Bridge / Brain
  -> canonical NEXUS envelope
  -> Governor + KAIJU
  -> HERMES / Engine
  -> ModelRelay | MCP | CDP execution/evidence channel
  -> artifact + continuity + trust evidence
```

The unified intent appears in `NEXUSantiGRAVnexlog-12.txt:1843-1938`. ACP is the northbound IDE/session protocol; A2A is delegation/task interoperability. Neither is a governor. HERMES remains an ACP-compatible execution client/lifecycle owner, not an authorization plane.

The historical first nine-lane A2A cycle was `0/9`; later broad “A2A closed” summaries do not replace a positive governed artifact cycle and a proofless negative denial. SAGE does not inherit A2A completion from those summaries.

## Agent-lane allocation

| Lane | Accepted role | Required evidence |
|---|---|---|
| FABLE5 | research, benchmark design, architecture critique | source/artifact provenance; no direct runtime claim |
| Codex / NEXUS | root orchestration, bounded implementation, claim gates | current diff, tests, live probe, continuity record |
| OpenCode / Kilo | CLI, registry, continuity, client synchronization | exact list/inference/tool-call probe |
| Grok | MCP/CDP/runtime/port and bounded Intern work | listener/DOM/artifact evidence |
| HERMES | approved-task claim/execute/retry/close; ACP-compatible client | canonical envelope, bounded retry, receipt |
| Qwen browser lane | Preview-DOM observation | current DOM delta, not chat assertion |
| Intern/A800 | human-driven science/training bench | quota hard rule, one kernel, durable artifact |

## Ordered deltas

### P0

1. Keep SAGE private, unpublished, and `observe_only`.
2. Preserve exact port/process ownership, six Actions, deep response sanitization, DLP, retention, and negative-authority gates.
3. Re-probe active ModelRelay/HERMES state before repeating historical counts.
4. Keep all no-evidence model quality as `null`/`UNSCORED`.
5. Treat the fresh changed-only grounding-scan hang as a liveness defect; do not reuse the prior successful scan as current proof.

### P1

1. Add public-edge abuse controls while retaining the fixed loopback origin and auth-before-upstream rule.
2. Complete one canonical provider/offer/alias catalogue and cross-client reach matrix.
3. Prove one Brain-governed A2A artifact cycle and one proofless denial.
4. Prepare a public-safe SAGE repository containing contracts, mocks, governance, and threat boundaries only.

### P2

1. Add per-user identity, durable hosting/privacy ownership, encrypted or approved proposal storage, deletion, backup/recovery, and reviewed scheduled retention.
2. Promote `proposal_write` only after an explicit gate and independent review transition service.
3. Add signed/fresh model-evidence provenance and provider-throttling telemetry.

### P3

1. Map ACP/A2A/MCP/CDP to one envelope and receipt identity.
2. Add CLI/model-card consistency, replay, lease, recursion, and dead-loop tests.
3. Bench the 8 GB local stack before any architecture change; keep A800 work human-driven and quota-gated.

### P4

1. Automate provider/endpoint/free-offer discovery as advisory diffs only.
2. Keep OmniRoute and similar aggregators quarantined as adapter/catalogue candidates until provenance, security, compatibility, and rollback gates pass.
3. Publish only leak-scanned, public-safe SAGE artifacts; never raw logs, private evidence, secrets, weights, or internal runtime topology.

## Claim limit

This reconciliation supports a private observe-only SAGE proof. It does not claim public production, proposal-write authority, execution authority, ModelRelay provider health, HERMES parity, A2A completion, or whole-system completion.
