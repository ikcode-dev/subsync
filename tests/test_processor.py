"""Tests for the subtitle processor (task S1.2).

Every output is checked with the SRT invariant helpers (``check_cues``,
``short_cues``), which were written from the requirements independently of
the processor, plus text preservation, whole milliseconds and report
consistency. The numbered scenarios come from the task's Test Scenarios.
"""

import copy
import math
import random
from datetime import timedelta

import pytest
from srt_invariants import Cue, check_cues, short_cues
from transcript_fixtures import (
    BLANK_SEGMENTS,
    EPISODE_WITH_URL,
    NO_SEGMENTS,
    UNICODE_AND_EMOJI,
    URL,
    WHISPER_QUIRKS,
    load_transcript,
    transcript_names,
)

from subsync.models import (
    ComplianceReport,
    ProcessingConfig,
    Subtitle,
    TranscriptionResult,
    TranscriptionSegment,
    Word,
)
from subsync import processor
from subsync.processor import find_structural_errors, process_transcription

MS = timedelta(milliseconds=1)

# =============================================================================
# Helpers
# =============================================================================


def ms(value: timedelta) -> int:
    """Return a timedelta as whole milliseconds (exact, no float rounding)."""
    return value // MS


def segment(
    text: str, start: float, end: float, *, seg_id: int = 0, words: bool = True
) -> TranscriptionSegment:
    """Build a segment with clean Whisper-style words (``" word"``).

    Word times are contiguous and proportional to word length, rounded to
    whole milliseconds. With ``words=False`` the segment has no word
    timestamps, only its text.
    """
    tokens = text.split()
    total = sum(len(token) for token in tokens)
    word_list: list[Word] = []
    cursor = start
    for token in tokens:
        stop = cursor + (end - start) * len(token) / total
        word_list.append(
            Word(word=f" {token}", start=round(cursor, 3), end=round(stop, 3))
        )
        cursor = stop
    return TranscriptionSegment(
        id=seg_id,
        start=start,
        end=end,
        text="".join(word.word for word in word_list),
        words=word_list if words else [],
    )


def transcript(*segments: TranscriptionSegment) -> TranscriptionResult:
    """Wrap segments in an English result that lasts past the last segment."""
    end = max((seg.end for seg in segments), default=0.0)
    return TranscriptionResult(
        language="en", duration=end + 5.0, segments=list(segments)
    )


def to_cues(subtitles: list[Subtitle]) -> list[Cue]:
    """Turn subtitles into invariant-checker cues without any writer."""
    return [
        Cue(
            index=sub.index,
            start_ms=ms(sub.start_time),
            end_ms=ms(sub.end_time),
            lines=list(sub.lines),
        )
        for sub in subtitles
    ]


def input_words(result: TranscriptionResult) -> list[str]:
    """The non-empty words of the input, in order, whitespace removed.

    A segment's words are its word texts joined as Whisper wrote them (a
    piece without a leading space continues the word before it), or its text
    when the word list holds no text.
    """
    tokens: list[str] = []
    for seg in result.segments:
        from_words = "".join(word.word for word in seg.words).split()
        tokens.extend(from_words or seg.text.split())
    return tokens


def output_words(subtitles: list[Subtitle]) -> list[str]:
    """The words of the output, in order."""
    return [token for sub in subtitles for token in sub.text.split()]


