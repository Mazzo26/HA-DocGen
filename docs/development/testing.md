# Testing

Shared test infrastructure for HA-DocGen lives only in `tools/ha_docgen/tests/`.

Production code must not import the test package. The helpers do not change
application behaviour and do not add test cases of their own.

Module 11 is complete. The suite covers shared infrastructure, unit tests,
integration tests, golden-file tests and informational performance
benchmarks.

---

# Directory structure

```text
tools/ha_docgen/tests/
├── conftest.py                      shared fixtures
├── support/
│   ├── __init__.py                  public test-helper exports
│   ├── builders.py                  model factories
│   ├── filesystem.py                temporary projects and project trees
│   ├── compare.py                   normalisation and comparison
│   ├── assertions.py                reusable assertions
│   ├── snapshots.py                 snapshot read, write and compare
│   ├── benchmarks.py                timing and memory samples
│   ├── integration.py               production-pipeline adapter
│   ├── project_data.py              representative project profiles
│   └── paths.py                     relative-path checks
├── golden/
│   ├── architecture.txt             console report golden files
│   ├── config.txt
│   ├── health.txt
│   └── integration/
│       ├── health.json
│       ├── documentation-index.txt
│       └── documents/               Markdown export golden files
├── test_integration_workflows.py    end-to-end workflows
├── test_performance_benchmarks.py   informational benchmarks
└── ...                              unit and component test modules
```

Pytest is configured in the repository `pyproject.toml`.

`testpaths` is `tools/ha_docgen/tests`.

---

# Pytest markers

Markers select subsets of the completed Module 11 suite. The full suite
remains `python -m pytest`.

| Marker | Purpose | Current use |
|--------|---------|-------------|
| `unit` | Isolated test of one component | YAML parser and repository unit modules |
| `integration` | Complete production workflow | `test_integration_workflows.py` |
| `snapshot` | Deterministic comparison with stored golden files | Golden-file tests in the integration suite |
| `benchmark` | Informational performance measurement | `test_performance_benchmarks.py` |

Not every isolated test is marked `unit`. Unmarked tests still run in the
full suite.

```bash
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m snapshot
python -m pytest -m benchmark
```

---

# Fixtures

Fixtures in `conftest.py` are opt-in and create a new value on every test.
Requesting one fixture does not change another.

| Fixture | Returns |
|---------|---------|
| `temporary_home_assistant_project` | Sample project directory |
| `temporary_output_directory` | Empty output directory |
| `sample_home_assistant_model` | In-memory `HomeAssistantModel` |
| `sample_yaml_repository` | In-memory `YamlRepository` |
| `sample_project_tree` | `ProjectTree` of an isolated sample project |
| `sample_dependency_graph` | Two-node `DependencyGraph` |
| `integration_home_assistant_project` | Representative filesystem project |
| `integration_project_config` | Production config for that project |
| `integration_pipeline` | Complete parsed, analysed and generated workflow |

The filesystem fixtures and the in-memory fixtures do not share objects.
The sample names match (`sample`, `sample_automation`, `light.sample`) so
tests can relate them.

---

# Builders

Import factories from `tools.ha_docgen.tests.support`.

```python
from tools.ha_docgen.tests.support import EntityBuilder, PackageBuilder

entity = EntityBuilder("light.kitchen").with_name("Kitchen").build()
package = PackageBuilder("lighting").build()
```

| Builder | Builds |
|---------|--------|
| `EntityBuilder` | `Entity` |
| `HomeAssistantModelBuilder` | `HomeAssistantModel` |
| `PackageBuilder` | `Package` with a `YamlDocument` |
| `AutomationBuilder` | `Automation` |
| `YamlRepositoryBuilder` | `YamlRepository` |

`build()` sorts collections by a stable key. Each builder instance keeps its
own configuration. There is no shared mutable builder state.

`build_sample_home_assistant_model()`, `build_sample_yaml_repository()` and
`build_sample_dependency_graph()` produce objects equivalent to the matching
fixtures. Each call returns a new instance.

