"""Shared pytest fixtures for the SubSync test suite."""

import logging
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest


@contextmanager
def isolated_root_logging() -> Iterator[None]:
    """Restore the root logger's handlers and level, and SubSync's level, on exit.

    ``cli.main`` calls ``logging.basicConfig(..., force=True)`` so that ``-v``
    turns on DEBUG logging in the real CLI process. In-process tests share
    one root logger, so without this a ``-v`` test would leave DEBUG, and a
    handler bound to that test's closed ``capsys`` stream, for every later
    test.
    """
    root = logging.getLogger()
    package = logging.getLogger("subsync")
    handlers = list(root.handlers)
    level = root.level
    package_level = package.level
    try:
        yield
    finally:
        root.handlers = handlers
        root.setLevel(level)
        package.setLevel(package_level)


@pytest.fixture(autouse=True)
def _isolate_root_logging() -> Iterator[None]:
    """Run every test inside ``isolated_root_logging``."""
    with isolated_root_logging():
        yield


@pytest.fixture
def run_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the process temp folder at a fresh, empty test folder.

    ``pipeline_temp_dir`` creates ``subsync_*`` folders there, so a test can
    assert that none is left behind. Both ``TMPDIR`` and the cached
    ``tempfile.tempdir`` are set, since the latter wins once computed.
    """
    folder = tmp_path / "run-tmp"
    folder.mkdir()
    monkeypatch.setenv("TMPDIR", str(folder))
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder
