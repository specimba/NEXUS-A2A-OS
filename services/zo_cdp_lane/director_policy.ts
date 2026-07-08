/**
 * Port of NEXUS external_browser_ai_director policy (subset, side-effect free).
 */
import { createHash } from "node:crypto";

export const ACTIONS = [
  "NOOP_UNCHANGED",
  "WAITING_MODEL",
  "CONTINUE_SENT",
  "ARTIFACT_CAPTURED",
  "BLOCKED_SETUP",
  "RETRY_LATER",
  "ESCALATE_CODEX",
] as const;

export type DirectorAction = (typeof ACTIONS)[number];

export type CycleObservation = {
  cdpStatus: "ok" | "error";
  bridgeStatus?: string;
  visibleMarker: string;
  visibleTail: string;
  modelGenerating?: boolean;
  newArtifactName?: string | null;
  errorCode?: string | null;
  requiresBridge?: boolean;
};

export type DirectorDecision = {
  action: DirectorAction;
  reason: string;
  providerAllowed?: boolean;
};

export function stableFingerprint(...parts: string[]): string {
  const h = createHash("sha256");
  for (const p of parts) {
    h.update(p, "utf8");
    h.update("\0");
  }
  return "sha256:" + h.digest("hex");
}

export function decideCycle(
  obs: CycleObservation,
  previousFingerprint: string | null
): DirectorDecision {
  if (obs.errorCode === "cdp_missing" || obs.cdpStatus !== "ok") {
    return { action: "BLOCKED_SETUP", reason: "cdp_not_ok" };
  }
  if (obs.requiresBridge && obs.bridgeStatus && obs.bridgeStatus !== "ok") {
    return { action: "BLOCKED_SETUP", reason: "bridge_unhealthy" };
  }
  const fp = stableFingerprint(
    obs.visibleMarker,
    obs.visibleTail.slice(-2048),
    obs.newArtifactName ?? ""
  );
  if (previousFingerprint === fp) {
    return { action: "NOOP_UNCHANGED", reason: "visible_fingerprint_unchanged" };
  }
  if (obs.modelGenerating) {
    return { action: "WAITING_MODEL", reason: "model_generating" };
  }
  return { action: "CONTINUE_SENT", reason: "material_visible_delta", providerAllowed: true };
}