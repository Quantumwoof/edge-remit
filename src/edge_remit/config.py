"""Runtime configuration. Demo OpenVINO path is the default."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]

load_dotenv(PROJECT_ROOT / ".env")


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


SPEECHMATICS_API_KEY = os.getenv("SPEECHMATICS_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()  # optional, unused

_live_explicit = os.getenv("LIVE_OPENVINO")
LIVE_OPENVINO = _truthy(_live_explicit) if _live_explicit is not None else False

_demo_explicit = os.getenv("DEMO_MODE")
if _demo_explicit is not None and _demo_explicit.strip() != "":
    DEMO_MODE = _truthy(_demo_explicit)
else:
    # Default to demo unless LIVE_OPENVINO is explicitly on.
    DEMO_MODE = not LIVE_OPENVINO

# If both flags conflict, LIVE wins only when OpenVINO can import.
if LIVE_OPENVINO and DEMO_MODE:
    DEMO_MODE = False
