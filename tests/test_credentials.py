from types import SimpleNamespace

from calibre_ai_plugin import credentials


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
