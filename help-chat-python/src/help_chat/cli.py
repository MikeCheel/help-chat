"""
Command line bridge for Help Chat operations used by the .NET wrapper.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from help_chat.doc_indexer import DocIndexer
from help_chat.keyring import KeyRing
from help_chat.llm import HelpChat


def _load_config(config_file: Path) -> Dict[str, Union[str, int]]:
    try:
        config_json = config_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Unable to read configuration file: {exc}") from exc

    try:
        return KeyRing.build(config_json)
    except Exception as exc:  # noqa: BLE001 - propagate exact failure details
        raise ValueError(str(exc)) from exc


def _load_prompt(prompt_file: Path) -> str:
    try:
        return prompt_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Unable to read prompt file: {exc}") from exc


def _success(data: Optional[Any] = None) -> int:
    payload = {"status": "ok"}
    if data is not None:
        payload["data"] = data
    print(json.dumps(payload))
    return 0


def _error(message: str) -> int:
    print(json.dumps({"status": "error", "message": message}))
    return 1


def _handle_validate(config_file: Path) -> int:
    config = _load_config(config_file)
    return _success(config)


def _handle_reindex(config_file: Path) -> int:
    config = _load_config(config_file)
    indexer = DocIndexer()

    def progress_callback(file_path: str) -> None:
        """Print progress message for each file being processed."""
        import sys
        progress_msg = json.dumps({"status": "progress", "file": file_path})
        print(progress_msg, flush=True)
        sys.stdout.flush()  # Extra flush to ensure immediate output

    indexer.reindex(config=config, progress_callback=progress_callback)
    return _success({"value": "reindexed"})


def _handle_make_request(config_file: Path, prompt_file: Path) -> int:
    config = _load_config(config_file)
    prompt = _load_prompt(prompt_file)
    chat = HelpChat(config)
    # Disable streaming for CLI bridge to maintain compatibility with .NET wrapper
    # The response will still benefit from optimized parameters (temperature, max_tokens, etc.)
    response = chat.make_request(prompt, stream=False)
    return _success(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Help Chat Python CLI bridge")
    parser.add_argument("--command", required=True, choices=["validate", "reindex", "make-request"])
    parser.add_argument("--config-file", required=True, type=Path)
    parser.add_argument("--prompt-file", type=Path)

    args = parser.parse_args()

    try:
        if args.command == "validate":
            return _handle_validate(args.config_file)
        if args.command == "reindex":
            return _handle_reindex(args.config_file)
        if args.command == "make-request":
            if args.prompt_file is None:
                raise ValueError("make-request requires --prompt-file argument.")
            return _handle_make_request(args.config_file, args.prompt_file)

        raise ValueError(f"Unsupported command: {args.command}")
    except Exception as exc:  # noqa: BLE001 - surface to caller
        return _error(f"{exc.__class__.__name__}: {exc}")


if __name__ == "__main__":
    sys.exit(main())
