"""Pytest configuration for monitoring tests — isolates state files from real user data."""
import pytest


@pytest.fixture(autouse=True)
def isolate_state_files(tmp_path):
    """Redirect both state files to tmp_path so real user data isn't read."""
    from unittest.mock import patch
    cal_fake = tmp_path / ".nexus" / "calibration_state.json"
    dream_fake = tmp_path / ".nexus_dream" / "dream_state.json"
    patches = [
        patch("nexus_os.monitoring.calibrated_hallucination_detector.CALIBRATION_STATE_FILE",
              new=cal_fake),
        patch("nexus_os.vault.dream_cycle.DREAM_STATE_FILE",
              new=dream_fake),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()
