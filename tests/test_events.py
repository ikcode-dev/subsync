"""Tests for the stage events module."""

import subprocess
import sys


def test_importing_events_loads_no_ml_stack() -> None:
    """The CLI imports events on its fast path, so they must stay light."""
    code = (
        "import sys\n"
        "import subsync.events\n"
        "heavy = ('torch', 'whisper', 'yt_dlp', 'subsync.pipeline')\n"
        "print([m for m in heavy if m in sys.modules])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "[]"
