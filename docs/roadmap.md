# HA-DocGen Roadmap

## Purpose

This roadmap describes the planned evolution of HA-DocGen.

Development is organised into modules. Each module builds upon the previous one while maintaining a stable and testable architecture.

The Home Assistant installation roadmap (platform phases) lives separately in:

```
docs/roadmap.md
```

---

# Module 1 – Foundation

## Status

✅ Completed

### Objectives

- Python project structure
- Git repository
- Virtual environment
- Development tooling
- Coding standards
- Documentation structure

---

# Module 2 – Repository Discovery

## Status

✅ Completed

### Objectives

- Filesystem traversal
- Folder discovery
- File discovery
- Repository abstraction
- Initial scanner framework

---

# Module 3 – ProjectTree

## Status

✅ Completed

### 3.1 FilesystemEntry

✅ Completed

### 3.2 ProjectTree

✅ Completed

### 3.3 ProjectTreeBuilder

✅ Completed

### 3.4 Shared Constants

✅ Completed

### 3.5 Logging & Diagnostics

✅ Completed

### 3.6 ScanPolicy

✅ Completed

### 3.7 Ignore Rules

✅ Completed

---

# Module 4 – Home Assistant Model

## Status

✅ Completed

### 4.1 Storage Scanner
✅ Completed

### 4.2 Storage Inventory
✅ Completed

### 4.3 Entity Registry
✅ Completed

### 4.4 Device Registry
✅ Completed

### 4.5 Area Registry
✅ Completed

### 4.6 Label Registry
✅ Completed

### 4.7 Floor Registry
✅ Completed

### 4.8 Config Entries
✅ Completed

### 4.9 HomeAssistantModel
✅ Completed

---

# Module 5 – YAML Analysis

## Status

✅ Completed

### 5.1 YAML Document
✅ Completed

### 5.2 YAML Loader
✅ Completed

### 5.3 Package Scanner
✅ Completed

### 5.4 Package Model
✅ Completed

### 5.5 Package Parser
✅ Completed

### 5.6 Section Model
✅ Completed

### 5.7 Automation Parser
✅ Completed

### 5.8 Script Parser
✅ Completed

### 5.9 Scene Parser
✅ Completed

### 5.10 Helper Parser
✅ Completed

### 5.11 Dashboard Parser
✅ Completed

### 5.12 Blueprint Parser
✅ Completed

### 5.13 Template Parser
✅ Completed

### 5.14 YAML Model Repository
✅ Completed

### 5.15 Domain Package Provenance
✅ Completed

---

# Module 6 – Relationship Analysis

## Status

✅ Completed

### 6.1 Relationship Models
✅ Completed

### 6.2 Entity Relationships
✅ Completed

### 6.3 Device Relationships
✅ Completed

### 6.4 Automation Relationships
✅ Completed

- Entity references
- Device references
- Area references
- Script references
- Scene references
- Automation references

### 6.5 Script Relationships
✅ Completed

- Entity references
- Script references
- Scene references

### 6.6 Dashboard Relationships
✅ Completed

- Entity references
- Device references

### 6.7 MQTT Relationships
✅ Completed

- Publish Topics
- Subscribe Topics
- MQTT Topic References

### 6.8 Relationship Repository
✅ Completed

- Immutable relationship repository
- Read-only lookup API

### 6.9 Dependency Graph
✅ Completed

- Immutable DependencyGraph (nodes + edges)
- Stateless DependencyGraphBuilder
- Read-only lookup API (`outgoing`, `incoming`, `contains`)
- Entity/Package views via ObjectType filter (no separate graph models)

---

# Module 7 – Documentation Generation

## Status

✅ Completed

### 7.1 Documentation Models
✅ Completed

- Immutable Document / Section / DocumentItem models
- Paragraph, Table, CodeBlock, BulletList
- Output-independent (no Markdown / HTML / JSON)

### 7.2 Markdown Builder
✅ Completed

- Stateless `MarkdownBuilder.build(document) -> str`
- Renders Document / Section / Paragraph / Table / CodeBlock / BulletList
- Document models only — no HA knowledge, generators or filesystem

### 7.3 Package Documentation
✅ Completed

