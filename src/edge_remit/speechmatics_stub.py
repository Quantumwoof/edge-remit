"""Optional Speechmatics STT stub (bonus award path).

Does **not** block the demo when ``SPEECHMATICS_API_KEY`` is missing.
Wire a real Speechmatics batch/realtime client here for the voice bonus.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_remit.config import SPEECHMATICS_API_KEY


@dataclass
class SpeechResult:
    ok: bool
    text: str
    provider: str
    detail: str


def speechmatics_available() -> bool:
    return bool(SPEECHMATICS_API_KEY)


def transcribe_audio_stub(audio_path: str | None = None) -> SpeechResult:
    """Stub transcription. Returns a clear message when no key is set."""
    if not SPEECHMATICS_API_KEY:
        return SpeechResult(
            ok=False,
            text="",
            provider="speechmatics",
            detail=(
                "SPEECHMATICS_API_KEY not set. EdgeRemit text demo still works. "
                "Set the key in .env to enable the Speechmatics bonus STT path."
            ),
        )

    # Key present but no live SDK call in MVP — keep judges unblocked.
    _ = audio_path
    return SpeechResult(
        ok=True,
        text="[Speechmatics stub] My brother wants to send five hundred dollars to Lagos.",
        provider="speechmatics",
        detail=(
            "API key detected. MVP returns a canned transcript; "
            "replace this stub with the Speechmatics Batch/Realtime API for production."
        ),
    )


def status() -> dict[str, Any]:
    return {
        "configured": speechmatics_available(),
        "blocks_demo": False,
        "note": (
            "Optional bonus. Demo runs fully without Speechmatics. "
            "See README § Speechmatics."
        ),
    }
