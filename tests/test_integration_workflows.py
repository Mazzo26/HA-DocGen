"""End-to-end integration, golden-file and regression tests."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from tools.ha_docgen import ProjectConfig
from tools.ha_docgen import main as cli
from tools.ha_docgen.config import load_config
from tools.ha_docgen.document import MarkdownExporter
from tools.ha_docgen.reporting import ConsoleRenderer, JsonRenderer, MarkdownRenderer
from tools.ha_docgen.scanner import Scanner
from tools.ha_docgen.tests.support import (
    IntegrationPipeline,
    assert_snapshot,
    build_integration_pipeline,
    project_profile_files,
    runtime_config_text,
    stable_report_metadata,
    write_text_files,
)

pytestmark = pytest.mark.integration

_GOLDEN_DIRECTORY = Path(__file__).parent / "golden" / "integration"
_PROFILE_COUNTS = (
    ("minimal", (2, 1)),
    ("typical", (4, 2)),
    ("larger", (12, 10)),
    ("edge", (5, 3)),
)
_REPORT_TITLES = (
    "Health Report",
    "Configuration Report",
    "Architecture Report",
    "Inventory Report",
    "Dependency Report",
    "Documentation Index Report",
)
_CLI_REPORTS = (
    ("health", "sensor.orphan"),
    ("config", "Light: light.kitchen"),
    ("architecture", "Module: lighting"),
    ("inventory", "Entity: light.kitchen"),
    ("dependencies", "mqtt_topic:home/evening"),
    ("performance", "Project path"),
    ("docs", "Generated documentation: Package: lighting"),
)


@pytest.mark.parametrize(("profile", "expected"), _PROFILE_COUNTS)
def test_project_profiles_scan_deterministically(
    tmp_path: Path,
    profile: str,
    expected: tuple[int, int],
) -> None:
    """Minimal, typical, larger and edge projects use the real scanner."""
    root = write_text_files(tmp_path / profile, project_profile_files(profile))
    config_file = _write_runtime_config(tmp_path, root, profile)
    config = load_config(config_file)

    first = Scanner(config).scan()
    second = Scanner(config).scan()

    assert (first.scan.yaml_files, first.scan.package_count) == expected
    assert first.scan == second.scan
    assert first.folders == second.folders


def test_complete_analysis_pipeline_connects_all_layers(
    integration_pipeline: IntegrationPipeline,
) -> None:
    """Discovery, loading, parsing, analysis and validation interact correctly."""
    pipeline = integration_pipeline

    assert len(pipeline.project_tree.folders) == 4
    assert len(pipeline.model.entities) == 4
    assert len(pipeline.yaml_repository.packages) == 2
    assert len(pipeline.yaml_repository.automations) == 2
    assert len(pipeline.yaml_repository.scripts) == 1
    assert len(pipeline.yaml_repository.dashboards) == 1
    assert len(pipeline.relationships.relationships) == len(pipeline.graph.edges)
    assert pipeline.validation_report.total_findings() == 1
    assert pipeline.validation_report.info_count() == 1


def test_complete_report_generation_has_stable_structure(
    integration_pipeline: IntegrationPipeline,
) -> None:
    """Every complete report exposes its title, summary and content sections."""
    reports = integration_pipeline.reports

    assert tuple(report.title for report in reports) == _REPORT_TITLES
    assert all(report.summary for report in reports)
    assert all(report.sections for report in reports)
    assert all(report.statistics for report in reports)
    assert {section.title for report in reports for section in report.sections} >= {
        "Summary",
        "Statistics",
    }


@pytest.mark.snapshot
@pytest.mark.parametrize(
    ("name", "render"),
    (
        (
            "health.json",
            lambda pipeline: JsonRenderer().render(pipeline.reports[0]),
        ),
        (
            "documentation-index.txt",
            lambda pipeline: ConsoleRenderer().render(pipeline.reports[-1]),
        ),
    ),
)
def test_complete_outputs_match_golden_files(
    integration_pipeline: IntegrationPipeline,
    name: str,
    render: Callable[[IntegrationPipeline], str],
) -> None:
    """Representative Markdown, JSON and console output is read-only golden data."""
    actual = render(integration_pipeline)
    assert_snapshot(_GOLDEN_DIRECTORY, name, actual)


@pytest.mark.snapshot
def test_documentation_export_creates_complete_stable_output(
    integration_pipeline: IntegrationPipeline,
    temporary_output_directory: Path,
) -> None:
    """The generated document repository exports a complete deterministic index."""
    MarkdownExporter().export(
        integration_pipeline.documents,
        temporary_output_directory,
    )
    names = tuple(sorted(path.name for path in temporary_output_directory.iterdir()))

    assert names == (
        "automation-arrival.md",
        "automation-climate-notice.md",
        "dashboard-main.md",
        "entity-binary_sensor.door.md",
        "entity-light.kitchen.md",
        "entity-sensor.orphan.md",
        "entity-sensor.temperature.md",
        "home-assistant-configuration.md",
        "index.md",
        "package-climate.md",
        "package-lighting.md",
    )
    for name in ("index.md", "package-lighting.md"):
        actual = (temporary_output_directory / name).read_text(encoding="utf-8")
        assert_snapshot(_GOLDEN_DIRECTORY / "documents", name, actual)


def test_identical_input_produces_identical_complete_output(
    integration_project_config: ProjectConfig,
) -> None:
    """Repeated complete execution preserves ordering, metadata and formatting."""
    first = build_integration_pipeline(integration_project_config)
    second = build_integration_pipeline(integration_project_config)

    render = MarkdownRenderer()
    assert first.relationships.relationships == second.relationships.relationships
    assert first.validations.results == second.validations.results
    assert first.documents.documents == second.documents.documents
    assert tuple(map(render.render, first.reports)) == tuple(
        map(render.render, second.reports)
    )


@pytest.mark.parametrize(("command", "expected_content"), _CLI_REPORTS)
def test_real_cli_report_workflows_are_deterministic(
    tmp_path: Path,
    integration_home_assistant_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    expected_content: str,
) -> None:
    """Every CLI report contains data from the configured temporary project."""
    config_file = _write_runtime_config(
        tmp_path,
        integration_home_assistant_project,
        "cli",
    )
    monkeypatch.setattr(cli, "_report_metadata", lambda *_: stable_report_metadata())
    arguments = ("--quiet", "report", command, "--config", str(config_file))

    first_code = cli.main(arguments)
    first_output = capsys.readouterr().out
    second_code = cli.main(arguments)
    second_output = capsys.readouterr().out

    assert first_code == second_code == cli.EXIT_SUCCESS
    assert first_output == second_output
    assert expected_content in first_output


def test_real_cli_scan_validate_and_output_override_workflows(
    tmp_path: Path,
    integration_home_assistant_project: Path,
) -> None:
    """Real scan and validate commands accept config and output paths."""
    config_file = _write_runtime_config(
        tmp_path,
        integration_home_assistant_project,
        "workflow",
    )
    output = tmp_path / "generated"

    assert cli.main(("--quiet", "--config", str(config_file))) == cli.EXIT_SUCCESS
    assert cli.main(("--quiet", "validate", "--config", str(config_file))) == cli.EXIT_SUCCESS
    assert (
        cli.main(
            (
                "--quiet",
                "report",
                "health",
                "--config",
                str(config_file),
                "--output",
                str(output),
            )
        )
        == cli.EXIT_SUCCESS
    )


@pytest.mark.parametrize(
    ("command", "expected_output"),
    (
        ((), ""),
        (("validate",), ""),
        (("report", "health"), "Health Report\n"),
    ),
)
def test_module_entrypoint_executes_real_process_workflows(
    tmp_path: Path,
    integration_home_assistant_project: Path,
    command: tuple[str, ...],
    expected_output: str,
) -> None:
    """The installed module boundary executes scan, validate and report commands."""
    config_file = _write_runtime_config(
        tmp_path,
        integration_home_assistant_project,
        "process",
    )
    result = subprocess.run(
        (
            sys.executable,
            "-m",
            "tools.ha_docgen.main",
            "--quiet",
            *command,
            "--config",
            str(config_file),
        ),
        cwd=Path(__file__).parents[3],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == cli.EXIT_SUCCESS
    assert result.stderr == ""
    assert result.stdout.startswith(expected_output)


def _write_runtime_config(
    directory: Path,
    root: Path,
    name: str,
) -> Path:
    """Write one complete CLI configuration and return its path."""
    path = directory / f"{name}.yaml"
    path.write_text(runtime_config_text(root), encoding="utf-8", newline="\n")
    return path
