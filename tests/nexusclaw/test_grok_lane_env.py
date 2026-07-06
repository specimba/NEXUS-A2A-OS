"""Tests for Grok lane env helpers."""

from nexus_os.nexusclaw import grok_lane_env as env


def test_default_grok_chat_url_contains_project_and_chat():
    url = env.DEFAULT_GROK_PROJECT_CHAT_URL
    assert "99253cca-2469-4454-8593-0f173b7f640f" in url
    assert "chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba" in url


def test_grok_project_url_env_override(monkeypatch):
    monkeypatch.setenv("NEXUS_GROK_PROJECT_CHAT_URL", "https://grok.com/project/test?chat=abc")
    assert env.grok_project_url() == "https://grok.com/project/test?chat=abc"


def test_zo_cdp_tunnel_url_default_port(monkeypatch):
    monkeypatch.delenv("NEXUS_ZO_CDP_TUNNEL_URL", raising=False)
    monkeypatch.delenv("NEXUS_GROK_CDP_PORT", raising=False)
    assert env.zo_cdp_tunnel_url() == "http://127.0.0.1:9224"


def test_zo_source_id_default():
    assert env.zo_source_id() == "zo-browser-lab"


def test_zo_chat_url_default():
    assert "specimba.zo.computer" in env.zo_chat_url()


def test_chatgpt_chat_url_default():
    assert "chatgpt.com" in env.chatgpt_chat_url()