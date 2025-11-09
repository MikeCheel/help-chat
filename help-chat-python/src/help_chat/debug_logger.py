"""
Debug Logger Module

Provides optional debug logging functionality to program_debug.log.
"""

import os
from datetime import datetime
from typing import Optional


class DebugLogger:
    """Simple debug logger that writes to program_debug.log when enabled."""

    _enabled: bool = False
    _log_path: Optional[str] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls, enabled: bool, log_directory: str) -> None:
        """
        Initialize the debug logger.

        Args:
            enabled: Whether debug logging is enabled
            log_directory: Directory where the log file should live
        """
        cls._enabled = enabled
        cls._initialized = True

        if enabled:
            try:
                os.makedirs(log_directory, exist_ok=True)
                cls._log_path = os.path.join(log_directory, "program_debug.log")
                with open(cls._log_path, "w", encoding="utf-8") as f:
                    f.write(f"=== Debug Log Started: {datetime.utcnow().isoformat()}Z ===\n")
            except Exception:
                # If we can't write the log, silently disable it
                cls._enabled = False
                cls._log_path = None

    @classmethod
    def log(cls, message: str) -> None:
        """
        Write a message to the debug log if enabled.

        Args:
            message: The message to log
        """
        if not cls._enabled or not cls._log_path:
            return

        try:
            timestamp = datetime.utcnow().isoformat()
            with open(cls._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}Z] {message}\n")
        except Exception:
            # Silently fail if we can't write to log
            pass

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if debug logging is enabled."""
        return cls._enabled
