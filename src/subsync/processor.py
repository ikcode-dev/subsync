"""Subtitle processor: turn a transcription into timed, laid-out subtitles.

Implements the slice S1 part of the phase 3 plan
(``spec/plan/phase-3-netflix-compliance.md``, "Delivery by slice"):

1. Cleanup: blank segments are dropped and word text is split on whitespace
   into tokens, so no token carries spaces.
2. Word times: taken from Whisper's word timestamps, or interpolated across
   the segment in proportion to character count when there are none; then
   repaired so that the times never run backwards.
3. Split: each segment becomes one or more chunks, cut at word boundaries so
   that every chunk fits the line layout and lasts at most the maximum
   duration. Boundaries after punctuation are preferred.
4. Timing: start and end come from the chunk's first and last word. Short
   subtitles are extended into free time; gaps and overlaps are fixed.
5. Lines: one line when it fits, otherwise the fewest lines, preferring a
   break after punctuation, then the most balanced split. A word longer than
   a line (R12) is kept whole on a line of its own.
6. Report (P2): ``short`` and ``long_word`` flags, and a structural self-check.

Text is never rewritten (decision 0008): the output words are the input
words, in order. All times are whole milliseconds, so the invariants still
hold once the times are written as ``HH:MM:SS,mmm``. Repeat collapsing (R13),
the article/preposition rule (R10), reading-speed easing (R11) and merging
short subtitles (P1) come in slice S2.
"""

import logging
import math
from dataclasses import dataclass
from datetime import timedelta

from subsync.models import (
    ComplianceFlag,
    ComplianceReport,
    ProcessingConfig,
    Subtitle,
    TranscriptionResult,
    TranscriptionSegment,
)

logger = logging.getLogger(__name__)

_MS = timedelta(milliseconds=1)

# A break is preferred after a token ending in one of these, once closing
# quotes and brackets are set aside.
_BREAK_AFTER = (".", ",", "!", "?", ":", ";", "…")
_CLOSING = "\"'”’»)]}"

# Split costs. Every chunk costs _CHUNK_COST, so the fewest chunks win; a
# break that is not after punctuation adds _MID_CLAUSE_COST; a chunk whose
# words span less than the minimum duration adds up to _SHORT_COST; unused
# room adds at most one line's worth, which favours chunks of similar size.
_CHUNK_COST = 1000.0
_MID_CLAUSE_COST = 200.0
_SHORT_COST = 300.0


@dataclass
class _Token:
    """One word without whitespace, with its span in whole milliseconds."""

    text: str
    start: int
    end: int


# =============================================================================
# Public interface
# =============================================================================


def process_transcription(
    result: TranscriptionResult, config: ProcessingConfig | None = None
) -> tuple[list[Subtitle], ComplianceReport]:
    """Turn a transcription into ordered subtitles and a compliance report.

    Never raises for content problems: an empty or all-blank transcript gives
    no subtitles and a report with ``total_subtitles == 0`` and no errors.

    Args:
        result: The transcription, with or without word timestamps.
        config: Compliance limits; the Netflix defaults when omitted.

    Returns:
        The subtitles, numbered from 1 in time order, and the report.
    """
    config = config or ProcessingConfig()

    segments = [
        tokens for segment in result.segments if (tokens := _segment_tokens(segment))
    ]
    _repair_times([token for tokens in segments for token in tokens])
    chunks = [chunk for tokens in segments for chunk in _split(tokens, config)]
    spans = _schedule(chunks, config)

    subtitles: list[Subtitle] = []
    for index, (chunk, (start, end)) in enumerate(
        zip(chunks, spans, strict=True), start=1
    ):
        words = [token.text for token in chunk]
        subtitles.append(
            Subtitle(
                index=index,
                start_time=start * _MS,
                end_time=end * _MS,
                text=" ".join(words),
                lines=_layout(words, config),
            )
        )

    report = _build_report(subtitles, config)
    if report.errors:
        logger.debug("Subtitle self-check failed: %s", "; ".join(report.errors))
    logger.debug(
        "Processed %d segments into %d subtitles (%d short, %d long word)",
        len(result.segments),
        report.total_subtitles,
        report.timing_issues,
        report.line_length_issues,
    )
    return subtitles, report


