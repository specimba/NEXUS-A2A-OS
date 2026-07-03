"""Durable token and rate governor shared by NEXUS provider call paths."""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class BudgetDenied(RuntimeError):
    """Raised when a provider request violates a durable budget gate."""


DEFAULT_POLICIES: dict[str, dict[str, Any]] = {
    "longcat": {
        "allocation_tokens": 65_000_000,
        "target_tokens": 58_500_000,
        "reserve_tokens": 6_500_000,
        "requires_verification": True,
        "initial_rpm": 6,
        "max_rpm": 12,
        "concurrency_limit": 1,
        "cooldown_seconds": 1_200,
    },
    "internai": {
        "allocation_tokens": 90_000_000,
        "target_tokens": 81_000_000,
        "reserve_tokens": 9_000_000,
        "requires_verification": True,
        "initial_rpm": 20,
        "max_rpm": 20,
        "concurrency_limit": 1,
        "cooldown_seconds": 1_200,
    },
    "nvidia": {
        "allocation_tokens": None,
        "target_tokens": None,
        "reserve_tokens": 0,
        "requires_verification": False,
        "initial_rpm": 8,
        "max_rpm": 8,
        "concurrency_limit": 1,
        "cooldown_seconds": 3_600,
    },
}


class ProviderBudgetLedger:
    """Transaction-safe provider budget, concurrency, and cooldown ledger."""

    PROBE_REQUEST_LIMIT = 2
    PROBE_TOKEN_LIMIT = 16_000
    RESERVATION_TTL_SECONDS = 3_600

    def __init__(self, path: str | Path | None = None) -> None:
        configured = os.environ.get("NEXUS_PROVIDER_BUDGET_DB")
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".nexus"))
        self.path = Path(path or configured or local / "NEXUS" / "modelrelay" / "provider_budget.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS provider_budgets (
                    provider TEXT PRIMARY KEY,
                    allocation_tokens INTEGER,
                    target_tokens INTEGER,
                    reserve_tokens INTEGER NOT NULL,
                    requires_verification INTEGER NOT NULL,
                    verified_balance_tokens INTEGER,
                    verified_at REAL,
                    reset_at REAL,
                    expires_at REAL,
                    verification_source TEXT,
                    initial_rpm INTEGER NOT NULL,
                    current_rpm INTEGER NOT NULL,
                    max_rpm INTEGER NOT NULL,
                    concurrency_limit INTEGER NOT NULL,
                    cooldown_seconds INTEGER NOT NULL,
                    cooldown_until REAL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    disabled_reason TEXT,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS provider_requests (
                    request_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL REFERENCES provider_budgets(provider),
                    estimated_tokens INTEGER NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    state TEXT NOT NULL,
                    probe INTEGER NOT NULL DEFAULT 0,
                    corpus INTEGER NOT NULL DEFAULT 0,
                    requested_model TEXT,
                    resolved_model TEXT,
                    provider_echo TEXT,
                    fallback_reason TEXT,
                    thinking_mode INTEGER,
                    latency_ms REAL,
                    status_code INTEGER,
                    failure_reason TEXT,
                    reserved_at REAL NOT NULL,
                    completed_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_provider_requests_window
                    ON provider_requests(provider, reserved_at, state);
                CREATE TABLE IF NOT EXISTS provider_budget_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at REAL NOT NULL,
                    details_json TEXT NOT NULL
                );
                """
            )
            now = time.time()
            for provider, policy in DEFAULT_POLICIES.items():
                connection.execute(
                    """
                    INSERT OR IGNORE INTO provider_budgets (
                        provider, allocation_tokens, target_tokens, reserve_tokens,
                        requires_verification, initial_rpm, current_rpm, max_rpm,
                        concurrency_limit, cooldown_seconds, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        provider,
                        policy["allocation_tokens"],
                        policy["target_tokens"],
                        policy["reserve_tokens"],
                        int(policy["requires_verification"]),
                        policy["initial_rpm"],
                        policy["initial_rpm"],
                        policy["max_rpm"],
                        policy["concurrency_limit"],
                        policy["cooldown_seconds"],
                        now,
                    ),
                )

    @staticmethod
    def _timestamp(value: str | float | int | None) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        from datetime import datetime

        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()

    def verify_balance(
        self,
        provider: str,
        remaining_tokens: int,
        *,
        source: str,
        reset_at: str | float | None = None,
        expires_at: str | float | None = None,
    ) -> dict[str, Any]:
        reset_ts = self._timestamp(reset_at)
        expiry_ts = self._timestamp(expires_at)
        if reset_ts is None and expiry_ts is None:
            raise ValueError("reset_at or expires_at is required for quota verification")
        if remaining_tokens < 0:
            raise ValueError("remaining_tokens must be non-negative")
        now = time.time()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT allocation_tokens FROM provider_budgets WHERE provider = ?", (provider,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown provider: {provider}")
            allocation = row["allocation_tokens"]
            if allocation is not None and remaining_tokens > allocation:
                raise ValueError("remaining_tokens exceeds configured allocation")
            connection.execute(
                """
                UPDATE provider_budgets
                SET verified_balance_tokens = ?, verified_at = ?, reset_at = ?,
                    expires_at = ?, verification_source = ?, enabled = 1,
                    disabled_reason = NULL, updated_at = ?
                WHERE provider = ?
                """,
                (remaining_tokens, now, reset_ts, expiry_ts, source, now, provider),
            )
            self._event(connection, provider, "balance_verified", {"source": source})
        return self.status(provider)

    def reserve(
        self,
        request_id: str,
        provider: str,
        estimated_tokens: int,
        *,
        probe: bool = False,
        corpus: bool = False,
        requested_model: str | None = None,
        thinking_mode: bool | None = None,
        emergency_override: bool = False,
    ) -> dict[str, Any]:
        if not request_id:
            raise ValueError("request_id is required")
        if estimated_tokens <= 0:
            raise ValueError("estimated_tokens must be positive")
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._expire_stale(connection, now)
                existing = connection.execute(
                    "SELECT * FROM provider_requests WHERE request_id = ?", (request_id,)
                ).fetchone()
                if existing is not None:
                    connection.commit()
                    return dict(existing)
                budget = connection.execute(
                    "SELECT * FROM provider_budgets WHERE provider = ?", (provider,)
                ).fetchone()
                if budget is None:
                    raise BudgetDenied(f"unknown provider: {provider}")
                if not budget["enabled"]:
                    raise BudgetDenied(f"provider disabled: {budget['disabled_reason'] or 'policy'}")
                if budget["cooldown_until"] and budget["cooldown_until"] > now:
                    raise BudgetDenied("provider cooldown is active")
                deadline = budget["expires_at"] or budget["reset_at"]
                if budget["requires_verification"] and deadline and deadline <= now:
                    raise BudgetDenied("verified quota window has expired")
                self._maybe_ramp(connection, budget, now)
                budget = connection.execute(
                    "SELECT * FROM provider_budgets WHERE provider = ?", (provider,)
                ).fetchone()

                active = connection.execute(
                    "SELECT COUNT(*) FROM provider_requests WHERE provider = ? AND state = 'reserved'",
                    (provider,),
                ).fetchone()[0]
                if active >= budget["concurrency_limit"]:
                    raise BudgetDenied("provider concurrency limit reached")
                if corpus:
                    corpus_active = connection.execute(
                        "SELECT COUNT(*) FROM provider_requests WHERE corpus = 1 AND state = 'reserved'"
                    ).fetchone()[0]
                    if corpus_active:
                        raise BudgetDenied("a corpus task is already active")

                rpm_count = connection.execute(
                    "SELECT COUNT(*) FROM provider_requests WHERE provider = ? AND reserved_at >= ?",
                    (provider, now - 60),
                ).fetchone()[0]
                if rpm_count >= budget["current_rpm"]:
                    raise BudgetDenied("provider RPM limit reached")

                if budget["requires_verification"] and budget["verified_at"] is None:
                    if not probe:
                        raise BudgetDenied("provider balance is not verified")
                    probe_stats = connection.execute(
                        """
                        SELECT COUNT(*), COALESCE(SUM(estimated_tokens), 0)
                        FROM provider_requests WHERE provider = ? AND probe = 1
                        """,
                        (provider,),
                    ).fetchone()
                    if probe_stats[0] >= self.PROBE_REQUEST_LIMIT:
                        raise BudgetDenied("pre-verification probe limit reached")
                    if probe_stats[1] + estimated_tokens > self.PROBE_TOKEN_LIMIT:
                        raise BudgetDenied("pre-verification probe token limit reached")
                elif budget["requires_verification"] and not emergency_override:
                    remaining = self._target_remaining(connection, budget, now, include_reserved=True)
                    if estimated_tokens > remaining:
                        raise BudgetDenied("protected reserve would be consumed")

                connection.execute(
                    """
                    INSERT INTO provider_requests (
                        request_id, provider, estimated_tokens, state, probe, corpus,
                        requested_model, thinking_mode, reserved_at
                    ) VALUES (?, ?, ?, 'reserved', ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        provider,
                        estimated_tokens,
                        int(probe),
                        int(corpus),
                        requested_model,
                        None if thinking_mode is None else int(thinking_mode),
                        now,
                    ),
                )
                self._event(connection, provider, "reserved", {"request_id": request_id})
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {"request_id": request_id, "provider": provider, "state": "reserved"}

    def complete(
        self,
        request_id: str,
        *,
        input_tokens: int | None,
        output_tokens: int | None,
        resolved_model: str | None = None,
        provider_echo: str | None = None,
        fallback_reason: str | None = None,
        latency_ms: float | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute(
                "SELECT * FROM provider_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
            if request is None:
                connection.rollback()
                raise KeyError(f"unknown request_id: {request_id}")
            budget = connection.execute(
                "SELECT requires_verification FROM provider_budgets WHERE provider = ?",
                (request["provider"],),
            ).fetchone()
            if budget["requires_verification"] and (input_tokens is None or output_tokens is None):
                connection.execute(
                    "UPDATE provider_requests SET state = 'failed', failure_reason = ?, completed_at = ? WHERE request_id = ?",
                    ("missing_usage_metadata", now, request_id),
                )
                connection.commit()
                raise BudgetDenied("usage metadata is required for budgeted providers")
            input_value = int(input_tokens or 0)
            output_value = int(output_tokens or 0)
            connection.execute(
                """
                UPDATE provider_requests
                SET state = 'completed', input_tokens = ?, output_tokens = ?,
                    resolved_model = ?, provider_echo = ?, fallback_reason = ?,
                    latency_ms = ?, status_code = 200, completed_at = ?
                WHERE request_id = ?
                """,
                (
                    input_value,
                    output_value,
                    resolved_model,
                    provider_echo,
                    fallback_reason,
                    latency_ms,
                    now,
                    request_id,
                ),
            )
            self._event(connection, request["provider"], "completed", {"request_id": request_id})
            connection.commit()
        return {"request_id": request_id, "state": "completed", "total_tokens": input_value + output_value}

    def fail(
        self,
        request_id: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute(
                "SELECT provider FROM provider_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
            if request is None:
                connection.rollback()
                raise KeyError(f"unknown request_id: {request_id}")
            provider = request["provider"]
            connection.execute(
                """
                UPDATE provider_requests SET state = 'failed', status_code = ?,
                    failure_reason = ?, completed_at = ? WHERE request_id = ?
                """,
                (status_code, reason, now, request_id),
            )
            if status_code == 429:
                budget = connection.execute(
                    "SELECT * FROM provider_budgets WHERE provider = ?", (provider,)
                ).fetchone()
                cooldown = max(float(retry_after_seconds or 0), float(budget["cooldown_seconds"]))
                new_rpm = budget["current_rpm"]
                if provider == "internai":
                    new_rpm = 10
                elif provider == "longcat":
                    new_rpm = max(1, budget["current_rpm"] // 2)
                connection.execute(
                    "UPDATE provider_budgets SET cooldown_until = ?, current_rpm = ?, updated_at = ? WHERE provider = ?",
                    (now + cooldown, new_rpm, now, provider),
                )
                self._event(connection, provider, "rate_limited", {"status_code": 429})
                count = connection.execute(
                    """
                    SELECT COUNT(*) FROM provider_budget_events
                    WHERE provider = ? AND event_type = 'rate_limited' AND occurred_at >= ?
                    """,
                    (provider, now - 86_400),
                ).fetchone()[0]
                if count >= 3:
                    connection.execute(
                        "UPDATE provider_budgets SET enabled = 0, disabled_reason = 'rate_limit_quarantine' WHERE provider = ?",
                        (provider,),
                    )
            elif status_code in (402, 403) or (reason and "unsupported model" in reason.lower()):
                connection.execute(
                    "UPDATE provider_budgets SET enabled = 0, disabled_reason = ?, updated_at = ? WHERE provider = ?",
                    (reason or f"http_{status_code}", now, provider),
                )
            elif status_code is None or status_code >= 500:
                recent = connection.execute(
                    """
                    SELECT COUNT(*) FROM provider_budget_events
                    WHERE provider = ? AND event_type = 'transient_failure' AND occurred_at >= ?
                    """,
                    (provider, now - 3_600),
                ).fetchone()[0]
                backoff = (60, 120, 300, 900)[min(recent, 3)]
                connection.execute(
                    "UPDATE provider_budgets SET cooldown_until = ?, updated_at = ? WHERE provider = ?",
                    (now + backoff, now, provider),
                )
                self._event(connection, provider, "transient_failure", {"status_code": status_code, "reason": reason})
            else:
                self._event(connection, provider, "failed", {"status_code": status_code, "reason": reason})
            connection.commit()
        return {"request_id": request_id, "state": "failed", "status_code": status_code}

    def clear_cooldown(self, provider: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE provider_budgets SET cooldown_until = NULL, updated_at = ? WHERE provider = ?",
                (time.time(), provider),
            )

    def status(self, provider: str) -> dict[str, Any]:
        now = time.time()
        with self._connect() as connection:
            budget = connection.execute(
                "SELECT * FROM provider_budgets WHERE provider = ?", (provider,)
            ).fetchone()
            if budget is None:
                raise KeyError(f"unknown provider: {provider}")
            active = connection.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(estimated_tokens), 0)
                FROM provider_requests WHERE provider = ? AND state = 'reserved'
                """,
                (provider,),
            ).fetchone()
            completed = self._completed_tokens(connection, provider, budget["verified_at"])
            external = self._external_consumed(budget)
            consumed = external + completed
            target_remaining = None
            if budget["target_tokens"] is not None:
                target_remaining = max(0, budget["target_tokens"] - consumed - active[1])
            deadline = budget["expires_at"] or budget["reset_at"]
            daily_budget = None
            if deadline and target_remaining is not None:
                days = max(1, math.ceil((deadline - now) / 86_400))
                daily_budget = math.ceil(target_remaining / days)
            return {
                "provider": provider,
                "allocation_tokens": budget["allocation_tokens"],
                "target_tokens": budget["target_tokens"],
                "reserve_tokens": budget["reserve_tokens"],
                "verified_balance_tokens": budget["verified_balance_tokens"],
                "balance_verified": budget["verified_at"] is not None or not budget["requires_verification"],
                "reset_at": budget["reset_at"],
                "expires_at": budget["expires_at"],
                "verification_source": budget["verification_source"],
                "consumed_tokens": consumed,
                "local_consumed_tokens": completed,
                "active_reservations": active[0],
                "active_reserved_tokens": active[1],
                "target_remaining_tokens": target_remaining,
                "daily_budget_tokens": daily_budget,
                "current_rpm": budget["current_rpm"],
                "max_rpm": budget["max_rpm"],
                "concurrency_limit": budget["concurrency_limit"],
                "cooldown_remaining_seconds": max(0, round((budget["cooldown_until"] or 0) - now)),
                "enabled": bool(budget["enabled"]),
                "disabled_reason": budget["disabled_reason"],
            }

    def all_status(self) -> dict[str, Any]:
        with self._connect() as connection:
            providers = [row[0] for row in connection.execute("SELECT provider FROM provider_budgets ORDER BY provider")]
        return {"providers": {provider: self.status(provider) for provider in providers}}

    def _target_remaining(self, connection: sqlite3.Connection, budget: sqlite3.Row, now: float, *, include_reserved: bool) -> int:
        consumed = self._external_consumed(budget) + self._completed_tokens(
            connection, budget["provider"], budget["verified_at"]
        )
        reserved = 0
        if include_reserved:
            reserved = connection.execute(
                "SELECT COALESCE(SUM(estimated_tokens), 0) FROM provider_requests WHERE provider = ? AND state = 'reserved'",
                (budget["provider"],),
            ).fetchone()[0]
        return max(0, int(budget["target_tokens"] or 0) - consumed - reserved)

    @staticmethod
    def _external_consumed(budget: sqlite3.Row) -> int:
        if budget["allocation_tokens"] is None or budget["verified_balance_tokens"] is None:
            return 0
        return max(0, budget["allocation_tokens"] - budget["verified_balance_tokens"])

    @staticmethod
    def _completed_tokens(connection: sqlite3.Connection, provider: str, since: float | None) -> int:
        if since is None:
            return 0
        return connection.execute(
            """
            SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0)
            FROM provider_requests
            WHERE provider = ? AND state = 'completed' AND completed_at >= ?
            """,
            (provider, since),
        ).fetchone()[0]

    @staticmethod
    def _maybe_ramp(connection: sqlite3.Connection, budget: sqlite3.Row, now: float) -> None:
        if budget["provider"] != "longcat" or budget["current_rpm"] >= budget["max_rpm"]:
            return
        if budget["verified_at"] is None or now - budget["verified_at"] < 6 * 3_600:
            return
        recent_limits = connection.execute(
            """
            SELECT COUNT(*) FROM provider_budget_events
            WHERE provider = 'longcat' AND event_type = 'rate_limited' AND occurred_at >= ?
            """,
            (now - 6 * 3_600,),
        ).fetchone()[0]
        if recent_limits == 0:
            connection.execute(
                "UPDATE provider_budgets SET current_rpm = max_rpm, updated_at = ? WHERE provider = 'longcat'",
                (now,),
            )

    def _expire_stale(self, connection: sqlite3.Connection, now: float) -> None:
        connection.execute(
            """
            UPDATE provider_requests
            SET state = 'failed', failure_reason = 'stale_reservation', completed_at = ?
            WHERE state = 'reserved' AND reserved_at < ?
            """,
            (now, now - self.RESERVATION_TTL_SECONDS),
        )

    @staticmethod
    def _event(connection: sqlite3.Connection, provider: str, event_type: str, details: dict[str, Any]) -> None:
        connection.execute(
            "INSERT INTO provider_budget_events (provider, event_type, occurred_at, details_json) VALUES (?, ?, ?, ?)",
            (provider, event_type, time.time(), json.dumps(details, sort_keys=True)),
        )
