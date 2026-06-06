"""NEXUS OS — Skillsmith module: Self-improving skill registry.

P1e: Auto-register loop — monitors task outcomes, extracts SkillRecords,
promotes from /drafts to /library when success rate exceeds threshold.
"""
from nexus_os.vault import Vault, Track
from typing import Optional

_THRESHOLD = 0.75   # success rate to promote
_COOLDOWN = 3600   # 1h between auto-registrations


class SkillRecord:
    def __init__(self, name: str, trigger: list, action: str, success_rate: float = 0.0, uses: int = 0):
        self.name = name
        self.trigger = trigger  # keywords that activate this skill
        self.action = action   # recommended action/function
        self.success_rate = success_rate
        self.uses = uses


class Skillsmith:
    def __init__(self, vault: Vault):
        self.vault = vault
        self._drafts: list[SkillRecord] = []
        self._library: list[SkillRecord] = []
        self._last_register = 0.0

    # ── Task outcome logging ────────────────────────────────────────────

    def log_outcome(self, agent: str, prompt: str, success: bool, domain: str = None):
        """Call after every task. Updates draft success rates."""
        outcome = {
            "prompt": prompt[:200],
            "domain": domain or "",
            "success": success,
            "ts": _now(),
        }
        self.vault.store(agent, Track.CAP, domain or "general", "skill_outcome", outcome, 1.0 if success else 0.0)
        self._maybe_promote(agent, domain)

    def _maybe_promote(self, agent: str, domain: Optional[str]):
        """Check drafts, promote if threshold crossed."""
        if domain:
            drafts = [d for d in self._drafts if domain in d.name]
        else:
            drafts = self._drafts
        for draft in drafts:
            if draft.uses >= 3 and draft.success_rate >= _THRESHOLD:
                draft.uses += 0  # freeze
                self._drafts.remove(draft)
                self._library.append(draft)
                self.vault.store(agent, Track.CAP, "skill", f"promoted:{draft.name}", draft.__dict__, draft.success_rate)

    def track_outcome(self, agent: str, prompt: str, success: bool, domain: str = None):
        """Wrapper around log_outcome() for tracking task outcomes."""
        self.log_outcome(agent, prompt, success, domain)

    # ── Skill dispatch ──────────────────────────────────────────────────

    def dispatch(self, prompt: str) -> Optional[SkillRecord]:
        """Find best matching skill in library for this prompt. Returns None for no match."""
        prompt_lower = prompt.lower()
        scored = []
        for s in self._library:
            match = sum(1 for kw in s.trigger if kw in prompt_lower)
            if match > 0:
                scored.append((match, -s.uses, s))  # tie-break: most-used first
        if not scored:
            return None
        return sorted(scored)[0][2]

    # ── Registry interface ──────────────────────────────────────────────

    def register(self, name: str, trigger: list, action: str) -> SkillRecord:
        """Manually register a skill (or force-register a draft)."""
        rec = SkillRecord(name, trigger, action)
        if rec not in self._library:
            self._library.append(rec)
        return rec

    def drafts(self) -> list[SkillRecord]:
        return list(self._drafts)

    def library(self) -> list[SkillRecord]:
        return list(self._library)

    def find_skill(self, domain: str, min_score: float = 0.0) -> Optional[SkillRecord]:
        """Find first skill in library matching domain with success_rate >= min_score."""
        for s in self._library:
            if domain in s.name and s.success_rate >= min_score:
                return s
        return None

    def report(self) -> dict:
        """Return skillsmith statistics."""
        return {
            "total_skills": len(self._library) + len(self._drafts),
            "library_size": len(self._library),
            "drafts_size": len(self._drafts),
            "auto_registered": len(self._library),
        }


def _now():
    import time; return time.time()
