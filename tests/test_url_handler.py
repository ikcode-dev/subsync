"""Tests for URL handler."""

import pytest
from subsync.url_handler import parse_youtube_url
from subsync.errors import URLParseError


def test_standard_watch_url():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_short_url():
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_embed_url():
    url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_legacy_embed_url():
    url = "https://www.youtube.com/v/dQw4w9WgXcQ"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_without_www():
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_http_not_https():
    url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_with_timestamp():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_with_playlist():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxyz"
    assert parse_youtube_url(url) == "dQw4w9WgXcQ"


def test_id_with_underscore():
    url = "https://www.youtube.com/watch?v=abc_def_123"
    assert parse_youtube_url(url) == "abc_def_123"


def test_id_with_hyphen():
    url = "https://www.youtube.com/watch?v=abc-def-123"
    assert parse_youtube_url(url) == "abc-def-123"


def test_non_youtube_url():
    url = "https://vimeo.com/12345"
    with pytest.raises(URLParseError, match="not a YouTube URL"):
        parse_youtube_url(url)


def test_missing_video_id():
    url = "https://www.youtube.com/watch"
    with pytest.raises(URLParseError, match="video ID"):
        parse_youtube_url(url)


def test_short_video_id():
    url = "https://www.youtube.com/watch?v=short"
    with pytest.raises(URLParseError, match="11 characters"):
        parse_youtube_url(url)


def test_long_video_id():
    url = "https://www.youtube.com/watch?v=wayTooLongVideoId"
    with pytest.raises(URLParseError, match="11 characters"):
        parse_youtube_url(url)


def test_invalid_chars_in_id():
    url = "https://www.youtube.com/watch?v=abc!def@123"
    with pytest.raises(URLParseError, match="11 characters"):
        parse_youtube_url(url)


def test_empty_url():
    url = ""
    with pytest.raises(URLParseError):
        parse_youtube_url(url)


def test_channel_url():
    url = "https://www.youtube.com/c/SomeChannel"
    with pytest.raises(URLParseError):
        parse_youtube_url(url)


def test_playlist_only_url():
    url = "https://www.youtube.com/playlist?list=PLxyz"
    with pytest.raises(URLParseError):
        parse_youtube_url(url)