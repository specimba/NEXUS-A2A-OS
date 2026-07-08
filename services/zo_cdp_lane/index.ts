import { serve } from "bun";
import { 
  BbonJudgeInput, 
  BehaviorNarrative, 
  JUDGE_SYSTEM_PROMPT, 
  buildJudgeUserPrompt 
} from "./bbon";

const PORT = Number(process.env.NEXUS_ZO_CDP_PORT ?? 7358);
const RELAY_URL = process.env.NEXUS_MODEL_RELAY_URL ?? "http://127.0.0.1:7350/v1/chat/completions";

/**
 * Dispatches N parallel model completions using different temperature/seeds to simulate rollouts.
 */
async function generateRollouts(task: string, n: number): Promise<BehaviorNarrative[]> {
  const rollouts: BehaviorNarrative[] = [];
  const promises: Promise<void>[] = [];

  for (let i = 0; i < n; i++) {
    const rolloutId = `rollout-${Math.random().toString(36).slice(2, 9)}`;
    const temp = 0.5 + (i * 0.15); // Vary temperature for diverse candidates

    const p = fetch(RELAY_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "auto-fastest",
        temperature: temp,
        messages: [
          {
            role: "system",
            value: "You are a NEXUS sub-agent planner. Output a step-by-step behavior narrative for this task. Include verification commands."
          },
          {
            role: "user",
            value: `Task: ${task}`
          }
        ]
      })
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Model completion failed for rollout ${rolloutId}: ${res.statusText}`);
        }
        const data = await res.json();
        const content = data.choices?.[0]?.message?.content ?? "";
        
        rollouts.push({
          rollout_id: rolloutId,
          task_id: "task-bbon-current",
          source_id: "zo-browser-lab",
          steps: [
            {
              n: 1,
              action: `Initialize model rollout with temp=${temp.toFixed(2)}`,
              outcome: "Success",
            },
            {
              n: 2,
              action: "Execute strategy generation",
              outcome: "Completed",
              evidence: "Model output length: " + content.length
            }
          ],
          result: "success",
          summary: content
        });
      })
      .catch((err) => {
        rollouts.push({
          rollout_id: rolloutId,
          task_id: "task-bbon-current",
          source_id: "zo-browser-lab",
          steps: [
            {
              n: 1,
              action: "Initialize rollout",
              outcome: "Failed: " + err.message,
            }
          ],
          result: "fail",
          summary: `Rollout generation failed: ${err.message}`
        });
      });

    promises.push(p);
  }

  await Promise.all(promises);
  return rollouts;
}

/**
 * Submits the rollouts to the ensembling judge.
 */
async function runJudge(task: string, narratives: BehaviorNarrative[]): Promise<any> {
  const judgeInput: BbonJudgeInput = { task, narratives };
  const userPrompt = buildJudgeUserPrompt(judgeInput);

  const res = await fetch(RELAY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "auto-fastest",
      temperature: 0.1,
      messages: [
        {
          role: "system",
          value: JUDGE_SYSTEM_PROMPT
        },
        {
          role: "user",
          value: userPrompt
        }
      ]
    })
  });

  if (!res.ok) {
    throw new Error(`Judge request failed: ${res.statusText}`);
  }

  const data = await res.json();
  const rawContent = data.choices?.[0]?.message?.content ?? "";
  
  // Clean up codeblock formatting if returned by model
  const cleaned = rawContent.replace(/```json|```/g, "").trim();
  return JSON.parse(cleaned);
}

const server = serve({
  port: PORT,
  async fetch(req) {
    const url = new URL(req.url);

    if (req.method === "GET" && url.pathname === "/health") {
      return Response.json({ status: "ok", service: "zo-cdp-lane-bbon" });
    }

    if (req.method === "POST" && url.pathname === "/zo/ask") {
      try {
        const body = await req.json();
        if (!body.task) {
          return new Response(JSON.stringify({ error: "Missing required parameter: task" }), {
            status: 400,
            headers: { "Content-Type": "application/json" }
          });
        }

        const n = Number(body.n ?? 3);
        console.log(`[bBoN] Received task: "${body.task}" (N=${n})`);
        
        console.log(`[bBoN] Dispatched ${n} rollouts...`);
        const narratives = await generateRollouts(body.task, n);

        console.log(`[bBoN] Running SEMA Judge...`);
        const verdict = await runJudge(body.task, narratives);

        return Response.json({
          status: "success",
          task: body.task,
          verdict,
          all_rollouts: narratives
        });
      } catch (err: any) {
        console.error("[bBoN] Error processing request:", err);
        return new Response(JSON.stringify({ error: err.message }), {
          status: 500,
          headers: { "Content-Type": "application/json" }
        });
      }
    }

    return new Response("Not Found", { status: 404 });
  }
});

console.log(`[bBoN] Zo CDP Lane service listening on http://localhost:${server.port}`);
