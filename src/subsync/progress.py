"""Progress reporting utilities for the SubSync pipeline.

This module provides a ProgressMapper that maps sub-task progress
(0.0–1.0) to a portion of overall pipeline progress, decoupling
progress display from pipeline logic.
"""

from collections.abc import Callable


class ProgressMapper:
    """Maps sub-task progress to a range within overall progress.

    Example:
        A download stage covering 5–50% of overall progress:

        >>> mapper = ProgressMapper(callback, start=0.05, end=0.50, stage="Downloading")
        >>> mapper.update(0.0)   # callback(0.05, "Downloading")
        >>> mapper.update(0.5)   # callback(0.275, "Downloading")
        >>> mapper.complete()    # callback(0.50, "Downloading")
    """

    def __init__(
        self,
        callback: Callable[[float, str], None] | None,
        start: float,
        end: float,
        stage: str,
    ) -> None:
        """Initialize the progress mapper.

        Args:
            callback: Progress callback or None for no-op.
            start: Start of the progress range (0.0–1.0).
            end: End of the progress range (0.0–1.0).
            stage: Human-readable stage name.
        """
        self._callback = callback
        self._start = start
        self._end = end
        self._stage = stage

    def update(self, fraction: float) -> None:
        """Report progress within this stage's range.

        Args:
            fraction: Sub-task progress from 0.0 to 1.0.
        """
        if self._callback is None:
            return

        mapped = self._start + (self._end - self._start) * fraction
        self._callback(mapped, self._stage)

    def complete(self) -> None:
        """Report this stage as complete (progress = end value)."""
        if self._callback is None:
            return

        self._callback(self._end, self._stage)