def check_output(
    result: TranscriptionResult,
    subtitles: list[Subtitle],
    report: ComplianceReport,
    config: ProcessingConfig | None = None,
) -> None:
    """Assert every S1.2 guarantee on one processor output."""
    config = config or ProcessingConfig()
    cues = to_cues(subtitles)

    # R8, R9, R12 invariants, from the independent checker
    assert check_cues(cues, config) == []

    # Whole milliseconds, text layout and preservation
    for sub in subtitles:
        assert sub.start_time % MS == timedelta(0), sub
        assert sub.end_time % MS == timedelta(0), sub
        assert sub.text.split(" ") == sub.text.split(), sub
        assert " ".join(sub.lines) == sub.text, sub
    assert output_words(subtitles) == input_words(result)

    # Report (P2) agrees with the subtitles and the checker
    short = [flag.subtitle_index for flag in report.flags if flag.kind == "short"]
    assert short == [cue.index for cue in short_cues(cues, config)]
    long_word = [
        flag.subtitle_index for flag in report.flags if flag.kind == "long_word"
    ]
    assert long_word == [
        sub.index
        for sub in subtitles
        if any(len(word) > config.max_chars_per_line for word in sub.text.split())
    ]
    for flag in report.flags:
        assert flag.start_time == subtitles[flag.subtitle_index - 1].start_time
    starts = [flag.start_time for flag in report.flags]
    assert starts == sorted(starts)
    assert report.total_subtitles == len(subtitles)
    assert report.timing_issues == len(short)
    assert report.line_length_issues == len(long_word)
    assert report.cps_warnings == 0
    assert report.errors == []
    assert report.is_compliant is True
    assert len(report.warnings) == len(report.flags)
    assert all(warning.strip() and "\n" not in warning for warning in report.warnings)


def process_and_check(
    result: TranscriptionResult, config: ProcessingConfig | None = None
) -> tuple[list[Subtitle], ComplianceReport]:
    """Run the processor and assert every guarantee on its output."""
    subtitles, report = process_transcription(result, config)
    check_output(result, subtitles, report, config)
    return subtitles, report


def word_starts_ms(result: TranscriptionResult) -> set[int]:
    """Every input word start, in milliseconds."""
    return {round(word.start * 1000) for seg in result.segments for word in seg.words}


# =============================================================================
# Scenarios 1-3: splitting and timing from words
# =============================================================================


class TestSplitting:
    """Chunks come from word timestamps and respect 2 x 42 and 7 s."""

    def test_two_short_sentences_keep_their_word_times(self):
        """Scenario 1: two subtitles, times from words, one line each."""
        result = transcript(
            segment("Hello there.", 1.0, 2.2),
            segment("How are you?", 3.0, 4.4, seg_id=1),
        )

        subtitles, report = process_and_check(result)

        assert [sub.index for sub in subtitles] == [1, 2]
        assert [(ms(sub.start_time), ms(sub.end_time)) for sub in subtitles] == [
            (1000, 2200),
            (3000, 4400),
        ]
        assert [sub.lines for sub in subtitles] == [["Hello there."], ["How are you?"]]
        assert [sub.text for sub in subtitles] == ["Hello there.", "How are you?"]
        assert report.flags == []

    def test_150_character_sentence_is_split_at_word_starts(self):
        """Scenario 2: split by length even though it lasts under 7 s."""
        text = (
            "Today we are going to build a small command line tool that turns any "
            "local video into subtitles you can upload to YouTube Studio without "
            "editing them."
        )
        assert len(text) == 150
        result = transcript(segment(text, 10.0, 16.5))

        subtitles, _ = process_and_check(result)

        assert len(subtitles) >= 2
        starts = word_starts_ms(result)
        for sub in subtitles:
            assert len(sub.lines) <= 2
            assert all(len(line) <= 42 for line in sub.lines)
            assert sum(len(line) for line in sub.lines) <= 84
            assert ms(sub.start_time) in starts

    def test_long_segment_is_split_into_pieces_of_at_most_7_seconds(self):
        """Scenario 3: a 9 s, 60-character segment is split by duration."""
        text = "Now we wait for the model to finish loading into memory okay"
        assert len(text) == 60
        result = transcript(segment(text, 2.0, 11.0))

        subtitles, _ = process_and_check(result)

        assert len(subtitles) >= 2
        starts = word_starts_ms(result)
        for sub in subtitles:
            assert ms(sub.end_time - sub.start_time) <= 7000
            assert ms(sub.start_time) in starts

    def test_split_prefers_a_boundary_after_punctuation(self):
        """A needed split lands after the sentence end, not mid-sentence."""
        first = "Okay so this is the first sentence and it is quite long."
        second = "And here comes a second one that is also fairly long."
        result = transcript(segment(f"{first} {second}", 0.0, 6.0))

        subtitles, _ = process_and_check(result)

        assert [sub.text for sub in subtitles] == [first, second]

    def test_split_after_punctuation_beats_a_more_even_split(self):
        """The sentence end wins even when a mid-sentence cut is more even."""
        first = "We start with a clean project folder."
        second = "Then we add the dependencies we need and write our very first test."
        result = transcript(segment(f"{first} {second}", 0.0, 6.0))

        subtitles, _ = process_and_check(result)

        assert [sub.text for sub in subtitles] == [first, second]

    def test_interpolates_word_times_without_word_timestamps(self):
        """Scenario 8: a 120-character segment with ``words=[]``."""
        text = (
            "This segment has no word timestamps so each word time is interpolated "
            "from the segment span in proportion to its length."
        )
        assert len(text) == 120
        result = transcript(segment(text, 4.0, 10.0, words=False))
        assert result.segments[0].words == []

        subtitles, _ = process_and_check(result)

        assert len(subtitles) >= 2
        assert ms(subtitles[0].start_time) == 4000
        span_ms = 6000
        for sub in subtitles[1:]:
            chars_before = text.index(sub.text)
            expected = 4000 + span_ms * chars_before / len(text)
            assert abs(ms(sub.start_time) - expected) <= 0.02 * span_ms
        assert ms(subtitles[-1].end_time) <= 10000


