from types import SimpleNamespace

import pytest

from bibliosleuth_ai import credentials


def test_linux_secret_service_uses_stdin_not_argv(monkeypatch):
    captured = {}
    monkeypatch.setattr(credentials.sys, "platform", "linux")
    monkeypatch.setattr(credentials.os, "name", "posix")
    monkeypatch.setattr(credentials.shutil, "which", lambda name: "/usr/bin/secret-tool")
    def fake_run(args, input_text=None):
        captured["args"] = args; captured["input"] = input_text
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(credentials, "_run", fake_run)
    credentials.save("sk-test-secret")
    assert "sk-test-secret" not in captured["args"]
    assert captured["input"] == "sk-test-secret\n"


def test_providers_use_separate_vault_identities(monkeypatch):
    calls = []
    monkeypatch.setattr(credentials.sys, "platform", "linux")
    monkeypatch.setattr(credentials.os, "name", "posix")
    monkeypatch.setattr(credentials.shutil, "which", lambda name: "/usr/bin/secret-tool")
    monkeypatch.setattr(credentials, "_run", lambda args, input_text=None: (calls.append((args, input_text)) or SimpleNamespace(returncode=0, stdout="", stderr="")))
    credentials.save("openai-secret", "openai")
    credentials.save("anthropic-secret", "anthropic")
    credentials.save("ollama-secret", "ollama")
    credentials.save("lmstudio-secret", "lmstudio")
    assert calls[0][0][-3:] != calls[1][0][-3:]
    assert len({tuple(call[0][-4:]) for call in calls}) == 4
    assert "openai-secret" not in calls[1][1]


def test_unknown_credential_provider_fails_closed():
    with pytest.raises(credentials.CredentialStoreError, match="Unknown"):
        credentials.load("unexpected-provider")
