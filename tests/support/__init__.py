"""Shared HA-DocGen test helpers.

Imported only by tests. Production code must not depend on this package.
"""

from __future__ import annotations

from .assertions import (
    assert_directories_equal,
    assert_files_equal,
    assert_ordered,
    assert_text_equal,
)
from .benchmarks import (
    BenchmarkResult,
    format_results,
    measure,
    measure_memory,
    ordered_results,
)
from .builders import (
    AutomationBuilder,
    EntityBuilder,
    HomeAssistantModelBuilder,
    PackageBuilder,
    YamlRepositoryBuilder,
    build_relationship,
    build_sample_dependency_graph,
    build_sample_home_assistant_model,
    build_sample_yaml_repository,
    build_validation_result,
)
from .compare import (
    directories_equal,
    files_equal,
    normalise_text,
    ordered,
    relative_files,
)
from .filesystem import (
    build_project_tree,
    create_output_directory,
    create_sample_project,
    sample_project_files,
    write_text_files,
)
from .integration import (
    IntegrationPipeline,
    build_integration_pipeline,
    stable_report_metadata,
)
from .paths import require_relative_path
from .project_data import (
    integration_project_files,
    project_profile_files,
    runtime_config_text,
)
from .snapshots import assert_snapshot, read_snapshot, snapshot_path, write_snapshot

__all__ = [
    "AutomationBuilder",
    "BenchmarkResult",
    "EntityBuilder",
    "HomeAssistantModelBuilder",
    "IntegrationPipeline",
    "PackageBuilder",
    "YamlRepositoryBuilder",
    "assert_directories_equal",
    "assert_files_equal",
    "assert_ordered",
    "assert_snapshot",
    "assert_text_equal",
    "build_integration_pipeline",
    "build_project_tree",
    "build_relationship",
    "build_sample_dependency_graph",
    "build_sample_home_assistant_model",
    "build_sample_yaml_repository",
    "build_validation_result",
    "create_output_directory",
    "create_sample_project",
    "directories_equal",
    "files_equal",
    "format_results",
    "integration_project_files",
    "measure",
    "measure_memory",
    "normalise_text",
    "ordered",
    "ordered_results",
    "project_profile_files",
    "read_snapshot",
    "relative_files",
    "require_relative_path",
    "runtime_config_text",
    "sample_project_files",
    "snapshot_path",
    "stable_report_metadata",
    "write_snapshot",
    "write_text_files",
]