# =============================================================================
# Scenarios 4-7, 9, 15: timing repair
# =============================================================================


class TestTiming:
    """Short extension, gaps, overlaps, broken word times and the 7 s clamp."""

    def test_short_subtitle_is_extended_into_silence(self):
        """Scenario 4: 400 ms "Yes." followed by 2 s of silence."""
        result = transcript(
            segment("Yes.", 1.0, 1.4),
            segment("Let's continue with the next step.", 3.4, 5.4, seg_id=1),
        )

        subtitles, report = process_and_check(result)

        assert ms(subtitles[0].start_time) == 1000
        assert ms(subtitles[0].end_time - subtitles[0].start_time) >= 833
        assert report.flags == []
        assert report.timing_issues == 0

    def test_short_subtitle_without_room_is_kept_and_flagged(self):
        """Scenario 5: 400 ms "Yes." with the next speech 450 ms later."""
        result = transcript(
            segment("Yes.", 1.0, 1.4),
            segment("Let's continue.", 1.85, 3.0, seg_id=1),
        )

        subtitles, report = process_and_check(result)

        assert [sub.text for sub in subtitles] == ["Yes.", "Let's continue."]
        assert ms(subtitles[0].end_time - subtitles[0].start_time) < 833
        assert ms(subtitles[1].start_time - subtitles[0].end_time) >= 83
        assert [(flag.kind, flag.subtitle_index) for flag in report.flags] == [
            ("short", 1)
        ]
        assert report.flags[0].start_time == timedelta(seconds=1)
        assert report.timing_issues == 1
        assert "Subtitle 1" in report.warnings[0]
        assert "00:00:01" in report.warnings[0]

    def test_overlapping_segments_are_separated_by_the_gap(self):
        """Scenario 6: segment 2 starts 300 ms before segment 1 ends."""
        result = transcript(
            segment("We start by opening the terminal.", 1.0, 4.0),
            segment("Then we type the command.", 3.7, 6.0, seg_id=1),
        )

        subtitles, _ = process_and_check(result)

        assert len(subtitles) == 2
        assert ms(subtitles[1].start_time) == 3700
        assert ms(subtitles[1].start_time - subtitles[0].end_time) >= 83
        assert subtitles[0].end_time > subtitles[0].start_time

    def test_small_gap_between_segments_is_widened(self):
        """Scenario 7: a 40 ms gap between segments."""
        result = transcript(
            segment("We start by opening the terminal.", 1.0, 4.0),
            segment("Then we type the command.", 4.04, 6.0, seg_id=1),
        )

        subtitles, _ = process_and_check(result)

        assert ms(subtitles[1].start_time - subtitles[0].end_time) >= 83
        assert ms(subtitles[1].start_time) == 4040

    def test_broken_word_times_keep_order_and_positive_durations(self):
        """Scenario 9: zero-length words, identical times, a backwards word."""
        words = [
            Word(" We", 1.0, 1.0),
            Word(" install", 1.0, 1.0),
            Word(" the", 1.0, 1.0),
            Word(" package,", 0.4, 0.2),
            Word(" then", 1.3, 1.3),
            Word(" we", 1.3, 1.3),
            Word(" run", 0.9, 1.6),
            Word(" the", 1.6, 1.6),
            Word(" tests.", 1.6, 1.5),
        ]
        first = TranscriptionSegment(
            id=0, start=1.0, end=1.6, text="".join(w.word for w in words), words=words
        )
        second = TranscriptionSegment(
            id=1,
            start=1.2,
            end=1.2,
            text=" Done.",
            words=[Word(" Done.", 1.2, 1.2)],
        )
        result = TranscriptionResult(
            language="en", duration=3.0, segments=[first, second]
        )

        subtitles, _ = process_and_check(result)

        assert output_words(subtitles) == [
            "We", "install", "the", "package,", "then", "we", "run", "the", "tests.", "Done.",
        ]  # fmt: skip
        for sub in subtitles:
            assert sub.end_time > sub.start_time

    def test_whisper_quirks_fixture_meets_every_invariant(self):
        """Scenario 9, stored fixture: overlaps, glitches and a no-words segment."""
        result = load_transcript(WHISPER_QUIRKS)

        subtitles, _ = process_and_check(result)

        assert subtitles
        for sub in subtitles:
            assert sub.end_time > sub.start_time

    def test_single_word_longer_than_7_seconds_is_clamped(self):
        """Scenario 15: a single word timed 0-9 s."""
        result = transcript(segment("Hello.", 0.0, 9.0))

        subtitles, report = process_and_check(result)

        assert len(subtitles) == 1
        assert ms(subtitles[0].start_time) == 0
        assert ms(subtitles[0].end_time) == 7000
        assert report.flags == []

    def test_crowded_segments_are_moved_apart_instead_of_overlapping(self):
        """Many segments at the same instant still come out valid and in order."""
        result = transcript(
            *[segment(f"Word{i}.", 5.0, 5.0, seg_id=i) for i in range(6)],
            segment("Later speech.", 5.1, 6.0, seg_id=6),
        )

        subtitles, report = process_and_check(result)

        assert [sub.text for sub in subtitles] == [f"Word{i}." for i in range(6)] + [
            "Later speech."
        ]
        assert report.timing_issues == len(short_cues(to_cues(subtitles)))

    def test_sub_millisecond_input_times_become_whole_milliseconds(self):
        """Times are whole milliseconds from the start, not rounded at write time."""
        words = [
            Word(" Precise", 1.0004, 1.2346),
            Word(" timing", 1.2346, 1.7771),
            Word(" here.", 1.7771, 2.9996),
        ]
        segments = [
            TranscriptionSegment(
                0, 1.0004, 2.9996, "".join(w.word for w in words), words
            ),
            TranscriptionSegment(
                1, 3.0831, 3.0832, " Next.", [Word(" Next.", 3.0831, 3.0832)]
            ),
        ]
        result = TranscriptionResult(language="en", duration=6.0, segments=segments)

        subtitles, _ = process_and_check(result)

        assert [(ms(sub.start_time), ms(sub.end_time)) for sub in subtitles] == [
            (1000, 3000),
            (3083, 3916),
        ]

    def test_non_finite_and_negative_times_do_not_raise(self):
        """Content problems never raise; bad times are repaired."""
        words = [
            Word(" Not", math.nan, math.nan),
            Word(" a", -2.0, -1.0),
            Word(" number.", math.inf, 1.0),
        ]
        result = TranscriptionResult(
            language="en",
            duration=3.0,
            segments=[
                TranscriptionSegment(
                    id=0, start=-1.0, end=1.0, text=" Not a number.", words=words
                )
            ],
        )

        subtitles, _ = process_and_check(result)

        assert [sub.text for sub in subtitles] == ["Not a number."]
        assert ms(subtitles[0].start_time) >= 0