- Stateless `PackageDocumentGenerator.generate(...) -> Document`
- One Package → one Document (Overview, Sections, Helpers, Automations,
  Scripts, Scenes, Templates)
- Filters domain objects by `object.package == package`
- Document models only — no Markdown, filesystem, repository or index

### 7.4 Entity Documentation
✅ Completed

- Stateless `EntityDocumentGenerator.generate(entity, relationships) -> Document`
- One Entity → one Document (Overview, Registry, Relationships)
- Uses only the Entity and an explicit `tuple[Relationship, ...]`
- Document models only — no Markdown, filesystem, repository, graph or
  HomeAssistantModel

### 7.5 Automation Documentation
✅ Completed

- Stateless `AutomationDocumentGenerator.generate(automation, relationships) -> Document`
- One Automation → one Document (Overview, Triggers, Conditions, Actions,
  Relationships)
- Uses only the Automation and an explicit `tuple[Relationship, ...]`
- Triggers / Conditions / Actions read explicit types from `Automation.raw`
- Document models only — no Markdown, filesystem, repository, graph or
  HomeAssistantModel

### 7.6 Dashboard Documentation
✅ Completed

- Stateless `DashboardDocumentGenerator.generate(dashboard, relationships) -> Document`
- One Dashboard → one Document (Overview, Views, Relationships)
- Uses only the Dashboard and an explicit `tuple[Relationship, ...]`
- Overview shows present first-class fields; Views list view titles from
  `Dashboard.views` metadata only; Relationships render
  `{type} → {target_type}:{target_id}` in given order
- Document models only — no Markdown, filesystem, repository, graph or
  HomeAssistantModel

### 7.7 Configuration Documentation
✅ Completed

- Stateless `ConfigurationDocumentGenerator.generate(model,
  yaml_repository, relationship_repository) -> Document`
- One configuration-wide Document (Overview, Registries, YAML,
  Relationships, Statistics)
- Uses only `HomeAssistantModel`, `YamlRepository` and
  `RelationshipRepository` collection lengths / type counts
- Document models only — no Markdown, filesystem, parsing, analysis,
  graph or repository mutation

### 7.8 Documentation Repository
✅ Completed

- Immutable `DocumentRepository` of already-generated `Document` objects
- Deduplicates and sorts by `Document.title`; `MappingProxyType` `_by_title`
- Read-only O(1) lookups: `document`, `documents_by_title`; field `documents`
- No generation, rendering, Markdown, filesystem, graph or exporters

### 7.9 Markdown Export
✅ Completed

- Stateless `MarkdownExporter.export(repository, output_directory)`
- One `.md` file per `Document` via existing `MarkdownBuilder`
- Deterministic filenames from `Document.title`; creates output directory
- Generates `index.md` with links to all repository documents

---

# Module 8 – Validation

## Status

✅ Completed

### 8.1 Validation Models
✅ Completed

- Immutable validation models
- Validation severity
- Validation result collection

### 8.2 Entity Validation
✅ Completed

- Stateless `EntityValidator.validate(entities, relationship_repository)
  -> tuple[ValidationResult, ...]`
- Explicit checks only: no relationships, empty target, empty entity ID,
  duplicate entity ID
- Deterministic sorted, deduplicated immutable tuple
- No validation engine, repository, reports, Markdown or filesystem

### 8.3 Automation Validation
✅ Completed

- Stateless `AutomationValidator.validate(automations,
  relationship_repository) -> tuple[ValidationResult, ...]`
- Explicit checks only: empty automation ID, empty alias, no
  relationships, empty relationship target, duplicate automation ID
- Deterministic sorted, deduplicated immutable tuple
- No validation engine, repository, reports, Markdown or filesystem

### 8.4 Dashboard Validation
✅ Completed

- Missing entities
- Missing devices
- Invalid cards

### 8.5 Package Validation
✅ Completed

- Duplicate automations
- Duplicate helpers
- Duplicate scripts
- Duplicate templates

### 8.6 MQTT Validation
✅ Completed

- Missing topics
- Duplicate topics
- Publish / Subscribe consistency

### 8.7 Validation Repository
✅ Completed

- Immutable validation repository
- Read-only lookup API

