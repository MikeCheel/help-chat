import json
import sys
from pathlib import Path

import pytest

from help_chat import cli


def _write_config(tmp_path: Path) -> Path:
    config_data = {
        "root_path": str(tmp_path / "docs"),
        "temp_path": str(tmp_path / "temp"),
        "api_path": "https://api.example.com/v1",
        "embeddings_path": str(tmp_path / "embeddings.db"),
        "api_key": "test-key",
        "supported_extensions": ".txt,.md",
    }
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "temp").mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")
    return config_file


def test_cli_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file = _write_config(tmp_path)

    monkeypatch.setenv("PYTHONPATH", "")
    monkeypatch.setattr(
        sys, "argv", ["help_chat.cli", "--command", "validate", "--config-file", str(config_file)]
    )

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["data"]["root_path"] == str(tmp_path / "docs")


def test_cli_reindex(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file = _write_config(tmp_path)
    called = {}

    class StubIndexer:
        def __init__(self) -> None:
            pass

        def reindex(self, config, progress_callback=None) -> None:
            called["config"] = dict(config)
            called["progress_callback"] = progress_callback

    monkeypatch.setattr(cli, "DocIndexer", StubIndexer)
    monkeypatch.setattr(
        sys, "argv", ["help_chat.cli", "--command", "reindex", "--config-file", str(config_file)]
    )

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["data"]["value"] == "reindexed"
    assert called["config"]["root_path"] == str(tmp_path / "docs")


def test_cli_make_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file = _write_config(tmp_path)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("What is the status?", encoding="utf-8")

    class StubChat:
        def __init__(self, config) -> None:
            self.config = dict(config)

        def make_request(self, prompt: str) -> str:
            return f"Echo: {prompt}"

    monkeypatch.setattr(cli, "HelpChat", StubChat)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "help_chat.cli",
            "--command",
            "make-request",
            "--config-file",
            str(config_file),
            "--prompt-file",
            str(prompt_file),
        ],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["data"] == "Echo: What is the status?"


def test_cli_missing_prompt_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file = _write_config(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "help_chat.cli",
            "--command",
            "make-request",
            "--config-file",
            str(config_file),
        ],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "error"
    assert "prompt-file" in payload["message"]


def test_cli_invalid_config_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_config = tmp_path / "missing.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "help_chat.cli",
            "--command",
            "validate",
            "--config-file",
            str(missing_config),
        ],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "error"
