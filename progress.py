"""Stateless execution progress reporting."""

from __future__ import annotations

from .logging import Logger


class ProgressReporter:
    """Report validated progress updates through an explicit logger."""

    def report(
        self,
        logger: Logger,
        completed: int,
        total: int,
        message: str,
    ) -> None:
        """Emit one deterministic progress update."""
        if total <= 0 or completed < 0 or completed > total:
            raise ValueError("Invalid progress bounds.")
        logger.info(f"Progress [{completed}/{total}] {message}")