### 8.8 Validation Report
✅ Completed

- Build validation summary
- Statistics
- Severity totals
- Ready for Markdown export

---

# Module 9 – Reporting

## Status

✅ Completed

### 9.1 Report Domain Models
✅ Completed

- Immutable Report / ReportSection / ReportMetadata models
- Severity StrEnum (INFO, WARNING, ERROR)
- Output-independent (no Markdown / HTML / JSON / CLI)

### 9.2 Health Report
✅ Completed

- Stateless `HealthReportGenerator.generate(repository, metadata) -> Report`
- Aggregates `ValidationRepository` findings into Report domain models
- Summary, statistics, Validation Summary / Errors / Warnings /
  Informational sections, and derived recommendations
- Report models only — no Markdown, JSON, console, filesystem or CLI

---

## 9.3 Configuration Report

### Status

✅ Completed

### Objectives

Generate:

- Entity inventory
- Automations
- Scripts
- Helpers
- MQTT
- Packages
- Summary statistics

- Unit tests

---

## 9.4 Architecture Report

### Status

✅ Completed

### Objectives

Generate:

- Modules
- Dependencies
- Layer violations
- Architecture summary

- Unit tests

---

## 9.5 Inventory Report

### Status

✅ Completed

### Objectives

Generate:

- Entities
- Integrations
- Domains
- Packages
- File inventory

- Unit tests

---

## 9.6 Dependency Report

### Status

✅ Completed

### Objectives

Generate:

- Module dependencies
- Circular dependencies
- External dependencies
- Dependency graph

- Unit tests

---

## 9.7 Performance Report

### Status

✅ Completed

### Objectives

Generate:

- Scan duration
- Validator timings
- Slow files
- Performance statistics

- Unit tests

---

## 9.8 Documentation Index

### Status

✅ Completed

### Objectives

- Stateless `DocumentationIndexReportGenerator.generate(model,
  yaml_repository, document_repository, relationship_repository, metadata)
  -> Report`
- Documentation inventory, generated document/index entries, existing cross
  references, statistics and derived recommendations
- Uses existing immutable repositories only; unavailable generated-file and
  documentation-health metadata is not invented
- Report models only — no scanning, rendering, filesystem writes or CLI

---

## 9.9 Console Renderer

### Status

✅ Completed

### Objectives

- Plain text renderer
- Tables
- Summary blocks
- Optional ANSI colour support

- Unit tests

---

## 9.10 Markdown Renderer

### Status

✅ Completed

### Objectives

- Markdown renderer
- Headings
- Tables
- Code blocks
- Links

- Unit tests

---

## 9.11 JSON Renderer

### Status

✅ Completed

### Objectives

- JSON serialization
- Metadata export
- Statistics export
- CI-friendly output

- Unit tests

---

## 9.12 CLI Integration

### Status

✅ Completed

### Objectives

Commands:

- report health
- report config
- report architecture
- report inventory
- report dependencies
- report performance
- report docs

- CLI integration tests

---

## 9.13 Reporting Infrastructure

### Status

Not Required

### Objectives

Introduce shared infrastructure only when required by multiple report implementations:

- Report registry
- Report builder interface
- Report generator
- Common reporting utilities

Refactor only when duplication justifies abstraction.

- Unit tests

---

## 9.14 End-to-End Tests

### Status

✅ Completed

### Objectives

- Integration tests
- Snapshot tests
- CLI tests
- Golden file tests

---

# Module 10 – Command Line Interface

## Status

✅ Completed

---

## Objectives

- Build a professional command line interface
- Centralize command dispatching
- Add structured logging and progress reporting
- Validate configuration before execution
- Support verbose and debug execution
- Implement incremental scanning and execution
- Improve execution performance for large projects

---

## Module 10.1 – CLI Foundation

**Status:** ✅ Completed

### Objectives

- Create CLI entrypoint
- Implement argument parser
- Implement command dispatcher
- Introduce shared CLI context
- Standardize exit codes
- Centralize error handling
- Generate help output
- Add version command

### Deliverables

- CLI package
- Main entrypoint
- Argument parser
- Dispatcher
- Context object
- Exit code definitions
- Help generation
- Version command

