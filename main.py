#!/usr/bin/env python3
"""CLI entry: python main.py [--demo-once]"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from edge_remit.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
