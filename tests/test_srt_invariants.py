"""Tests for the SRT invariant checker test helper."""

import pytest
from srt_invariants import (
    Cue,
    SrtParseError,
    assert_valid_srt,
    check_cues,
    find_srt_violations,
    parse_srt,
    short_cues,
)

from subsync.models import ProcessingConfig

URL = "github.com/ikcode-dev/subsync/blob/main/README.md"

VALID = (
    "1\n"
    "00:00:01,000 --> 00:00:03,500\n"
    "Welcome to the show.\n"
    "\n"
    "2\n"
    "00:00:04,000 --> 00:00:08,000\n"
    "Today we install the package,\n"
    "then we run the tests.\n"
    "\n"
    "3\n"
    "01:02:03,456 --> 01:02:05,000\n"
    "See you next time.\n"
)


def violations_of(text: str | bytes) -> list[str]:
    """Return the violations for SRT given as text (encoded UTF-8) or bytes."""
    data = text.encode("utf-8") if isinstance(text, str) else text
    return find_srt_violations(data, ProcessingConfig())


def assert_single_violation(text: str | bytes, fragment: str) -> None:
    """Assert that exactly one violation is reported and it mentions fragment."""
    found = violations_of(text)
    assert len(found) == 1, found
    assert fragment in found[0], found


class TestParse:
    """parse_srt reads cues and rejects bad grammar."""

    def test_parses_valid_file(self) -> None:
        """Indices, times in ms and text lines are read."""
        cues = parse_srt(VALID.encode())
        assert [c.index for c in cues] == [1, 2, 3]
        assert (cues[0].start_ms, cues[0].end_ms) == (1000, 3500)
        assert cues[1].lines == [
            "Today we install the package,",
            "then we run the tests.",
        ]
        assert cues[2].start_ms == 3_723_456

    def test_bad_timestamp_raises(self) -> None:
        """A period instead of a comma is bad grammar."""
        with pytest.raises(SrtParseError, match="bad timing line"):
            parse_srt(VALID.replace("00:00:01,000", "00:00:01.000").encode())

    def test_bad_index_raises(self) -> None:
        """A non-numeric cue number is bad grammar."""
        with pytest.raises(SrtParseError, match="cue number"):
            parse_srt(VALID.replace("2\n00:00:04", "two\n00:00:04").encode())

    def test_missing_timing_line_raises(self) -> None:
        """A block with only an index is bad grammar."""
        with pytest.raises(SrtParseError, match="missing the timing line"):
            parse_srt(b"1\n")

    def test_tolerates_bom_and_crlf(self) -> None:
        """Format problems are reported by the checks, not by the parser."""
        data = b"\xef\xbb\xbf" + VALID.replace("\n", "\r\n").encode()
        assert len(parse_srt(data)) == 3


class TestValidFile:
    """A valid file passes every check."""

    def test_valid_three_cue_file(self) -> None:
        """Scenario 5: a 2-line cue and a time over 1 h, no violations."""
        assert violations_of(VALID) == []
        assert_valid_srt(VALID.encode())

    def test_long_url_alone_on_a_line(self) -> None:
        """Scenario 7: a 49-character single word on its own line is allowed."""
        assert len(URL) == 49
        text = VALID.replace("See you next time.", f"See you at\n{URL}")
        assert violations_of(text) == []

    def test_non_ascii_text(self) -> None:
        """Characters are counted as characters, not bytes."""
        line = "ZAŻÓŁĆ GĘŚLĄ JAŹŃ " * 2  # 36 characters, more than 42 bytes
        text = VALID.replace("Welcome to the show.", line.strip())
        assert violations_of(text) == []


