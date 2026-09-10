from __future__ import annotations

import vaultsafe_client.clipboard as clipboard


def test_uses_first_available_tool(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> None:
        calls.append(list(cmd))
        return None

    monkeypatch.setattr(clipboard.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)
    assert clipboard.copy_to_clipboard("s3cret") == "wl-copy"
    assert calls == [["wl-copy"]]


def test_falls_to_second_tool(monkeypatch):
    which_calls: list[str] = []

    def fake_which(name: str):
        which_calls.append(name)
        return None if name == "wl-copy" else f"/usr/bin/{name}"

    monkeypatch.setattr(clipboard.shutil, "which", fake_which)
    monkeypatch.setattr(clipboard.subprocess, "run", lambda cmd, **kwargs: None)
    assert clipboard.copy_to_clipboard("x") == "xclip"
    assert which_calls == ["wl-copy", "xclip"]


def test_returns_none_when_no_tool(monkeypatch):
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: None)
    assert clipboard.copy_to_clipboard("x") is None


def test_feeds_text_via_stdin(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> None:
        captured["input"] = kwargs.get("input")
        return None

    monkeypatch.setattr(clipboard.shutil, "which", lambda name: "/usr/bin/pbcopy")
    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)
    clipboard.copy_to_clipboard("s3cret")
    assert captured["input"] == b"s3cret"