# =============================================================================
# Scenarios 10-12: line layout and long words
# =============================================================================


class TestLines:
    """Lines prefer punctuation, then balance; long words stay whole (R12)."""

    def test_text_up_to_42_characters_stays_on_one_line(self):
        """Text of at most 42 characters is a single line."""
        text = "This line is exactly forty-two characters."
        assert len(text) == 42
        subtitles, _ = process_and_check(transcript(segment(text, 0.0, 3.0)))

        assert [sub.lines for sub in subtitles] == [[text]]

    def test_break_after_the_comma(self):
        """Scenario 11: a 46-character line breaks after the comma."""
        text = "We install the package, then we run the tests."
        assert len(text) == 46

        subtitles, _ = process_and_check(transcript(segment(text, 0.0, 3.0)))

        assert [sub.lines for sub in subtitles] == [
            ["We install the package,", "then we run the tests."]
        ]

    def test_punctuation_wins_over_a_more_balanced_break(self):
        """A break after punctuation is preferred to a more balanced one."""
        text = "We install the package with uv, then run the tests."

        subtitles, _ = process_and_check(transcript(segment(text, 0.0, 3.5)))

        assert [sub.lines for sub in subtitles] == [
            ["We install the package with uv,", "then run the tests."]
        ]

    def test_balanced_break_without_punctuation(self):
        """Scenario 12: 60 characters without punctuation, no one-word orphan."""
        text = "We open a terminal and then run the build script for our app"
        assert len(text) == 60

        subtitles, _ = process_and_check(transcript(segment(text, 0.0, 4.0)))

        assert len(subtitles) == 1
        lines = subtitles[0].lines
        assert len(lines) == 2
        assert all(len(line) <= 42 for line in lines)
        assert all(len(line.split()) >= 2 for line in lines)
        assert abs(len(lines[0]) - len(lines[1])) <= 6

    def test_long_url_is_kept_whole_on_its_own_line_and_flagged(self):
        """Scenario 10: the 49-character URL stays unchanged and is flagged."""
        text = f"The full guide is at {URL} if you want to follow along."
        result = transcript(segment(text, 20.0, 26.0))

        subtitles, report = process_and_check(result)

        with_url = [sub for sub in subtitles if URL in sub.text.split()]
        assert len(with_url) == 1
        assert URL in with_url[0].lines
        assert output_words(subtitles).count(URL) == 1
        assert all("…" not in sub.text for sub in subtitles)
        long_flags = [flag for flag in report.flags if flag.kind == "long_word"]
        assert len(long_flags) == 1
        assert long_flags[0].subtitle_index == with_url[0].index
        assert long_flags[0].start_time == with_url[0].start_time
        assert report.line_length_issues == 1
        warning = report.warnings[report.flags.index(long_flags[0])]
        assert URL in warning
        assert f"Subtitle {with_url[0].index}" in warning

    def test_word_pieces_without_leading_space_stay_one_word(self):
        """Whisper splits a URL or a number into pieces with no leading space.

        The pieces are one word of the text: no space is inserted, so the URL
        stays copy-pasteable and is flagged as one long word.
        """
        pieces = "github .com /ikcode -dev /subsync /blob /main /README .md".split()
        assert "".join(pieces) == URL
        texts = [
            " See",
            *[f" {pieces[0]}", *pieces[1:]],
            " and",
            " version",
            " 3",
            ".14",
            ".",
        ]
        words = [
            Word(text, 1.0 + 0.2 * i, 1.2 + 0.2 * i) for i, text in enumerate(texts)
        ]
        result = transcript(
            TranscriptionSegment(
                id=0, start=1.0, end=words[-1].end, text="".join(texts), words=words
            )
        )

        subtitles, report = process_and_check(result)

        assert output_words(subtitles) == ["See", URL, "and", "version", "3.14."]
        assert any(URL in sub.lines for sub in subtitles)
        assert [flag.kind for flag in report.flags] == ["long_word"]
        url_subtitle = next(sub for sub in subtitles if URL in sub.lines)
        assert ms(url_subtitle.start_time) == 1000

    def test_two_long_words_can_share_a_subtitle_one_per_line(self):
        """Two long words fit one subtitle when each has its own line."""
        other = "x" * 43
        result = transcript(segment(f"{URL} {other}", 0.0, 3.0))

        subtitles, report = process_and_check(result)

        assert [sub.lines for sub in subtitles] == [[URL, other]]
        assert [flag.kind for flag in report.flags] == ["long_word"]

    def test_text_around_a_long_word_moves_to_neighbouring_subtitles(self):
        """Text on both sides of a long word cannot share its subtitle."""
        before = "Before the link we say quite a few words here,"
        after = "and after the link we also say many more words."
        result = transcript(segment(f"{before} {URL} {after}", 0.0, 6.0))

        subtitles, _ = process_and_check(result)

        with_url = next(sub for sub in subtitles if URL in sub.lines)
        assert len(with_url.lines) <= 2
        assert len(subtitles) >= 2