---

## Module 10.2 – Logging & Progress Reporting

**Status:** ✅ Completed

### Objectives

- Implement centralized logging
- Add console logger
- Support quiet mode
- Support verbose mode
- Support debug mode
- Report execution progress
- Measure execution timings
- Print execution summary

### Deliverables

- Logger abstraction
- Console logger
- Progress reporter
- Timing utilities
- Execution summary
- CLI options:
  - `--quiet`
  - `--verbose`
  - `--debug`

---

## Module 10.3 – Configuration Validation

**Status:** ✅ Completed

### Objectives

- Load configuration
- Validate configuration
- Validate project paths
- Validate output directories
- Validate runtime environment
- Prevent execution with invalid configuration

### Deliverables

- Configuration loader
- Configuration validator
- Path validator
- Environment validator
- Output validator
- `validate` CLI command
- CLI options:
  - `--config`
  - `--output`

---

## Module 10.4 – Incremental Execution

**Status:** ✅ Completed

### Objectives

- Detect modified files
- Skip unchanged files
- Cache project fingerprints
- Cache file hashes
- Support dependency invalidation
- Improve execution speed

### Deliverables

- Incremental scanner
- Change detector
- Cache manager
- Fingerprint storage
- File hashing
- Dependency invalidation
- CLI options:
  - `--incremental`
  - `--force`
  - `--clean-cache`

---

## Completion Criteria

Module 10 is complete when:

- [x] CLI entrypoint is fully operational
- [x] All report commands execute through the dispatcher
- [x] Help and version commands are available
- [x] Logging is centralized
- [x] Quiet, verbose and debug modes function correctly
- [x] Progress reporting is implemented
- [x] Configuration validation prevents invalid execution
- [x] Incremental execution correctly skips unchanged files
- [x] Cache management is deterministic
- [x] Exit codes are standardized
- [x] Documentation has been updated
- [x] All tests pass
- [x] No coverage threshold is configured; the full test suite is the coverage gate

---

# Module 11 – Testing

## Status

✅ Completed

### Objectives

- Shared test infrastructure
- Comprehensive unit test suite
- Integration and snapshot testing
- Performance benchmarking

---

## 11.1 Test Infrastructure

### Status

✅ Completed

### Deliverables

- Standardised pytest configuration
- Shared fixtures (`conftest.py`)
- Test data builders and factories
- Temporary project helpers
- Snapshot utilities
- Benchmark utilities
- Common test assertions
- Testing documentation

---

## 11.2 Unit Tests

### Status

✅ Completed

### Deliverables

- Domain model tests
- Validation tests
- Parser tests
- Repository tests
- Dependency graph tests
- Reporting tests
- Renderer tests
- CLI tests
- Coverage reporting

---

## 11.3 Integration & Snapshot Tests

### Status

✅ Completed

### Deliverables

- End-to-end project execution tests
- Complete CLI workflow tests
- Multi-project integration tests
- Snapshot (golden file) tests
- Deterministic output verification
- Regression test suite

---

## 11.4 Performance Benchmarks

### Status

✅ Completed

### Deliverables

- Benchmark framework
- Cold run benchmarks
- Warm run benchmarks
- Large project benchmarks
- Memory usage benchmarks
- Performance regression detection
- Benchmark documentation

---

## Acceptance Criteria

- Shared test infrastructure is reused by all test modules.
- Unit tests cover all public functionality.
- Integration tests validate complete DocGen workflows.
- Snapshot tests produce deterministic output.
- Benchmarks are repeatable and documented.
- No duplicated test helpers or fixtures.
- All tests pass in CI.

---

# Module 12 – Release

## Status

✅ Completed

### Objectives

- GitHub Actions
- Automated testing
- Versioning
- Package distribution
- Release documentation

---

## 12.1 CI Infrastructure

### Status

✅ Completed

### Objectives

- GitHub Actions quality workflow
- Install HA-DocGen and cache pip dependencies
- Run Ruff and the full pytest suite
- Collect coverage
- Fail the job on the first failed quality gate

---

## 12.2 Package Build & Distribution

### Status

✅ Completed

### Objectives

