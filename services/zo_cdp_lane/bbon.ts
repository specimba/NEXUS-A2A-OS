/**
 * Behavior Best-of-N scaffold (Agent-S pattern, Zo /zo/ask parallel dispatch).
 */
export type BehaviorNarrative = {
  rollout_id: string;
  task_id: string;
  source_id: string;
  steps: { n: number; action: string; outcome: string; evidence?: string }[];
  result: "success" | "partial" | "fail";
  summary: string;
};

export type BbonJudgeInput = {
  task: string;
  narratives: BehaviorNarrative[];
};

export const JUDGE_SYSTEM_PROMPT = `You are the NEXUS bBoN judge. Pick the single best behavior narrative.
Criteria: evidence on disk, fewest assumptions, safe side effects, matches task.
Reply JSON only: {"winner_rollout_id":"...","reason":"...","hermes_exec":["one verify command"]}`;

export function buildJudgeUserPrompt(input: BbonJudgeInput): string {
  return JSON.stringify(input, null, 2);
}

export async function dispatchZoRollouts(
  task: string,
  n: number
): Promise<BehaviorNarrative[]> {
  const port = Number(process.env.NEXUS_ZO_CDP_PORT ?? 7358);
  const res = await fetch(`http://127.0.0.1:${port}/zo/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, n })
  });
  if (!res.ok) {
    throw new Error(`Failed to dispatch rollouts: ${res.statusText}`);
  }
  const data = await res.json();
  return data.all_rollouts;
}