# =============================================================================
# Scenarios 13-14: cleanup and text preservation
# =============================================================================


class TestTextPreservation:
    """Blank input yields nothing; every other word survives unchanged."""

    @pytest.mark.parametrize("name", [BLANK_SEGMENTS, NO_SEGMENTS])
    def test_blank_transcript_gives_no_subtitles(self, name):
        """Scenario 13: only blank segments, or none at all."""
        subtitles, report = process_transcription(load_transcript(name))

        assert subtitles == []
        assert report.total_subtitles == 0
        assert report.errors == []
        assert report.is_compliant is True
        assert report.flags == []
        assert report.warnings == []

    def test_polish_diacritics_and_emoji_are_preserved(self):
        """Scenario 14: case and Unicode are kept exactly."""
        result = load_transcript(UNICODE_AND_EMOJI)

        subtitles, _ = process_and_check(result)

        assert [sub.text for sub in subtitles] == [
            "ZAŻÓŁĆ GĘŚLĄ JAŹŃ",
            "zażółć gęślą jaźń 🎉 👍🏽 👩‍💻 café naïve",
        ]

    def test_whitespace_in_word_text_is_normalized(self):
        """Leading, doubled and internal whitespace never reaches a subtitle."""
        words = [
            Word("  So", 0.0, 0.3),
            Word("\twe ", 0.3, 0.5),
            Word(" New  York", 0.5, 1.2),
            Word("", 1.2, 1.3),
            Word(" \n", 1.3, 1.4),
            Word(" go.", 1.4, 2.0),
        ]
        result = TranscriptionResult(
            language="en",
            duration=3.0,
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=0.0,
                    end=2.0,
                    text="".join(w.word for w in words),
                    words=words,
                )
            ],
        )

        subtitles, _ = process_and_check(result)

        assert [sub.text for sub in subtitles] == ["So we New York go."]

    def test_input_is_not_modified(self):
        """Processing creates new objects and leaves the transcript alone."""
        result = load_transcript(WHISPER_QUIRKS)
        before = copy.deepcopy(result)

        process_transcription(result)

        assert result == before