def find_structural_errors(
    subtitles: list[Subtitle], config: ProcessingConfig | None = None
) -> list[str]:
    """List structural breakage in subtitles (P2).

    Structural breakage is a numbering gap, an out-of-order or overlapping
    subtitle, an end at or before its start, or a line count outside 1 to
    ``max_lines``. The processor makes these impossible, so any finding is a
    bug. Gaps, durations and line lengths are warnings, not checked here.

    Args:
        subtitles: Subtitles in output order.
        config: Limits to check against; the Netflix defaults when omitted.

    Returns:
        One human-readable line per problem; empty when the structure is sound.
    """
    config = config or ProcessingConfig()
    errors: list[str] = []
    previous: Subtitle | None = None
    for position, subtitle in enumerate(subtitles, start=1):
        label = f"Subtitle {subtitle.index}"
        if subtitle.index != position:
            errors.append(f"{label} is numbered out of sequence (expected {position})")
        if subtitle.end_time <= subtitle.start_time:
            errors.append(f"{label} ends at or before its start")
        if previous is not None:
            if subtitle.start_time < previous.start_time:
                errors.append(f"{label} starts before subtitle {previous.index}")
            elif subtitle.start_time < previous.end_time:
                errors.append(f"{label} overlaps subtitle {previous.index}")
        if not 1 <= len(subtitle.lines) <= config.max_lines:
            errors.append(
                f"{label} has {len(subtitle.lines)} lines (expected 1 to {config.max_lines})"
            )
        previous = subtitle
    return errors


# =============================================================================
# Cleanup and word times
# =============================================================================


def _to_ms(seconds: float) -> int:
    """Convert seconds to whole milliseconds; negative or non-finite gives 0."""
    if not math.isfinite(seconds) or seconds <= 0:
        return 0
    return round(seconds * 1000)


