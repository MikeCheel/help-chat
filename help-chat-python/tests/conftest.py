"""
Pytest configuration to expose the package modules without requiring an editable install.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if SRC_PATH.is_dir():
    src_string = str(SRC_PATH)
    if src_string not in sys.path:
        sys.path.insert(0, src_string)