# =============================================================================
# Report (P2) and configuration
# =============================================================================


class TestReport:
    """The report counts flags, lists them by time and has no errors."""

    def test_episode_fixture_has_exactly_one_long_word_flag(self):
        """The integration fixture: one long_word flag, no short flag."""
        result = load_transcript(EPISODE_WITH_URL)

        subtitles, report = process_and_check(result)

        assert len(subtitles) >= len(result.segments)
        assert [flag.kind for flag in report.flags] == ["long_word"]
        assert report.flags[0].detail == URL
        assert report.line_length_issues == 1
        assert report.timing_issues == 0
        assert report.is_compliant is True

    def test_flags_are_sorted_by_start_time_with_one_warning_each(self):
        """A short flag and a later long-word flag, in time order."""
        result = transcript(
            segment("Yes.", 1.0, 1.4),
            segment("Let's continue.", 1.85, 3.0, seg_id=1),
            segment(f"Read {URL} now.", 5.0, 8.0, seg_id=2),
        )

        subtitles, report = process_and_check(result)

        assert [flag.kind for flag in report.flags] == ["short", "long_word"]
        assert report.timing_issues == 1
        assert report.line_length_issues == 1
        assert report.total_subtitles == len(subtitles)
        assert len(report.warnings) == 2

    def test_default_config_is_used_when_none_is_given(self):
        """``config=None`` behaves like the Netflix defaults."""
        result = load_transcript(EPISODE_WITH_URL)

        assert process_transcription(result) == process_transcription(
            result, ProcessingConfig()
        )

    def test_custom_limits_come_from_the_config(self):
        """Tighter limits are honoured; nothing is hard-coded."""
        config = ProcessingConfig(
            max_chars_per_line=30,
            min_duration_ms=1000,
            max_duration_ms=4000,
            min_gap_ms=120,
        )
        result = load_transcript(EPISODE_WITH_URL)

        subtitles, report = process_and_check(result, config)

        assert all(
            len(line) <= 30 for sub in subtitles for line in sub.lines if " " in line
        )
        assert all(ms(sub.end_time - sub.start_time) <= 4000 for sub in subtitles)
        assert report.line_length_issues == 1