- Source distribution (sdist)
- Wheel distribution
- Authoritative package metadata in `pyproject.toml`
- Package discovery without tests or development artifacts
- Installation from generated artifacts
- Build verification without publishing

---

## 12.3 Version Management

### Status

✅ Completed

### Objectives

- Single authoritative application version in `version.py`
- Semantic version validation
- CLI, package and distribution metadata consistency
- Version retrieval independent of Git
- Version documentation

## 12.4 Release Automation

### Status

✅ Completed

### Objectives

- Automate release workflow
- Generate release artifacts
- Publish build outputs
- Validate release pipeline

Completion Criteria

- Release workflow completes successfully
- Artifacts are uploaded
- Release process is repeatable

---

## 12.5 Release Documentation

### Status

✅ Completed

### Objectives

- Create release procedure
- Document versioning policy
- Document publishing process
- Document recovery procedure
- Update README and roadmap

Completion Criteria

- Release process fully documented
- New contributor can perform a release
- Documentation reviewed and consistent

---

## 12.6 End-to-End Validation

### Status

✅ Completed

### Objectives

- Validate complete release workflow
- Verify CI from clean checkout
- Verify package installation
- Verify generated artifacts
- Update changelog

Completion Criteria

- Full release executed successfully
- Documentation matches implementation
- Module marked complete

---

# Module 13 – AI Context

## Status

✅ Completed

### 13.1 AI Context Foundation

#### Status

✅ Completed

- Immutable AI context models
- Context metadata
- Context sections
- AIContext object hierarchy
- Context Generator
- Generate context from AnalysisModel
- Combine YAML, Registry and Relationships
- Generate AIContext objects

### 13.2 Entity & Automation Context

#### Status

✅ Completed

#### Entity Context

- Entity overview
- Registry information
- Relationships
- Package membership

#### Automation Context

- Triggers
- Conditions
- Actions
- Referenced entities
- Related scripts
- Related scenes
- Package information

### 13.3 Dashboard Context

#### Status

✅ Completed

- Dashboard overview
- Dashboard metadata
- Views
- Referenced entities
- Related automations
- Deterministic projection

### 13.4 Package Context

#### Status

✅ Completed

- Package overview
- Automations
- Scripts
- Scenes
- Helpers
- Templates
- Relationships

### 13.5 Prompt Builder

#### Status

✅ Completed

- Task-oriented prompts
- Programming prompts
- Refactoring prompts
- Documentation prompts

### 13.6 AI Export

#### Status

✅ Completed

- Markdown context
- JSON context
- Plain text context

---

# Module 14 – Scanner Improvements

## Status

✅ Completed

### 14.1 Scanner Architecture

#### Status

✅ Completed

- Consolidate discovery into ProjectTree
- Remove duplicate discovery paths
- Improve repository detection

### 14.2 Root YAML Support

#### Status

✅ Completed

- Support automations.yaml
- Support scripts.yaml
- Support scenes.yaml
- Preserve package architecture

### 14.3 Include Resolution

#### Status

✅ Completed

- ADR for include handling
- Support !include
- Support !include_dir_list
- Support !include_dir_merge_list
- Support !include_dir_named
- Support !include_dir_merge_named

### 14.4 Scanner Diagnostics

#### Status

✅ Completed

- YAML loading diagnostics
- Unclaimed files
- Repository inventory derived from ProjectTree

### 14.5 Pipeline Integration

#### Status

✅ Completed

- Production pipeline consumes one `ProjectTree` from `discover_project`
- Package and dashboard YAML is selected with `project_files()`
- `root_yaml_files()` is stored without loading or classifying those files
- Each loaded document is passed to `resolve_includes()`
- `scanner_diagnostics()` facts are stored unchanged

---

# Module 15 – ESPHome

## Status

✅ Completed

### 15.1 ESPHome Domain Model

#### Status

✅ Completed

- ESPHome domain models
- AnalysisModel integration
- Repository integration
- Relationship support

### 15.2 ESPHome Context

#### Status

✅ Completed

- Device overview
- Sensors
- Binary sensors
- Switches
- Related Home Assistant entities
- Deterministic projection

---

# Module 16 – Reporting

## Status

✅ Completed