class TestOneViolationPerMutation:
    """Scenario 6: each mutation reports exactly that violation."""

    def test_overlap(self) -> None:
        """Cue 2 starts before cue 1 ends."""
        assert_single_violation(
            VALID.replace("00:00:04,000 -->", "00:00:03,000 -->"), "overlaps"
        )

    def test_out_of_order(self) -> None:
        """Cue 2 starts before cue 1 starts."""
        text = VALID.replace(
            "00:00:04,000 --> 00:00:08,000", "00:00:00,100 --> 00:00:00,900"
        )
        assert_single_violation(text, "out of order")

    def test_gap_of_82_ms(self) -> None:
        """82 ms between cues is too close."""
        assert_single_violation(
            VALID.replace("00:00:04,000 -->", "00:00:03,582 -->"), "gap of 82 ms"
        )

    def test_gap_of_83_ms_is_fine(self) -> None:
        """83 ms is the minimum and is allowed."""
        assert (
            violations_of(VALID.replace("00:00:04,000 -->", "00:00:03,583 -->")) == []
        )

    def test_duration_of_7001_ms(self) -> None:
        """7001 ms is over the maximum."""
        assert_single_violation(
            VALID.replace("--> 00:00:08,000", "--> 00:00:11,001"), "7001 ms"
        )

    def test_duration_of_7000_ms_is_fine(self) -> None:
        """7000 ms is the maximum and is allowed."""
        assert (
            violations_of(VALID.replace("--> 00:00:08,000", "--> 00:00:11,000")) == []
        )

    def test_start_not_before_end(self) -> None:
        """A cue that ends when it starts is broken."""
        assert_single_violation(
            VALID.replace("--> 00:00:03,500", "--> 00:00:01,000"), "not before end"
        )

    def test_three_lines(self) -> None:
        """A third line is too many."""
        assert_single_violation(
            VALID.replace(
                "then we run the tests.\n", "then we run the tests.\nAgain.\n"
            ),
            "3 lines",
        )

    def test_no_lines(self) -> None:
        """A cue with a timing line and no text is broken."""
        assert_single_violation(VALID.replace("Welcome to the show.\n", ""), "0 lines")

    def test_43_character_two_word_line(self) -> None:
        """A 43-character line with a space is too long."""
        line = "a" * 21 + " " + "b" * 21
        assert len(line) == 43
        assert_single_violation(
            VALID.replace("Welcome to the show.", line), "43 characters"
        )

    def test_42_character_two_word_line_is_fine(self) -> None:
        """42 characters is the maximum and is allowed."""
        line = "a" * 20 + " " + "b" * 21
        assert violations_of(VALID.replace("Welcome to the show.", line)) == []

    def test_long_word_sharing_its_line(self) -> None:
        """A long word with other text on the same line is too long."""
        assert_single_violation(
            VALID.replace("See you next time.", f"See {URL}"), "characters is over"
        )

    def test_index_gap(self) -> None:
        """Indices must run 1..n."""
        assert_single_violation(
            VALID.replace("3\n01:02:03", "4\n01:02:03"), "index 4, expected 3"
        )

    def test_bom(self) -> None:
        """A UTF-8 BOM is not allowed."""
        assert_single_violation(b"\xef\xbb\xbf" + VALID.encode(), "BOM")

    def test_crlf(self) -> None:
        """CRLF line endings are not allowed."""
        assert_single_violation(VALID.replace("\n", "\r\n"), "carriage returns")

    def test_missing_final_newline(self) -> None:
        """The file must end with a newline."""
        assert_single_violation(VALID.rstrip("\n"), "does not end with a newline")

    def test_extra_final_newline(self) -> None:
        """The file must end with a single newline."""
        assert_single_violation(VALID + "\n", "more than one newline")

    def test_two_blank_lines_between_cues(self) -> None:
        """Cues are separated by exactly one blank line."""
        assert_single_violation(
            VALID.replace("\n\n2\n", "\n\n\n2\n"), "more than one blank line"
        )

    def test_bad_timestamp(self) -> None:
        """A bad timing line is reported as a parse error."""
        assert_single_violation(
            VALID.replace("00:00:01,000", "00:00:01.000"), "bad timing line"
        )

    def test_not_utf8(self) -> None:
        """Bytes that are not UTF-8 are reported."""
        assert_single_violation(VALID.encode("utf-16"), "not valid UTF-8")

    def test_empty_file(self) -> None:
        """An SRT file with no cues is not uploadable."""
        assert "contains no cues" in violations_of(b"")


class TestCheckCues:
    """check_cues inspects every cue, not just the first."""

    def test_violation_in_last_cue_is_found(self) -> None:
        """A problem after several valid cues is still reported."""
        cues = [
            Cue(1, 0, 1000, ["one"]),
            Cue(2, 2000, 3000, ["two"]),
            Cue(3, 4000, 12000, ["three"]),
        ]
        found = check_cues(cues, ProcessingConfig())
        assert len(found) == 1
        assert "cue 3" in found[0]

    def test_uses_config_limits(self) -> None:
        """Limits come from the config."""
        cues = [Cue(1, 0, 1000, ["a" * 10 + " " + "b" * 10])]
        assert check_cues(cues, ProcessingConfig(max_chars_per_line=20)) != []
        assert check_cues(cues, ProcessingConfig()) == []

    def test_assert_valid_srt_lists_all_violations(self) -> None:
        """assert_valid_srt raises with every violation listed."""
        text = VALID.replace("00:00:04,000 -->", "00:00:03,582 -->").replace(
            "3\n01:02:03", "4\n01:02:03"
        )
        with pytest.raises(AssertionError) as info:
            assert_valid_srt(text.encode())
        message = str(info.value)
        assert "2 violations" in message
        assert "gap of 82 ms" in message
        assert "index 4, expected 3" in message


class TestShortCues:
    """Scenario 8: short cues are listed, not reported as violations."""

    def test_500_ms_cue(self) -> None:
        """A 500 ms cue is listed by short_cues and is not a violation."""
        text = VALID.replace(
            "00:00:01,000 --> 00:00:03,500", "00:00:01,000 --> 00:00:01,500"
        )
        assert violations_of(text) == []
        short = short_cues(parse_srt(text.encode()), ProcessingConfig())
        assert [c.index for c in short] == [1]

    def test_833_ms_cue_is_not_short(self) -> None:
        """833 ms is the minimum and is not short."""
        text = VALID.replace(
            "00:00:01,000 --> 00:00:03,500", "00:00:01,000 --> 00:00:01,833"
        )
        assert short_cues(parse_srt(text.encode()), ProcessingConfig()) == []


def test_checker_does_not_import_processor_or_writer() -> None:
    """The checker is independent of the code it checks."""
    import srt_invariants

    source = open(srt_invariants.__file__, encoding="utf-8").read()
    assert "subsync.processor" not in source
    assert "subsync.writer" not in source
