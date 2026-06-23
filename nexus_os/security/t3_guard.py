import os
import hashlib
import time
import logging
from typing import Dict, Any, Tuple, Optional
from nexus_os.db.manager import DatabaseManager, DBConfig

logger = logging.getLogger(__name__)


class T3CrossSessionGuard:
    """
    T3 Temporal Cross-Session Guard.
    Detects cron prompting accumulation, trust inflation via benign loops,
    and exfiltration disguised in deep automated context.
    """

    def __init__(self, db: Optional[DatabaseManager] = None, system_threshold: int = 5, drift_window_seconds: int = 3600):
        if db is None:
            config = DBConfig(
                db_path=os.environ.get("NEXUS_GOVERNANCE_DB") or "nexus_governance.db",
                passphrase="",
                encrypted=False
            )
            self.db = DatabaseManager(config)
        else:
            self.db = db
        self.system_threshold = system_threshold
        self.drift_window_seconds = drift_window_seconds
        self.setup_schema()

    def setup_schema(self):
        """Create the t3_session_prompts table if it does not exist."""
        try:
            conn = self.db.get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS t3_session_prompts (
                    session_id TEXT,
                    prompt_hash TEXT,
                    timestamp REAL,
                    is_system_initiated INTEGER,
                    prompt_length INTEGER
                )
            """)
            conn.commit()
        except Exception as e:
            logger.error("T3Guard: Failed to create t3_session_prompts table: %s", e)

    def log_prompt(self, session_id: str, prompt: str, is_system: bool = False):
        """Log prompt hash and metadata for temporal analysis."""
        if not session_id or not prompt:
            return
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        timestamp = time.time()
        is_sys_val = 1 if is_system else 0
        prompt_len = len(prompt)

        try:
            conn = self.db.get_connection()
            conn.execute(
                "INSERT INTO t3_session_prompts (session_id, prompt_hash, timestamp, is_system_initiated, prompt_length) VALUES (?, ?, ?, ?, ?)",
                (session_id, prompt_hash, timestamp, is_sys_val, prompt_len)
            )
            conn.commit()
        except Exception as e:
            logger.error("T3Guard: Failed to log prompt to DB: %s", e)

    def check_drift_and_inflation(self, session_id: str, current_prompt: str) -> Tuple[bool, float, str]:
        """
        Analyze current session prompt pattern.
        Returns:
            (should_escalate: bool, anomaly_score: float, reason: str)
        """
        if not session_id or not current_prompt:
            return False, 0.0, "OK"

        now = time.time()
        start_window = now - self.drift_window_seconds

        try:
            conn = self.db.get_connection()
            cursor = conn.execute(
                "SELECT is_system_initiated, timestamp FROM t3_session_prompts WHERE session_id = ? AND timestamp >= ? ORDER BY timestamp DESC",
                (session_id, start_window)
            )
            rows = cursor.fetchall()
        except Exception as e:
            logger.error("T3Guard: Failed to retrieve prompt logs: %s", e)
            return False, 0.0, "DB error during check"

        if not rows:
            return False, 0.0, "OK"

        # Count system-initiated actions in the window
        system_prompts_count = sum(1 for r in rows if r[0] == 1)
        total_prompts = len(rows)

        # 1. Trust Inflation check:
        # If there is a large number of system-initiated prompts (e.g. cron monitoring)
        # the agent gets "contextualized" and might bypass normal checks.
        anomaly_score = 0.0
        reason = "OK"

        if system_prompts_count >= self.system_threshold:
            # High density of system/cron prompts
            anomaly_score = min(1.0, 0.2 * system_prompts_count)
            
            # If the current prompt is NOT system initiated, it could be a piggyback exfiltration!
            # i.e., user injection sneaking into a highly-trusted automated loop.
            is_current_sys = current_prompt.startswith("[SYSTEM]") or current_prompt.startswith("cron:")
            if not is_current_sys:
                anomaly_score = min(1.0, anomaly_score + 0.3)
                reason = (
                    f"T3-Anomaly: Non-system prompt piggybacking on high-density cron session "
                    f"({system_prompts_count} system prompts in window)"
                )
                return True, anomaly_score, reason

        # 2. Sequential prompt repetition check (denial of service or loops)
        if total_prompts >= 10:
            anomaly_score = max(anomaly_score, 1.0)
            reason = f"T3-Anomaly: Conversation starter spam/loop detected ({total_prompts} actions in window)"
            return True, anomaly_score, reason

        return False, anomaly_score, reason
