"""YouTube URL parsing utilities."""

import re
from urllib.parse import urlparse, parse_qs

from subsync.errors import URLParseError


def parse_youtube_url(url: str) -> str:
    """Extract video ID from YouTube URL.

    Args:
        url: A YouTube video URL in any supported format.

    Returns:
        The 11-character video ID.

    Raises:
        URLParseError: If URL is invalid, not YouTube, or missing video ID.
    """
    if not url:
        raise URLParseError("URL is empty")

    try:
        parsed = urlparse(url)
    except ValueError:
        raise URLParseError("Invalid URL format")

    netloc = parsed.netloc.lower()
    if netloc not in ['youtube.com', 'www.youtube.com', 'youtu.be']:
        raise URLParseError("not a YouTube URL")

    path = parsed.path
    query = parsed.query

    video_id = None

    if netloc == 'youtu.be':
        # youtu.be/VIDEO_ID
        if path.startswith('/'):
            parts = path.split('/')
            if len(parts) >= 2:
                video_id = parts[1]
    elif netloc in ['youtube.com', 'www.youtube.com']:
        if path == '/watch':
            # youtube.com/watch?v=VIDEO_ID
            params = parse_qs(query)
            video_id = params.get('v', [None])[0]
        elif path.startswith('/embed/'):
            # youtube.com/embed/VIDEO_ID
            parts = path.split('/')
            if len(parts) >= 3:
                video_id = parts[2]
        elif path.startswith('/v/'):
            # youtube.com/v/VIDEO_ID
            parts = path.split('/')
            if len(parts) >= 3:
                video_id = parts[2]

    if not video_id:
        raise URLParseError("video ID")

    # Validate video ID
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        raise URLParseError("11 characters")

    return video_id