---

# Filesystem helpers

`create_sample_project(root)` writes:

- `configuration.yaml`
- `packages/sample.yaml`

`write_text_files(root, files)` writes any relative UTF-8 mapping in sorted
path order. Absolute paths and `..` are rejected.

`build_project_tree(root)` reads an existing directory into a `ProjectTree`.
File modification times are fixed, so the tree does not depend on the clock.
Files and folders are ordered by relative POSIX path.

---

# Comparison and assertions

`normalise_text()` converts CRLF and CR to LF and removes trailing whitespace
from each line. Leading blank lines, trailing blank lines and a missing final
newline stay as they are. `ordered()` returns a sorted tuple. `files_equal()`
and `directories_equal()` compare that normalised UTF-8 text. Directory
listings are sorted.

Assertions raise `AssertionError`:

- `assert_text_equal`
- `assert_files_equal`
- `assert_directories_equal`
- `assert_ordered`

---

# Golden files

Committed golden files live under `tools/ha_docgen/tests/golden/`.

- `tests/golden/` stores console report goldens (`health.txt`, `config.txt`,
  `architecture.txt`).
- `tests/golden/integration/` stores representative end-to-end goldens:
  JSON and console reports plus Markdown export under
  `tests/golden/integration/documents/`.

`snapshots.py` provides the comparison helpers. `assert_snapshot()` only
reads and compares. It never writes. Call `write_snapshot()` to store or
replace a snapshot.

```python
from pathlib import Path

from tools.ha_docgen.tests.support import assert_snapshot

golden = Path("tools/ha_docgen/tests/golden/integration")
assert_snapshot(golden, "health.json", actual)
```

A missing snapshot fails the assertion. Snapshot changes are therefore
always explicit: normal pytest execution cannot create or replace golden
files.

---

# Integration tests

`test_integration_workflows.py` exercises the real production components
across filesystem scanning, YAML and registry parsing, relationship
analysis, dependency graph construction, validation, document/report
generation, rendering, export and the `python -m tools.ha_docgen.main`
process boundary.

The project data in `support/project_data.py` provides minimal, typical,
larger and edge-case profiles. `support/integration.py` adapts one
production analysis into an immutable `IntegrationPipeline`. Fixed report
metadata and project-relative POSIX provenance keep output independent of
clocks, temporary roots and operating system path separators.

Run only the integration and golden suites with:

```bash
python -m pytest -m integration
python -m pytest -m snapshot
```

---

# Benchmarks

`measure(name, action, iterations=1)` returns a frozen `BenchmarkResult`
with the total elapsed seconds. `measure_memory()` additionally records peak
traced memory in bytes. `ordered_results()` sorts samples by name and
`format_results()` serializes that order as structured JSON.

Run the informational benchmark suite from the repository root:

```bash
python -m pytest -m benchmark -s -q
```

`-s` exposes one JSON result array per benchmark case. Every sample contains
`name`, `elapsed_seconds`, `iterations` and `peak_bytes`; `peak_bytes` is
`null` for elapsed-time-only samples. Samples are sorted by their stable
profile-qualified name.

The suite reuses the `minimal`, `typical` and `larger` temporary project
profiles. Project construction happens before timing starts. It measures
production discovery and tree construction, YAML and registry parsing, the
complete parsing pipeline, cold/warm complete analysis, peak memory,
relationship analysis, dependency graph construction, validation,
Health/Configuration/Architecture/Documentation Index reports, document
generation, Markdown export and complete CLI execution.

Compare results only between equivalent environments and commands. A cold
run observes the first complete analysis in a case; the following warm run
may benefit from operating-system file caches but assumes no application
cache. Elapsed time and peak memory naturally vary by interpreter, operating
system, hardware and current load.

Benchmarks fail only when a production operation cannot complete. They never
assert `elapsed_seconds`, `peak_bytes`, ratios or hardcoded limits. The
measurements are therefore informational regression evidence, not a
pass/fail performance gate.
