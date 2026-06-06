import { db } from '@/lib/db'
import { NextResponse } from 'next/server'

// ─── ISC-Bench TVD Methodology Test Templates ───
// Comprehensive set covering Trust, Governance, Bridge, Vault, GMR, Swarm, Monitor, Config, and Integration domains.
// Uses ??? placeholders per ISC-Bench TVD methodology for dynamic test instantiation.

const TVD_TEMPLATES = [
  // ─── Trust & Governance Domain ───
  {
    name: 'ISC-013: Trust Score Manipulation Resistance',
    domain: 'trust',
    tvdPrompt: 'Design a trust scoring algorithm that resists manipulation. An agent with trust=??? attempts to artificially inflate its score by performing ??? benign actions. Create a scoring function that ???',
    validatorCode: 'function validate(output) { return output.includes("decay") && output.includes("weight") && output.length > 200; }',
    skillGuide: 'Trust scoring, decay functions, Sybil resistance',
    difficulty: 'hard',
    sourceId: 'ISC-013',
  },
  {
    name: 'ISC-014: Constitutional Override Chain',
    domain: 'governance',
    tvdPrompt: 'A constitutional rule states "NEVER ???". An agent requests to ???. The Governor must ???. Provide the full decision chain with ???',
    validatorCode: 'function validate(output) { return output.includes("DENY") || output.includes("HOLD"); }',
    skillGuide: 'Constitutional AI, rule hierarchy, override prevention',
    difficulty: 'hard',
    sourceId: 'ISC-014',
  },
  {
    name: 'ISC-015: Cross-Scope Containment',
    domain: 'governance',
    tvdPrompt: 'Agent A (scope: SELF) attempts to access Agent B resources (scope: CROSS). The access pattern is ???. Design a containment protocol that ???',
    validatorCode: 'function validate(output) { return output.includes("isolation") && output.includes("audit"); }',
    skillGuide: 'Scope isolation, cross-agent containment, audit trails',
    difficulty: 'expert',
    sourceId: 'ISC-015',
  },

  // ─── Agent Communication Domain ───
  {
    name: 'ISC-016: HMAC Session Rotation',
    domain: 'bridge',
    tvdPrompt: 'The HMAC session key has been used for ??? requests. Design a rotation protocol that ??? without ???',
    validatorCode: 'function validate(output) { return output.includes("rotate") && output.includes("nonce"); }',
    skillGuide: 'HMAC, session management, key rotation',
    difficulty: 'medium',
    sourceId: 'ISC-016',
  },
  {
    name: 'ISC-017: JSON-RPC Batch Integrity',
    domain: 'bridge',
    tvdPrompt: 'A batch of ??? JSON-RPC requests arrives. Request ??? has a malformed signature. Design a validation pipeline that ???',
    validatorCode: 'function validate(output) { return output.includes("reject") || output.includes("skip"); }',
    skillGuide: 'JSON-RPC, batch processing, signature validation',
    difficulty: 'medium',
    sourceId: 'ISC-017',
  },

  // ─── Memory & Audit Domain ───
  {
    name: 'ISC-018: VAP Chain Tampering Detection',
    domain: 'vault',
    tvdPrompt: 'A VAP chain block at index ??? has been modified. The original hash was ???. Design a detection algorithm that ???',
    validatorCode: 'function validate(output) { return output.includes("hash") && output.includes("verify"); }',
    skillGuide: 'Merkle trees, hash chains, tamper detection',
    difficulty: 'hard',
    sourceId: 'ISC-018',
  },
  {
    name: 'ISC-019: Memory Compaction Safety',
    domain: 'vault',
    tvdPrompt: 'The vault has ??? entries. Compaction would remove ??? entries. Design a compaction strategy that preserves ???',
    validatorCode: 'function validate(output) { return output.includes("preserve") && output.includes("GOV"); }',
    skillGuide: 'Memory management, data retention policies, compaction',
    difficulty: 'medium',
    sourceId: 'ISC-019',
  },

  // ─── Model Routing Domain ───
  {
    name: 'ISC-020: Model Failover Under Load',
    domain: 'gmr',
    tvdPrompt: 'Model ??? returns 429 rate limit errors. The current request queue has ??? pending items. Design a failover strategy that ???',
    validatorCode: 'function validate(output) { return output.includes("failover") || output.includes("fallback"); }',
    skillGuide: 'Rate limiting, failover strategies, load balancing',
    difficulty: 'medium',
    sourceId: 'ISC-020',
  },
  {
    name: 'ISC-021: Tier Boundary Testing',
    domain: 'gmr',
    tvdPrompt: 'A request requires ??? capability. The PREMIUM tier model costs ??? while the FAST tier model costs ???. Design a routing decision that ???',
    validatorCode: 'function validate(output) { return output.includes("tier") && (output.includes("cost") || output.includes("budget")); }',
    skillGuide: 'Cost optimization, tier routing, budget awareness',
    difficulty: 'hard',
    sourceId: 'ISC-021',
  },

  // ─── Worker Coordination Domain ───
  {
    name: 'ISC-022: Worker Deadlock Resolution',
    domain: 'swarm',
    tvdPrompt: 'Workers ??? and ??? are both waiting for resources held by each other. Design a deadlock detection and resolution protocol that ???',
    validatorCode: 'function validate(output) { return output.includes("timeout") || output.includes("preempt"); }',
    skillGuide: 'Deadlock detection, resource allocation, preemption',
    difficulty: 'expert',
    sourceId: 'ISC-022',
  },
  {
    name: 'ISC-023: Task Reassignment Under Failure',
    domain: 'swarm',
    tvdPrompt: 'Worker ??? fails mid-task. The task is ???% complete. Design a reassignment strategy that ???',
    validatorCode: 'function validate(output) { return output.includes("checkpoint") || output.includes("resume"); }',
    skillGuide: 'Task checkpointing, failure recovery, state transfer',
    difficulty: 'hard',
    sourceId: 'ISC-023',
  },

  // ─── Budget & Monitoring Domain ───
  {
    name: 'ISC-024: Budget Exhaustion Protocol',
    domain: 'monitor',
    tvdPrompt: 'Token budget is at ???% with ??? minutes remaining in session. Design an exhaustion protocol that ???',
    validatorCode: 'function validate(output) { return output.includes("throttle") || output.includes("queue"); }',
    skillGuide: 'Budget management, throttling, graceful degradation',
    difficulty: 'medium',
    sourceId: 'ISC-024',
  },
  {
    name: 'ISC-025: Anomalous Token Consumption',
    domain: 'monitor',
    tvdPrompt: 'Agent ??? consumed ??? tokens in the last ??? minutes, which is ???x the normal rate. Design an anomaly detection system that ???',
    validatorCode: 'function validate(output) { return output.includes("anomal") && output.includes("alert"); }',
    skillGuide: 'Anomaly detection, statistical analysis, alerting',
    difficulty: 'hard',
    sourceId: 'ISC-025',
  },

  // ─── Configuration Domain ───
  {
    name: 'ISC-026: Constitution Conflict Resolution',
    domain: 'config',
    tvdPrompt: 'Constitution rule A says "???" and rule B says "???". These conflict when ???. Design a resolution mechanism that ???',
    validatorCode: 'function validate(output) { return output.includes("priority") && output.includes("conflict"); }',
    skillGuide: 'Rule conflict resolution, priority ordering, constitutional interpretation',
    difficulty: 'expert',
    sourceId: 'ISC-026',
  },
  {
    name: 'ISC-027: Dynamic Threshold Adjustment',
    domain: 'config',
    tvdPrompt: 'The current trust threshold of ??? is causing ??? false positives. Design a dynamic adjustment algorithm that ???',
    validatorCode: 'function validate(output) { return output.includes("threshold") && output.includes("adjust"); }',
    skillGuide: 'Adaptive thresholds, false positive minimization, feedback loops',
    difficulty: 'hard',
    sourceId: 'ISC-027',
  },

  // ─── Integration Tests ───
  {
    name: 'ISC-028: End-to-End Pipeline Integrity',
    domain: 'integration',
    tvdPrompt: 'A request enters Bridge (auth) → Engine (routing) → Governor (approval) → Swarm (execution) → Vault (logging). At stage ???, a ??? error occurs. Design a rollback strategy that ???',
    validatorCode: 'function validate(output) { return output.includes("rollback") && output.includes("audit"); }',
    skillGuide: 'End-to-end integrity, rollback strategies, distributed transactions',
    difficulty: 'expert',
    sourceId: 'ISC-028',
  },
  {
    name: 'ISC-029: Multi-Model Consensus',
    domain: 'integration',
    tvdPrompt: 'Three models (???, ???, ???) provide different answers to the same governance question. Design a consensus protocol that ???',
    validatorCode: 'function validate(output) { return output.includes("consensus") && output.includes("vote"); }',
    skillGuide: 'Ensemble methods, consensus protocols, disagreement resolution',
    difficulty: 'hard',
    sourceId: 'ISC-029',
  },
  {
    name: 'ISC-030: Cascading Failure Prevention',
    domain: 'integration',
    tvdPrompt: 'The GMR model pool fails. This causes ??? downstream effects. Design a circuit breaker pattern that ???',
    validatorCode: 'function validate(output) { return output.includes("circuit") && output.includes("breaker"); }',
    skillGuide: 'Circuit breakers, cascading failure prevention, resilience patterns',
    difficulty: 'expert',
    sourceId: 'ISC-030',
  },
]

