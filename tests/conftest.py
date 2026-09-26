"""Shared pytest fixtures for the SubSync test suite."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import pytest


@contextmanager
def isolated_root_logging() -> Iterator[None]:
    """Restore the root logger's handlers and level on exit.

    ``cli.main`` calls ``logging.basicConfig(..., force=True)`` so that ``-v``
    turns on DEBUG logging in the real CLI process. In-process tests share
    one root logger, so without this a ``-v`` test would leave DEBUG, and a
    handler bound to that test's closed ``capsys`` stream, for every later
    test.
    """
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    try:
        yield
    finally:
        root.handlers = handlers
        root.setLevel(level)


@pytest.fixture(autouse=True)
def _isolate_root_logging() -> Iterator[None]:
    """Run every test inside ``isolated_root_logging``."""
    with isolated_root_logging():
        yield
