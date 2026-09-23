"""Informational performance benchmarks for representative production workflows."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from ha_docgen import ProjectConfig, load_config
from ha_docgen import main as cli
from ha_docgen._pipeline import (
    _build_documents,
    _build_project_analysis,
    _build_registry_model,
    _build_relationships,
    _build_validations,
    _build_yaml_repository,
    _discover_project,
)
from ha_docgen.document import MarkdownExporter
from ha_docgen.graph import DependencyGraphBuilder
from ha_docgen.policy import ScanPolicy
from ha_docgen.project.builder import ProjectTreeBuilder
from ha_docgen.project.walker import FilesystemWalker
from tests.support.paths import REPOSITORY_ROOT, module_subprocess_env
from tests.support import (
    BenchmarkResult,
    format_results,
    measure,
    measure_memory,
    project_profile_files,
    runtime_config_text,
    stable_report_metadata,
    write_text_files,
)

_PROFILES = ("minimal", "typical", "larger")


@dataclass(frozen=True, slots=True)
class BenchmarkProject:
    """One configured representative project prepared outside measurements."""

    profile: str
    config_path: Path
    config: ProjectConfig


@pytest.fixture(params=_PROFILES, ids=_PROFILES)
def benchmark_project(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> BenchmarkProject:
    """Build one existing Module 11.3 project profile for benchmark use."""
    profile = str(request.param)
    root = write_text_files(tmp_path / profile, project_profile_files(profile))
    config_path = tmp_path / f"{profile}-config.yaml"
    config_path.write_text(
        runtime_config_text(root),
        encoding="utf-8",
        newline="\n",
    )
    return BenchmarkProject(profile, config_path, load_config(config_path))


@pytest.mark.benchmark
def test_project_discovery_benchmarks(benchmark_project: BenchmarkProject) -> None:
    """Measure filesystem scanning and ProjectTree construction separately."""
    config = benchmark_project.config
    entries = FilesystemWalker().walk(config.root)
    policy = ScanPolicy()
    included = tuple(entry for entry in entries if policy.is_included(entry.path))

    _emit(
        (
            measure(
                _name(benchmark_project, "discovery.scan"),
                lambda: FilesystemWalker().walk(config.root),
            ),
            measure(
                _name(benchmark_project, "discovery.tree"),
                lambda: ProjectTreeBuilder().build(config.root, included),
            ),
        )
    )


@pytest.mark.benchmark
def test_parsing_benchmarks(benchmark_project: BenchmarkProject) -> None:
    """Measure YAML, registry and combined production parsing."""
    config = benchmark_project.config
    tree = _discover_project(config)

    _emit(
        (
            measure(
                _name(benchmark_project, "parsing.yaml"),
                lambda: _build_yaml_repository(config, tree),
            ),
            measure(
                _name(benchmark_project, "parsing.registry"),
                lambda: _build_registry_model(config, tree),
            ),
            measure(
                _name(benchmark_project, "parsing.complete"),
                lambda: (
                    _build_registry_model(config, tree),
                    _build_yaml_repository(config, tree),
                ),
            ),
        )
    )


@pytest.mark.benchmark
def test_complete_pipeline_benchmarks(benchmark_project: BenchmarkProject) -> None:
    """Observe cold, warm and peak-memory complete production runs."""
    config = benchmark_project.config

    _emit(
        (
            measure(
                _name(benchmark_project, "pipeline.cold"),
                lambda: _build_project_analysis(config),
            ),
            measure(
                _name(benchmark_project, "pipeline.warm"),
                lambda: _build_project_analysis(config),
            ),
            measure_memory(
                _name(benchmark_project, "pipeline.memory"),
                lambda: _build_project_analysis(config),
            ),
        )
    )


@pytest.mark.benchmark
def test_relationship_benchmarks(benchmark_project: BenchmarkProject) -> None:
    """Measure relationship analysis and dependency graph construction."""
    config = benchmark_project.config
    tree = _discover_project(config)
    model = _build_registry_model(config, tree)
    yaml_repository = _build_yaml_repository(config, tree)
    relationships = _build_relationships(model, yaml_repository)

    _emit(
        (
            measure(
                _name(benchmark_project, "relationships.analysis"),
                lambda: _build_relationships(model, yaml_repository),
            ),
            measure(
                _name(benchmark_project, "relationships.graph"),
                lambda: DependencyGraphBuilder().build(relationships),
            ),
        )
    )


@pytest.mark.benchmark
def test_validation_benchmark(benchmark_project: BenchmarkProject) -> None:
    """Measure the complete production validation pipeline."""
    config = benchmark_project.config
    tree = _discover_project(config)
    model = _build_registry_model(config, tree)
    yaml_repository = _build_yaml_repository(config, tree)
    relationships = _build_relationships(model, yaml_repository)

    _emit(
        (
            measure(
                _name(benchmark_project, "validation.pipeline"),
                lambda: _build_validations(model, yaml_repository, relationships),
            ),
        )
    )


@pytest.mark.benchmark
def test_report_generation_benchmarks(benchmark_project: BenchmarkProject) -> None:
    """Measure the four representative production report generators."""
    analysis = _build_project_analysis(benchmark_project.config)
    metadata = stable_report_metadata()

    _emit(
        tuple(
            measure(
                _name(benchmark_project, f"reports.{command}"),
                lambda command=command: cli._generate_report_from_analysis(
                    command,
                    analysis,
                    metadata,
                ),
            )
            for command in ("health", "config", "architecture", "docs")
        )
    )


@pytest.mark.benchmark
def test_document_generation_benchmarks(
    benchmark_project: BenchmarkProject,
    tmp_path: Path,
) -> None:
    """Measure document generation and Markdown export."""
    config = benchmark_project.config
    tree = _discover_project(config)
    model = _build_registry_model(config, tree)
    yaml_repository = _build_yaml_repository(config, tree)
    relationships = _build_relationships(model, yaml_repository)
    documents = _build_documents(model, yaml_repository, relationships)
    output_directory = tmp_path / "markdown-output"

    _emit(
        (
            measure(
                _name(benchmark_project, "documents.generation"),
                lambda: _build_documents(model, yaml_repository, relationships),
            ),
            measure(
                _name(benchmark_project, "documents.markdown_export"),
                lambda: MarkdownExporter().export(documents, output_directory),
            ),
        )
    )


@pytest.mark.benchmark
def test_complete_cli_benchmark(benchmark_project: BenchmarkProject) -> None:
    """Measure complete CLI report execution against a temporary project."""
    _emit(
        (
            measure(
                _name(benchmark_project, "cli.complete"),
                lambda: _require_cli_success(benchmark_project.config_path),
            ),
        )
    )


def _name(project: BenchmarkProject, operation: str) -> str:
    """Return a stable profile-qualified benchmark name."""
    return f"{project.profile}.{operation}"


def _emit(results: tuple[BenchmarkResult, ...]) -> None:
    """Write deterministic structured samples for observational use."""
    sys.stdout.write(f"{format_results(results)}\n")


def _require_cli_success(config_path: Path) -> None:
    """Run the production CLI and raise only when execution itself fails."""
    subprocess.run(
        (
            sys.executable,
            "-m",
            "ha_docgen.main",
            "--quiet",
            "report",
            "health",
            "--config",
            str(config_path),
        ),
        cwd=REPOSITORY_ROOT,
        env=module_subprocess_env(),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