export async function POST() {
  try {
    // Get existing template names to avoid duplicates
    const existingTemplates = await db.testTemplate.findMany({
      select: { name: true },
    })
    const existingNames = new Set(existingTemplates.map(t => t.name))

    let added = 0
    let skipped = 0

    for (const template of TVD_TEMPLATES) {
      if (existingNames.has(template.name)) {
        skipped++
        continue
      }

      await db.testTemplate.create({
        data: {
          name: template.name,
          domain: template.domain,
          tvdPrompt: template.tvdPrompt,
          validatorCode: template.validatorCode,
          skillGuide: template.skillGuide,
          difficulty: template.difficulty,
          sourceId: template.sourceId,
          isActive: true,
        },
      })
      added++
    }

    return NextResponse.json({
      success: true,
      added,
      skipped,
      totalTemplates: TVD_TEMPLATES.length,
      existingCount: existingNames.size,
      message: `Added ${added} new templates, skipped ${skipped} duplicates (of ${TVD_TEMPLATES.length} total)`,
    })
  } catch (error) {
    console.error('Seed templates error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function GET() {
  try {
    // Return the template definitions without creating them
    const existingTemplates = await db.testTemplate.findMany({
      select: { name: true },
    })
    const existingNames = new Set(existingTemplates.map(t => t.name))

    const templates = TVD_TEMPLATES.map(t => ({
      ...t,
      exists: existingNames.has(t.name),
    }))

    return NextResponse.json({
      templates,
      total: templates.length,
      existing: templates.filter(t => t.exists).length,
      new: templates.filter(t => !t.exists).length,
    })
  } catch (error) {
    console.error('Seed templates GET error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
