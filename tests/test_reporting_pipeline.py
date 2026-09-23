"""Integration and golden tests for the complete reporting pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from tools.ha_docgen import main as cli
from tools.ha_docgen.diagnostics import collect_diagnostics
from tools.ha_docgen.reporting import (
    ConsoleRenderer,
    JsonRenderer,
    MarkdownRenderer,
    ReportMetadata,
)

_COMMANDS = (
    "health",
    "config",
    "architecture",
    "inventory",
    "dependencies",
    "performance",
    "docs",
)
_GOLDEN_DIRECTORY = Path(__file__).parent / "golden"


def _metadata() -> ReportMetadata:
    """Return stable metadata for deterministic pipeline output."""
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.1.0",
        project_path=Path("project"),
        execution_time=0.25,
    )


def _configure_cli(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Configure only external CLI inputs while retaining the real pipeline."""
    config = Mock(version="0.1.0", root=Path("project"))
    monkeypatch.setattr(cli, "load_config", Mock(return_value=config))
    monkeypatch.setattr(
        cli, "validate_runtime_configuration", Mock(return_value=())
    )
    monkeypatch.setattr(cli, "_report_metadata", Mock(return_value=_metadata()))
    return config


@pytest.mark.parametrize("command", _COMMANDS)
def test_every_report_object_renders_in_all_supported_formats(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    """All renderers accept the exact Report produced for each command."""
    config = _configure_cli(monkeypatch)
    report = cli._generate_report(command, config, collect_diagnostics())

    console = ConsoleRenderer().render(report)
    markdown = MarkdownRenderer().render(report)
    json_output = JsonRenderer().render(report)

    assert console.startswith(report.title)
    assert markdown.startswith(f"# {report.title}")
    assert json.loads(json_output)["title"] == report.title


@pytest.mark.parametrize("command", ("health", "config", "architecture"))
def test_console_output_matches_complete_golden_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    """Stable report output must match its complete committed golden file."""
    _configure_cli(monkeypatch)

    exit_code = cli.main(("report", command))
    output = capsys.readouterr().out
    expected = (_GOLDEN_DIRECTORY / f"{command}.txt").read_text(encoding="utf-8")

    assert exit_code == 0
    assert output == expected