class TestStructuralErrors:
    """The self-check behind ``report.errors`` finds structural breakage."""

    @staticmethod
    def sub(
        index: int, start: int, end: int, lines: list[str] | None = None
    ) -> Subtitle:
        """Build a subtitle from millisecond times."""
        lines = ["text"] if lines is None else lines
        return Subtitle(
            index=index,
            start_time=timedelta(milliseconds=start),
            end_time=timedelta(milliseconds=end),
            text=" ".join(lines),
            lines=lines,
        )

    def test_valid_subtitles_have_no_errors(self):
        """Ordered, separated subtitles with 1-2 lines are fine."""
        subtitles = [self.sub(1, 0, 1000), self.sub(2, 1083, 2000, ["a", "b"])]

        assert find_structural_errors(subtitles) == []

    @pytest.mark.parametrize(
        ("case", "fragment"),
        [
            ("overlap", "overlaps"),
            ("disorder", "starts before"),
            ("end_before_start", "ends at or before"),
            ("three_lines", "3 lines"),
            ("no_lines", "0 lines"),
            ("numbering", "numbered"),
        ],
    )
    def test_each_structural_problem_is_reported(self, case, fragment):
        """One error per broken rule, naming the problem."""
        cases = {
            "overlap": [self.sub(1, 0, 1000), self.sub(2, 900, 2000)],
            "disorder": [self.sub(1, 1000, 2000), self.sub(2, 500, 800)],
            "end_before_start": [self.sub(1, 1000, 1000)],
            "three_lines": [self.sub(1, 0, 1000, ["a", "b", "c"])],
            "no_lines": [self.sub(1, 0, 1000, [])],
            "numbering": [self.sub(1, 0, 1000), self.sub(3, 2000, 3000)],
        }

        errors = find_structural_errors(cases[case])

        assert len(errors) == 1, errors
        assert fragment in errors[0]

    def test_self_check_failure_reaches_the_report(self, monkeypatch):
        """A broken processor step shows up in ``report.errors`` (P2).

        Fault injection: the line layout is forced to 3 lines, which the
        processor normally makes impossible. The report must say so and
        stop claiming compliance.
        """
        monkeypatch.setattr(processor, "_layout", lambda words, config: ["a", "b", "c"])
        result = transcript(segment("Hello there.", 1.0, 2.2))

        subtitles, report = process_transcription(result)

        assert len(subtitles) == 1
        assert report.errors == ["Subtitle 1 has 3 lines (expected 1 to 2)"]
        assert report.is_compliant is False
        assert report.warnings == []


# =============================================================================
# Every stored fixture, and scenario 16: seeded adversarial transcripts
# =============================================================================


@pytest.mark.parametrize("name", transcript_names())
def test_every_stored_transcript_meets_the_invariants(name):
    """Every JSON fixture passes the checker, preservation and the report checks."""
    process_and_check(load_transcript(name))


VOCABULARY = [
    "we", "install", "the", "package,", "then", "run", "tests.", "Okay!", "really?",
    "note:", "sync;", "a", "I", "uv", "—", "3.14", "(maybe),", '"quoted."', "e.g.",
    "...", "it's", "YouTube", "Studio", "subtitles", "--output-directory", "ZAŻÓŁĆ",
    "gęślą", "🎉", "👩‍💻", "café", URL, "x" * 43, "y" * 42, "z" * 41,
    "supercalifragilisticexpialidocious-and-then-some-more",
]  # fmt: skip

# Every fourth transcript uses other limits, so nothing may be hard-coded.
OTHER_CONFIGS = [
    ProcessingConfig(
        max_chars_per_line=30,
        min_duration_ms=1000,
        max_duration_ms=5000,
        min_gap_ms=120,
    ),
    ProcessingConfig(max_chars_per_line=20, max_lines=3),
    ProcessingConfig(max_lines=1, min_gap_ms=0),
]


