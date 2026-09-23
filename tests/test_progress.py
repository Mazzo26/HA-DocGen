"""Tests for stateless execution progress reporting."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from ha_docgen import ProgressReporter


def test_progress_reporter_emits_deterministic_progress() -> None:
    """A valid progress update has stable, context-rich output."""
    logger = Mock()

    ProgressReporter().report(logger, completed=2, total=4, message="Analyze YAML")

    logger.info.assert_called_once_with("Progress [2/4] Analyze YAML")


@pytest.mark.parametrize(
    ("completed", "total"),
    ((-1, 1), (2, 1), (0, 0)),
)
def test_progress_reporter_rejects_invalid_bounds(
    completed: int,
    total: int,
) -> None:
    """Invalid progress cannot produce misleading output."""
    with pytest.raises(ValueError, match="progress"):
        ProgressReporter().report(Mock(), completed, total, "Invalid")
