"""Lane conversation policy tests."""

from nexus_os.nexusclaw import lane_conversation as lc


def test_grok_nudge_paths_exist_names():
    assert "continue" in lc.GROK_NUDGE_PROMPTS
    assert lc.GROK_NUDGE_PROMPTS["continue"].endswith("nudge_continue.md")


def test_zo_wait_default():
    assert lc.ZO_DEFAULT_IDLE_WAIT_SEC >= 600