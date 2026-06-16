"""
bridge/deployment_gate.py — Deployment Gate Checker

Validates deployment readiness across Vercel and Cloudflare Workers targets.
Provides health checks, pre-deployment validation, and fallback routing
when primary deployment targets are unreachable.

Known issues (as of 2026-05-21):
  - Vercel: Account blocked (external infrastructure; requires manual resolution)
  - Cloudflare Workers: Deployment failing (wrangler auth issue)

This module implements:
  1. Health checks for both platforms
  2. Deployment readiness validation
  3. Fallback to local-only mode when both are unavailable
  4. Status reporting for dashboard consumption
"""

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DeployTarget(Enum):
    VERCEL = "vercel"
    CLOUDFLARE_WORKERS = "cloudflare_workers"
    LOCAL_ONLY = "local_only"


class GateStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class DeploymentCheck:
    """Result of a single deployment target check."""
    target: DeployTarget
    status: GateStatus
    message: str
    checked_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentGateResult:
    """Aggregate result of all deployment gate checks."""
    overall_status: GateStatus
    checks: List[DeploymentCheck]
    recommended_target: DeployTarget
    fallback_active: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "recommended_target": self.recommended_target.value,
            "fallback_active": self.fallback_active,
            "timestamp": self.timestamp,
            "checks": [
                {
                    "target": c.target.value,
                    "status": c.status.value,
                    "message": c.message,
                    "checked_at": c.checked_at,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


class DeploymentGate:
    """
    Validates deployment gates for Vercel and Cloudflare Workers.
    Falls back to local-only mode when external targets are unavailable.
    """

    def __init__(
        self,
        vercel_token: Optional[str] = None,
        cloudflare_token: Optional[str] = None,
        vercel_project_id: Optional[str] = None,
        cloudflare_account_id: Optional[str] = None,
        check_timeout: float = 10.0,
    ):
        self.vercel_token = vercel_token
        self.cloudflare_token = cloudflare_token
        self.vercel_project_id = vercel_project_id
        self.cloudflare_account_id = cloudflare_account_id
        self.check_timeout = check_timeout
        self._last_result: Optional[DeploymentGateResult] = None
        self._cache_ttl = 60.0

    def check_all(self, force: bool = False) -> DeploymentGateResult:
        """Run all deployment gate checks and return aggregate result."""
        if not force and self._last_result:
            age = time.time() - self._last_result.timestamp
            if age < self._cache_ttl:
                return self._last_result

        checks = [
            self._check_vercel(),
            self._check_cloudflare(),
        ]

        healthy_targets = [c for c in checks if c.status == GateStatus.HEALTHY]
        degraded_targets = [c for c in checks if c.status == GateStatus.DEGRADED]

        if healthy_targets:
            overall = GateStatus.HEALTHY
            recommended = healthy_targets[0].target
            fallback = False
        elif degraded_targets:
            overall = GateStatus.DEGRADED
            recommended = degraded_targets[0].target
            fallback = False
        else:
            overall = GateStatus.BLOCKED
            recommended = DeployTarget.LOCAL_ONLY
            fallback = True

        result = DeploymentGateResult(
            overall_status=overall,
            checks=checks,
            recommended_target=recommended,
            fallback_active=fallback,
        )
        self._last_result = result
        return result

    def _check_vercel(self) -> DeploymentCheck:
        """Check Vercel deployment readiness."""
        if not self.vercel_token:
            return DeploymentCheck(
                target=DeployTarget.VERCEL,
                status=GateStatus.BLOCKED,
                message="No Vercel token configured",
                details={"reason": "missing_credentials"},
            )

        try:
            import requests
        except ImportError:
            return DeploymentCheck(
                target=DeployTarget.VERCEL,
                status=GateStatus.BLOCKED,
                message="requests library not available",
                details={"reason": "missing_dependency"},
            )

        max_attempts = 3
        attempt = 0
        backoff = 1.0

        while attempt < max_attempts:
            attempt += 1
            try:
                resp = requests.get(
                    "https://api.vercel.com/v9/projects",
                    headers={"Authorization": f"Bearer {self.vercel_token}"},
                    timeout=self.check_timeout,
                    params={"limit": "1"},
                )
                if resp.status_code == 200:
                    return DeploymentCheck(
                        target=DeployTarget.VERCEL,
                        status=GateStatus.HEALTHY,
                        message="Vercel API accessible",
                        details={"http_status": 200},
                    )
                elif resp.status_code == 403 or resp.status_code == 401:
                    return DeploymentCheck(
                        target=DeployTarget.VERCEL,
                        status=GateStatus.BLOCKED,
                        message="Vercel account blocked or token revoked",
                        details={"http_status": resp.status_code, "body": resp.text[:200]},
                    )
                elif resp.status_code >= 500:
                    if attempt == max_attempts:
                        return DeploymentCheck(
                            target=DeployTarget.VERCEL,
                            status=GateStatus.DEGRADED,
                            message=f"Vercel API returned {resp.status_code} after {max_attempts} attempts",
                            details={"http_status": resp.status_code},
                        )
                else:
                    return DeploymentCheck(
                        target=DeployTarget.VERCEL,
                        status=GateStatus.DEGRADED,
                        message=f"Vercel API returned {resp.status_code}",
                        details={"http_status": resp.status_code},
                    )
            except requests.RequestException as e:
                if attempt == max_attempts:
                    return DeploymentCheck(
                        target=DeployTarget.VERCEL,
                        status=GateStatus.BLOCKED,
                        message=f"Vercel check failed after {max_attempts} attempts: {e}",
                        details={"error": str(e)},
                    )

            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= 2.0

    def _check_cloudflare(self) -> DeploymentCheck:
        """Check Cloudflare Workers deployment readiness."""
        if not self.cloudflare_token:
            return DeploymentCheck(
                target=DeployTarget.CLOUDFLARE_WORKERS,
                status=GateStatus.BLOCKED,
                message="No Cloudflare token configured",
                details={"reason": "missing_credentials"},
            )

        try:
            import requests
        except ImportError:
            return DeploymentCheck(
                target=DeployTarget.CLOUDFLARE_WORKERS,
                status=GateStatus.BLOCKED,
                message="requests library not available",
                details={"reason": "missing_dependency"},
            )

        max_attempts = 3
        attempt = 0
        backoff = 1.0

        while attempt < max_attempts:
            attempt += 1
            try:
                resp = requests.get(
                    f"https://api.cloudflare.com/client/v4/accounts/{self.cloudflare_account_id}/workers/scripts",
                    headers={"Authorization": f"Bearer {self.cloudflare_token}"},
                    timeout=self.check_timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        return DeploymentCheck(
                            target=DeployTarget.CLOUDFLARE_WORKERS,
                            status=GateStatus.HEALTHY,
                            message="Cloudflare Workers API accessible",
                            details={"http_status": 200},
                        )
                    else:
                        return DeploymentCheck(
                            target=DeployTarget.CLOUDFLARE_WORKERS,
                            status=GateStatus.DEGRADED,
                            message="Cloudflare API returned 200 but success=false",
                            details={"http_status": 200, "success": False, "body": resp.text[:200]},
                        )
                elif resp.status_code == 403 or resp.status_code == 401:
                    return DeploymentCheck(
                        target=DeployTarget.CLOUDFLARE_WORKERS,
                        status=GateStatus.BLOCKED,
                        message="Cloudflare token invalid or permissions missing",
                        details={"http_status": resp.status_code, "body": resp.text[:200]},
                    )
                elif resp.status_code >= 500:
                    if attempt == max_attempts:
                        return DeploymentCheck(
                            target=DeployTarget.CLOUDFLARE_WORKERS,
                            status=GateStatus.DEGRADED,
                            message=f"Cloudflare API returned {resp.status_code} after {max_attempts} attempts",
                            details={"http_status": resp.status_code},
                        )
                else:
                    return DeploymentCheck(
                        target=DeployTarget.CLOUDFLARE_WORKERS,
                        status=GateStatus.DEGRADED,
                        message=f"Cloudflare API returned {resp.status_code}",
                        details={"http_status": resp.status_code},
                    )
            except requests.RequestException as e:
                if attempt == max_attempts:
                    return DeploymentCheck(
                        target=DeployTarget.CLOUDFLARE_WORKERS,
                        status=GateStatus.BLOCKED,
                        message=f"Cloudflare check failed after {max_attempts} attempts: {e}",
                        details={"error": str(e)},
                    )

            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= 2.0

    def get_status_summary(self) -> Dict[str, Any]:
        """Return a dashboard-friendly status summary."""
        result = self.check_all()
        return {
            "deployment_gate": result.to_dict(),
            "action_required": result.overall_status == GateStatus.BLOCKED,
            "resolution_steps": self._get_resolution_steps(result),
        }

    def _get_resolution_steps(self, result: DeploymentGateResult) -> List[str]:
        """Provide actionable resolution steps for blocked gates."""
        steps = []
        for check in result.checks:
            if check.status == GateStatus.BLOCKED:
                if check.target == DeployTarget.VERCEL:
                    steps.append(
                        "Vercel: Contact support or re-authenticate at "
                        "https://vercel.com/account/tokens"
                    )
                elif check.target == DeployTarget.CLOUDFLARE_WORKERS:
                    steps.append(
                        "Cloudflare: Verify wrangler auth with "
                        "'wrangler whoami' or regenerate API token at "
                        "https://dash.cloudflare.com/profile/api-tokens"
                    )
        if result.fallback_active:
            steps.append(
                "FALLBACK ACTIVE: System running in local-only mode. "
                "External deployments paused until gates resolve."
            )
        return steps
