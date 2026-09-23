"""Benchmark helper infrastructure.

Records elapsed time. This module does not define benchmarks and does not
assert timing thresholds, because wall-clock duration is not deterministic.
"""

from __future__ import annotations

import json
import tracemalloc
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """One observational timing sample."""

    name: str
    iterations: int
    elapsed_seconds: float
    peak_bytes: int | None = None


def measure(
    name: str,
    action: Callable[[], object],
    *,
    iterations: int = 1,
) -> BenchmarkResult:
    """Record total wall-clock time for ``iterations`` calls of ``action``."""
    _require_iterations(iterations)
    started = perf_counter()
    _repeat(action, iterations)
    elapsed = perf_counter() - started
    return BenchmarkResult(name=name, iterations=iterations, elapsed_seconds=elapsed)


def measure_memory(
    name: str,
    action: Callable[[], object],
    *,
    iterations: int = 1,
) -> BenchmarkResult:
    """Record elapsed time and peak traced memory for production work."""
    _require_iterations(iterations)
    tracemalloc.start()
    started = perf_counter()
    try:
        _repeat(action, iterations)
        elapsed = perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return BenchmarkResult(
        name=name,
        iterations=iterations,
        elapsed_seconds=elapsed,
        peak_bytes=peak_bytes,
    )


def ordered_results(
    results: Iterable[BenchmarkResult],
) -> tuple[BenchmarkResult, ...]:
    """Return benchmark samples sorted by name."""
    return tuple(sorted(results, key=lambda item: item.name))


def format_results(results: Iterable[BenchmarkResult]) -> str:
    """Serialize ordered benchmark samples as deterministic JSON."""
    samples = (
        {
            "name": result.name,
            "elapsed_seconds": result.elapsed_seconds,
            "iterations": result.iterations,
            "peak_bytes": result.peak_bytes,
        }
        for result in ordered_results(results)
    )
    return json.dumps(tuple(samples), separators=(",", ":"))


def _require_iterations(iterations: int) -> None:
    """Reject a non-positive iteration count."""
    if iterations < 1:
        raise ValueError("iterations must be at least 1")


def _repeat(action: Callable[[], object], iterations: int) -> None:
    """Call ``action`` exactly ``iterations`` times."""
    for _ in range(iterations):
        action()
