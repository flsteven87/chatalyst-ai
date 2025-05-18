import importlib
import os

import openai


def test_openai_chat_agent_uses_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    import app.config
    importlib.reload(app.config)
    import app.core.agents.openai_chat as chat_mod
    importlib.reload(chat_mod)

    called = {}

    def fake_create(**kwargs):
        called["api_key"] = openai.api_key
        return {"choices": [{"message": {"content": "hi"}}]}

    monkeypatch.setattr(openai.ChatCompletion, "create", fake_create)
    agent = chat_mod.OpenAIChatAgent()
    assert agent.api_key == "test-key"
    reply = agent.chat([{"role": "user", "content": "hi"}])
    assert reply == "hi"
    assert called["api_key"] == "test-key"
