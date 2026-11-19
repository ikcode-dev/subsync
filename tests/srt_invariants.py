"""SRT invariant checker: a test helper, not production code.

Written from the requirements (R8, R9, R12, P2 and the E9 file format),
independently of the processor and the writer, so that tests can check any
SRT file SubSync writes. Import it from any test as ``srt_invariants``.

- ``parse_srt`` turns SRT bytes into cues and fails on bad grammar.
- ``check_cues`` lists rule violations in parsed cues.
- ``find_srt_violations`` adds the file-format checks to ``check_cues``;
  ``assert_valid_srt`` raises with all of them listed.
- ``short_cues`` lists cues under the minimum duration. Those are not
  violations: callers compare them with the report's ``short`` flags.
"""

import re
from dataclasses import dataclass

from subsync.models import ProcessingConfig

BOM = b"\xef\xbb\xbf"

_TIMING = re.compile(
    r"^(\d{2,}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2,}):([0-5]\d):([0-5]\d),(\d{3})$"
)


class SrtParseError(ValueError):
    """The SRT text does not follow the SRT grammar."""


@dataclass
class Cue:
    """One parsed SRT cue.

    Attributes:
        index: The cue number as written.
        start_ms: Start time in milliseconds.
        end_ms: End time in milliseconds.
        lines: Text lines, in order.
    """

    index: int
    start_ms: int
    end_ms: int
    lines: list[str]

    @property
    def duration_ms(self) -> int:
        """Duration in milliseconds."""
        return self.end_ms - self.start_ms


def _to_ms(hours: str, minutes: str, seconds: str, millis: str) -> int:
    """Convert timestamp parts to milliseconds."""
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)


def _normalize(data: bytes) -> str:
    """Decode UTF-8, drop a BOM and turn CRLF or CR into LF.

    The format checks in ``find_srt_violations`` report BOMs and CRs; parsing
    tolerates them so that the rule checks still run.
    """
    text = data.decode("utf-8")
    text = text.removeprefix("﻿")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_srt(data: bytes) -> list[Cue]:
    """Parse SRT bytes into cues.

    Blocks are separated by one or more blank lines. Each block is an index
    line, a ``HH:MM:SS,mmm --> HH:MM:SS,mmm`` timing line, then zero or more
    text lines.

    Args:
        data: The raw file content.

    Returns:
        The cues in file order.

    Raises:
        SrtParseError: On undecodable bytes, a bad index or a bad timing line.
    """
    try:
        text = _normalize(data)
    except UnicodeDecodeError as exc:
        raise SrtParseError(f"not valid UTF-8: {exc}") from exc

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    cues: list[Cue] = []
    for number, block in enumerate(blocks, start=1):
        index_line = block[0]
        if not index_line.isdigit():
            raise SrtParseError(
                f"block {number}: expected a cue number, got {index_line!r}"
            )
        if len(block) < 2:
            raise SrtParseError(f"block {number}: missing the timing line")
        match = _TIMING.match(block[1])
        if not match:
            raise SrtParseError(
                f"block {number}: bad timing line {block[1]!r}, "
                "expected 'HH:MM:SS,mmm --> HH:MM:SS,mmm'"
            )
        parts = match.groups()
        cues.append(
            Cue(
                index=int(index_line),
                start_ms=_to_ms(*parts[:4]),
                end_ms=_to_ms(*parts[4:]),
                lines=block[2:],
            )
        )
    return cues