def random_word_text(rng: random.Random) -> str:
    """A Whisper-like word: leading/trailing whitespace, sometimes blank or two words."""
    roll = rng.random()
    if roll < 0.05:
        return rng.choice(["", " ", "  ", "\t", "  "])
    body = rng.choice(VOCABULARY)
    if roll < 0.08:
        body = f"{body} {rng.choice(VOCABULARY)}"
    prefix = rng.choice([" ", " ", " ", " ", "", "  ", "\t", "\n "])
    suffix = rng.choice(["", "", "", "", " ", "\t"])
    return f"{prefix}{body}{suffix}"


def random_segment(
    rng: random.Random, seg_id: int, cursor: float
) -> TranscriptionSegment:
    """A segment with adversarial timing, starting near ``cursor``."""
    start = cursor + rng.choice(
        [rng.uniform(-1.5, 0.5), rng.uniform(0.0, 3.0), rng.uniform(5, 20)]
    )
    if rng.random() < 0.08:
        text = rng.choice(["", " ", "  \n\t", " "])
        blank_words = [Word(" ", start, start + 0.2)] if rng.random() < 0.5 else []
        return TranscriptionSegment(seg_id, start, start + 1.0, text, blank_words)

    mode = rng.choice(
        ["clean", "clean", "zero", "identical", "backwards", "jitter", "huge"]
    )
    words: list[Word] = []
    t = start
    for _ in range(rng.randint(1, 40)):
        text = random_word_text(rng)
        if mode == "zero":
            begin = end = t
            t += rng.uniform(0.0, 0.15)
        elif mode == "identical":
            begin, end = start, start + rng.choice([0.0, 0.3])
        elif mode == "backwards" and rng.random() < 0.3:
            begin = t - rng.uniform(0.0, 2.5)
            end = begin + rng.uniform(-0.2, 0.5)
        elif mode == "jitter":
            begin = t + rng.gauss(0, 0.3)
            end = begin + rng.gauss(0.2, 0.3)
            t += rng.uniform(0.0, 0.5)
        elif mode == "huge" and rng.random() < 0.1:
            begin, end = t, t + rng.uniform(5.0, 15.0)
            t = end
        else:
            begin = t
            end = t + rng.uniform(0.02, 0.6)
            t = end + rng.choice([0.0, 0.0, rng.uniform(0.0, 1.5)])
        words.append(Word(text, begin, end))  # sub-millisecond times on purpose

    seg_text = "".join(word.word for word in words)
    seg_end = max(word.end for word in words) if rng.random() < 0.8 else start - 0.5
    if rng.random() < 0.2:
        words = []  # no word timestamps: times are interpolated from the segment
        seg_end = start + rng.choice([rng.uniform(-0.5, 0.2), rng.uniform(0.5, 15.0)])
    return TranscriptionSegment(seg_id, start, seg_end, seg_text, words)


def random_transcript(rng: random.Random) -> TranscriptionResult:
    """An adversarial transcript of 0 to 12 segments."""
    segments: list[TranscriptionSegment] = []
    cursor = rng.uniform(-0.5, 3.0)
    for seg_id in range(rng.randint(0, 12)):
        seg = random_segment(rng, seg_id, cursor)
        segments.append(seg)
        cursor = max(seg.start, seg.end)
    return TranscriptionResult(language="en", duration=cursor + 2.0, segments=segments)


def test_seeded_random_adversarial_transcripts():
    """Scenario 16: 200 adversarial transcripts, fixed seed."""
    rng = random.Random(20260926)
    checked_subtitles = 0
    for case in range(200):
        result = random_transcript(rng)
        config = (
            OTHER_CONFIGS[case // 4 % len(OTHER_CONFIGS)]
            if case % 4 == 3
            else ProcessingConfig()
        )
        try:
            subtitles, report = process_transcription(result, config)
            check_output(result, subtitles, report, config)
        except AssertionError as exc:
            raise AssertionError(f"case {case} failed: {exc}\n{result!r}") from exc
        checked_subtitles += len(subtitles)
    assert checked_subtitles > 1000
