"""Hand-built Whisper transcripts stored as JSON: a test helper.

Each file in ``tests/fixtures/transcripts/`` mirrors ``TranscriptionResult``:
``language``, ``duration`` and ``segments``, where each segment has ``id``,
``start``, ``end``, ``text`` and ``words`` (each with ``word``, ``start``,
``end``, times in seconds). Word texts keep Whisper's leading spaces and
attached punctuation. An optional top-level ``description`` says what the
transcript is for and is not part of the result.

Import it from any test as ``transcript_fixtures`` (pytest puts ``tests`` on
the path). The processor tests run every fixture; the integration tests use
them as the stand-in transcriber's output.
"""

import json
from pathlib import Path
from typing import Any

from subsync.models import TranscriptionResult, TranscriptionSegment, Word

TRANSCRIPTS_DIR = Path(__file__).parent / "fixtures" / "transcripts"

URL = "github.com/ikcode-dev/subsync/blob/main/README.md"
"""The 49-character URL used for the long-word rule (R12)."""

EPISODE_WITH_URL = "english_episode_with_url"
"""A realistic multi-segment English episode (38.6 s of speech in 41 s).

It contains ``URL`` once, as a single word, so the processor reports exactly
one ``long_word`` flag and no ``short`` flag.
"""

NO_SEGMENTS = "no_segments"
"""A transcript with no segments at all: Whisper found no speech."""

BLANK_SEGMENTS = "blank_segments"
"""Only empty or whitespace-only segments."""

UNICODE_AND_EMOJI = "unicode_and_emoji"
"""Polish diacritics in both cases, and emoji including a ZWJ sequence."""

WHISPER_QUIRKS = "whisper_quirks"
"""Overlapping segments, zero-length, identical and backwards word times,
a segment without words, an empty segment, and stray whitespace in words."""


def transcript_names() -> list[str]:
    """Return the names of every stored transcript, sorted.

    Returns:
        File stems of the JSON files in ``TRANSCRIPTS_DIR``.
    """
    return sorted(path.stem for path in TRANSCRIPTS_DIR.glob("*.json"))


def transcript_from_dict(data: dict[str, Any]) -> TranscriptionResult:
    """Build a ``TranscriptionResult`` from its JSON form.

    Args:
        data: A mapping with ``language``, ``duration`` and ``segments``.

    Returns:
        The transcription result the mapping describes.
    """
    segments = [
        TranscriptionSegment(
            id=segment["id"],
            start=segment["start"],
            end=segment["end"],
            text=segment["text"],
            words=[
                Word(word=word["word"], start=word["start"], end=word["end"])
                for word in segment.get("words", [])
            ],
        )
        for segment in data["segments"]
    ]
    return TranscriptionResult(
        language=data["language"], duration=data["duration"], segments=segments
    )


def load_transcript(name: str) -> TranscriptionResult:
    """Load a stored transcript by name.

    Args:
        name: The file stem, such as ``EPISODE_WITH_URL``.

    Returns:
        A fresh ``TranscriptionResult`` on every call, safe to modify.

    Raises:
        FileNotFoundError: If no transcript has that name.
    """
    path = TRANSCRIPTS_DIR / f"{name}.json"
    return transcript_from_dict(json.loads(path.read_text(encoding="utf-8")))