def check_cues(cues: list[Cue], config: ProcessingConfig | None = None) -> list[str]:
    """List every rule violation in parsed cues.

    Checks: indices run 1..n in order; start < end; no overlap and no
    out-of-order cue; gaps of at least ``min_gap_ms``; durations of at most
    ``max_duration_ms``; 1 to ``max_lines`` lines; lines of at most
    ``max_chars_per_line`` characters unless the line is a single word.

    Args:
        cues: Parsed cues, in file order.
        config: Limits to check against; the Netflix defaults when omitted.

    Returns:
        One human-readable line per violation; empty when the cues are valid.
    """
    config = config or ProcessingConfig()
    violations: list[str] = []
    previous: Cue | None = None
    for position, cue in enumerate(cues, start=1):
        label = f"cue {position} (#{cue.index})"
        if cue.index != position:
            violations.append(f"{label}: index {cue.index}, expected {position}")
        if cue.start_ms >= cue.end_ms:
            violations.append(
                f"{label}: start {cue.start_ms} ms is not before end {cue.end_ms} ms"
            )
        elif cue.duration_ms > config.max_duration_ms:
            violations.append(
                f"{label}: duration {cue.duration_ms} ms is over "
                f"{config.max_duration_ms} ms"
            )
        if previous is not None:
            gap = cue.start_ms - previous.end_ms
            if gap < 0:
                violations.append(
                    f"{label}: overlaps or is out of order with the previous cue "
                    f"(starts {cue.start_ms} ms, previous ends {previous.end_ms} ms)"
                )
            elif gap < config.min_gap_ms:
                violations.append(
                    f"{label}: gap of {gap} ms is under {config.min_gap_ms} ms"
                )
        if not 1 <= len(cue.lines) <= config.max_lines:
            violations.append(
                f"{label}: {len(cue.lines)} lines, expected 1 to {config.max_lines}"
            )
        for line in cue.lines:
            single_word = len(line.split()) == 1 and line == line.strip()
            if len(line) > config.max_chars_per_line and not single_word:
                violations.append(
                    f"{label}: line of {len(line)} characters is over "
                    f"{config.max_chars_per_line}: {line!r}"
                )
        previous = cue
    return violations


def find_srt_violations(
    data: bytes, config: ProcessingConfig | None = None
) -> list[str]:
    """List every file-format and rule violation in SRT bytes.

    Format checks (E9): UTF-8, no BOM, no carriage returns, at least one cue,
    cues separated by exactly one blank line, a single trailing newline.
    Rule checks: everything in ``check_cues``.

    Args:
        data: The raw file content.
        config: Limits to check against; the Netflix defaults when omitted.

    Returns:
        One human-readable line per violation; empty when the file is valid.
    """
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"not valid UTF-8: {exc}"]

    violations: list[str] = []
    if data.startswith(BOM):
        violations.append("starts with a UTF-8 BOM")
    if b"\r" in data:
        violations.append("contains carriage returns (\\r); expected LF only")

    text = _normalize(data)
    if not text.endswith("\n"):
        violations.append("does not end with a newline")
    elif text.endswith("\n\n"):
        violations.append("ends with more than one newline")
    body = text.rstrip("\n")
    if body.startswith("\n"):
        violations.append("starts with a blank line")
    if "\n\n\n" in body:
        violations.append("cues separated by more than one blank line")
    if any(line != "" and line.strip() == "" for line in body.split("\n")):
        violations.append("contains a whitespace-only line")

    try:
        cues = parse_srt(data)
    except SrtParseError as exc:
        violations.append(f"parse error: {exc}")
        return violations
    if not cues:
        violations.append("contains no cues")
    violations.extend(check_cues(cues, config))
    return violations


def assert_valid_srt(data: bytes, config: ProcessingConfig | None = None) -> None:
    """Assert that SRT bytes meet the file format and every rule.

    Args:
        data: The raw file content.
        config: Limits to check against; the Netflix defaults when omitted.

    Raises:
        AssertionError: Listing every violation found.
    """
    violations = find_srt_violations(data, config)
    if violations:
        listed = "\n".join(f"  - {violation}" for violation in violations)
        raise AssertionError(f"invalid SRT ({len(violations)} violations):\n{listed}")


def short_cues(cues: list[Cue], config: ProcessingConfig | None = None) -> list[Cue]:
    """Return the cues shorter than the minimum duration.

    These are not violations; the processor keeps them and flags them as
    ``short`` when they cannot be extended.

    Args:
        cues: Parsed cues.
        config: Limits to check against; the Netflix defaults when omitted.

    Returns:
        The cues whose duration is under ``min_duration_ms``.
    """
    config = config or ProcessingConfig()
    return [cue for cue in cues if cue.duration_ms < config.min_duration_ms]