def _spread(texts: list[str], start: int, end: int) -> list[_Token]:
    """Time words across a span in proportion to their character count.

    Args:
        texts: Words without whitespace.
        start: Span start in milliseconds.
        end: Span end in milliseconds; an end before the start means no span.

    Returns:
        One token per word, in order.
    """
    if not texts:
        return []
    span = max(0, end - start)
    total = sum(len(text) for text in texts) + len(texts) - 1
    tokens: list[_Token] = []
    offset = 0
    for text in texts:
        first = start + span * offset // total
        offset += len(text)
        tokens.append(_Token(text, first, start + span * offset // total))
        offset += 1  # the space before the next word
    return tokens


def _segment_tokens(segment: TranscriptionSegment) -> list[_Token]:
    """Return a segment's words as whitespace-free tokens with raw times.

    The tokens are the whitespace-separated words of the word texts joined as
    Whisper wrote them. Whisper gives a continuation piece no leading space
    (a URL arrives as ``" github"``, ``".com"``, ``"/ikcode"``...), so such a
    piece extends the token before it instead of starting a new one. A token
    runs from its first piece's start to its last piece's end; a word text
    holding several parts shares its span by character count.

    Without word text, the segment text is split and its words' times are
    interpolated across the segment. A blank segment gives no tokens.
    """
    tokens: list[_Token] = []
    open_word = False  # the joined text so far ends inside a word
    for word in segment.words:
        text = word.word
        parts = _spread(text.split(), _to_ms(word.start), _to_ms(word.end))
        if parts and open_word and not text[0].isspace():
            piece = parts.pop(0)
            tokens[-1].text += piece.text
            tokens[-1].end = piece.end
        tokens.extend(parts)
        if text:
            open_word = not text[-1].isspace()
    if tokens:
        return tokens
    return _spread(segment.text.split(), _to_ms(segment.start), _to_ms(segment.end))


def _repair_times(tokens: list[_Token]) -> None:
    """Make token times monotonic, in place, keeping the token order.

    A start earlier than the start before it is raised to match, so starts
    never decrease. Each end is then moved to lie between its own start and
    the next token's start.
    """
    floor = 0
    for token in tokens:
        token.start = max(token.start, floor)
        floor = token.start
    for current, following in zip(tokens, tokens[1:]):
        current.end = min(max(current.end, current.start), following.start)
    if tokens:
        tokens[-1].end = max(tokens[-1].end, tokens[-1].start)


# =============================================================================
# Splitting into chunks
# =============================================================================


def _ends_clause(text: str) -> bool:
    """Tell whether a word ends in punctuation that makes a good break."""
    return text.rstrip(_CLOSING).endswith(_BREAK_AFTER)


def _min_lines(words: list[str], width: int) -> int:
    """Return the fewest lines the words fit on.

    A line holds words up to ``width`` characters; a longer word sits alone on
    its own line. Filling each line greedily gives the minimum.
    """
    lines = 0
    open_width: int | None = None  # length of the line being filled, if any
    for word in words:
        if open_width is not None and open_width + 1 + len(word) <= width:
            open_width += 1 + len(word)
        else:
            lines += 1
            open_width = len(word) if len(word) <= width else None
    return lines


def _fits(chunk: list[_Token], config: ProcessingConfig) -> bool:
    """Tell whether a chunk can be one subtitle.

    A single word always fits (its duration is clamped later). Otherwise the
    words must span at most the maximum duration and fit the line layout.
    Dropping words from either end of a chunk that fits keeps it fitting.
    """
    if len(chunk) == 1:
        return True
    if chunk[-1].end - chunk[0].start > config.max_duration_ms:
        return False
    words = [token.text for token in chunk]
    return _min_lines(words, config.max_chars_per_line) <= config.max_lines


def _chunk_cost(
    chunk: list[_Token], closes_segment: bool, config: ProcessingConfig
) -> float:
    """Score one chunk for the split; lower is better."""
    cost = _CHUNK_COST
    if not closes_segment and not _ends_clause(chunk[-1].text):
        cost += _MID_CLAUSE_COST
    duration = chunk[-1].end - chunk[0].start
    if duration < config.min_duration_ms:
        cost += (
            _SHORT_COST * (config.min_duration_ms - duration) / config.min_duration_ms
        )
    capacity = config.max_chars_per_line * config.max_lines
    unused = max(0, capacity - len(" ".join(token.text for token in chunk)))
    return cost + unused * unused / capacity


def _split(tokens: list[_Token], config: ProcessingConfig) -> list[list[_Token]]:
    """Cut one segment's tokens into chunks that each fit one subtitle.

    Dynamic programming over cut positions picks the cheapest sequence of
    fitting chunks (see ``_chunk_cost``). Because a fitting chunk stays
    fitting when words are dropped from its ends, the search for chunks that
    end at a given word stops at the first one that does not fit.
    """
    count = len(tokens)
    best = [0.0] + [math.inf] * count
    cut = [0] * (count + 1)
    for end in range(1, count + 1):
        for begin in range(end - 1, -1, -1):
            chunk = tokens[begin:end]
            if not _fits(chunk, config):
                break
            cost = best[begin] + _chunk_cost(chunk, end == count, config)
            if cost < best[end]:
                best[end], cut[end] = cost, begin

    chunks: list[list[_Token]] = []
    end = count
    while end > 0:
        chunks.append(tokens[cut[end] : end])
        end = cut[end]
    chunks.reverse()
    return chunks


# =============================================================================
# Timing
# =============================================================================


def _schedule(
    chunks: list[list[_Token]], config: ProcessingConfig
) -> list[tuple[int, int]]:
    """Give every chunk its final start and end in milliseconds.

    Starts come from each chunk's first word, moved later only when the
    previous subtitle would otherwise have no room (at least 1 ms plus the
    gap). Ends come from the last word, capped by the maximum duration and by
    the next start minus the gap. A subtitle under the minimum duration is
    extended into the free time up to the same caps.

    Returns:
        ``(start, end)`` per chunk: ordered, ``end > start``, gaps of at least
        ``min_gap_ms`` and durations of at most ``max_duration_ms``.
    """
    gap = config.min_gap_ms
    starts: list[int] = []
    for chunk in chunks:
        start = chunk[0].start
        if starts:
            start = max(start, starts[-1] + gap + 1)
        starts.append(start)

    spans: list[tuple[int, int]] = []
    for position, (chunk, start) in enumerate(zip(chunks, starts, strict=True)):
        limit = start + config.max_duration_ms
        if position + 1 < len(starts):
            limit = min(limit, starts[position + 1] - gap)
        end = min(max(chunk[-1].end, start + 1), limit)
        if end - start < config.min_duration_ms:
            end = max(end, min(start + config.min_duration_ms, limit))
        spans.append((start, end))
    return spans


# =============================================================================
# Line layout
# =============================================================================


def _layout(words: list[str], config: ProcessingConfig) -> list[str]:
    """Lay a chunk's words out on the fewest lines.

    With more than one line, the break positions are chosen by dynamic
    programming, comparing in order: the number of breaks not after
    punctuation, the sum of squared line lengths (balance), then longer lower
    lines. A line holds one word longer than the width, or words up to it.
    """
    width = config.max_chars_per_line
    line_count = _min_lines(words, width)
    if line_count <= 1:
        return [" ".join(words)]

    count = len(words)
    best: list[list[tuple[int, int, int] | None]] = [
        [None] * (count + 1) for _ in range(line_count + 1)
    ]
    cut = [[0] * (count + 1) for _ in range(line_count + 1)]
    best[0][0] = (0, 0, 0)
    for line in range(1, line_count + 1):
        for end in range(1, count + 1):
            for begin in range(end - 1, -1, -1):
                length = len(" ".join(words[begin:end]))
                if end - begin > 1 and length > width:
                    break
                previous = best[line - 1][begin]
                if previous is None:
                    continue
                mid_clause = int(begin > 0 and not _ends_clause(words[begin - 1]))
                score = (
                    previous[0] + mid_clause,
                    previous[1] + length * length,
                    previous[2] - (line - 1) * length,
                )
                current = best[line][end]
                if current is None or score < current:
                    best[line][end], cut[line][end] = score, begin

    lines: list[str] = []
    end = count
    for line in range(line_count, 0, -1):
        begin = cut[line][end]
        lines.append(" ".join(words[begin:end]))
        end = begin
    lines.reverse()
    return lines


# =============================================================================
# Report
# =============================================================================


def _timestamp(value: timedelta) -> str:
    """Format a time as ``HH:MM:SS``, like the Studio editor."""
    seconds = value // timedelta(seconds=1)
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _describe(flag: ComplianceFlag, config: ProcessingConfig) -> str:
    """Write one human-readable warning line for a flag."""
    where = f"Subtitle {flag.subtitle_index} at {_timestamp(flag.start_time)}"
    if flag.kind == "long_word":
        return (
            f"{where}: word over {config.max_chars_per_line} characters "
            f"kept whole: {flag.detail}"
        )
    return (
        f"{where}: lasts {flag.detail}, under {config.min_duration_ms} ms; "
        "the next subtitle is too close to extend it"
    )


def _build_report(
    subtitles: list[Subtitle], config: ProcessingConfig
) -> ComplianceReport:
    """Build the compliance report: flags, counts, warnings and errors (P2)."""
    flags: list[ComplianceFlag] = []
    for subtitle in subtitles:
        long_words = [
            word
            for word in subtitle.text.split()
            if len(word) > config.max_chars_per_line
        ]
        if long_words:
            flags.append(
                ComplianceFlag(
                    kind="long_word",
                    subtitle_index=subtitle.index,
                    start_time=subtitle.start_time,
                    detail=" ".join(long_words),
                )
            )
        duration = (subtitle.end_time - subtitle.start_time) // _MS
        if duration < config.min_duration_ms:
            flags.append(
                ComplianceFlag(
                    kind="short",
                    subtitle_index=subtitle.index,
                    start_time=subtitle.start_time,
                    detail=f"{duration} ms",
                )
            )
    flags.sort(key=lambda flag: (flag.start_time, flag.subtitle_index))

    errors = find_structural_errors(subtitles, config)
    return ComplianceReport(
        total_subtitles=len(subtitles),
        timing_issues=sum(1 for flag in flags if flag.kind == "short"),
        cps_warnings=0,
        line_length_issues=sum(1 for flag in flags if flag.kind == "long_word"),
        is_compliant=not errors,
        warnings=[_describe(flag, config) for flag in flags],
        errors=errors,
        flags=flags,
    )