Home Assistant Inventory Reporting. It reports parsed Home Assistant
objects from a completed analysis. It is not discovery, not scanning
and not a parser, and it does not walk the filesystem again.

### 16.1 Home Assistant Inventory Reporting

#### Status

✅ Completed

- Distinguish discovered files from parsed objects
- Automation inventory
- Script inventory
- Scene inventory
- Blueprint inventory
- Helper inventory
- Label inventory
- Deterministic reporting
- Reporting based on `AnalysisModel` and the existing repositories

---

# Repository Migration

## Status

🚧 In Progress

Functional development of HA-DocGen is complete.

Modules 1–16 represent the completed implementation of the application.

The remaining work prepares HA-DocGen for standalone distribution.

This repository migration introduces no new functionality, no architecture changes, no pipeline redesign and no behavioural changes.

This roadmap now tracks repository migration and future development rather than implementation of the original application.

---

## Phase 1 — Repository Extraction

### Status

✅ Completed

### Objectives

- create standalone repository structure
- introduce src layout
- relocate production code
- relocate tests
- relocate documentation
- preserve architecture
- preserve history where possible

### Deliverables

- standalone repository
- src/ha_docgen package
- tests outside package
- docs preserved
- examples folder

### 1.1 Repository Skeleton

✅ Completed

### 1.2 Move Production Package to `src`

✅ Completed

### 1.3 Restore Imports After `src` Migration

✅ Completed

### 1.4 Restore Executable Repository

✅ Completed

### 1.5 Complete Repository Extraction

✅ Completed

---

## Phase 2 — Packaging

### Status

✅ Completed

### Objectives

- create pyproject.toml
- requirements
- package metadata
- console entrypoint
- __main__.py
- build configuration

### Deliverables

- editable install
- wheel
- sdist
- console script

### 2.1 Introduce Modern Python Packaging

✅ Completed

### 2.2 Packaging Polish and Distribution Metadata

✅ Completed

---

## Phase 3 — GitHub

### Status

🚧 In Progress

### Objectives

- GitHub workflows
- README
- LICENSE
- CONTRIBUTING
- SECURITY
- issue templates
- pull request template

### Deliverables

- complete GitHub repository

### 3.1 GitHub Continuous Integration

✅ Completed

### 3.2 Release Validation

✅ Completed

### 3.3 Automated GitHub Release Pipeline

✅ Completed

---

## Phase 4 — Documentation

### Phase 4.1 — Documentation Path Migration

#### Status

✅ Completed

#### Objectives

- update repository paths
- update `src` layout references
- update import examples
- update command examples
- remove obsolete standalone migration references

#### Deliverables

- documentation paths fully consistent

---

### Phase 4.2 — Development Documentation

#### Objectives

- review development documentation
- align testing documentation
- align release documentation
- align contribution workflow
- update developer examples

#### Deliverables

- development documentation fully consistent

---

### Phase 4.3 — Architecture Documentation

#### Objectives

- update architecture documentation
- align package structure
- align architecture diagrams
- verify architecture principles
- preserve architectural consistency

#### Deliverables

- architecture documentation reflects the standalone repository

---

### Phase 4.4 — ADR & Historical Documentation

#### Objectives

- create ADR describing the repository extraction
- preserve existing ADR history
- preserve changelog history
- distinguish historical decisions from current architecture

#### Deliverables

- repository migration fully documented
- ADR history complete and consistent

---

### Phase 4.5 — Documentation Validation

#### Objectives

- validate internal documentation links
- verify repository references
- verify command examples
- verify installation instructions
- perform repository-wide documentation consistency audit

#### Deliverables

- documentation ready for Version 1.0.0

---

## Phase 5 — First Public Release

### Objectives

- update version
- update changelog
- validate release
- create GitHub release

### Deliverables

- Version 1.0.0

---

# Long-Term Vision

HA-DocGen is an independent open-source project that provides an enterprise-grade analysis platform for Home Assistant installations.

The application will:

- analyse repositories
- understand Home Assistant architecture
- detect relationships
- identify risks
- generate documentation
- validate configuration
- generate AI-ready context
- support long-term maintenance

without modifying the Home Assistant installation.