# HA-DocGen Modules

## Purpose

This document describes the functional modules that make up HA-DocGen.

Each module has a single responsibility and can be developed, tested and extended independently.

Production code lives in `src/ha_docgen/`. Component paths below are relative to that package. The test suite lives in `tests/` outside the package.

The roadmap serves as the primary reference for future development.

Module numbering matches `roadmap.md`.

---

# Development Status

| Module | Description | Status |
|----------|-------------|--------|
| 1. Foundation | Project setup, configuration and tooling | ✅ Complete |
| 2. Repository Discovery | Filesystem traversal and scanner framework | ✅ Complete |
| 3. ProjectTree | Filesystem abstraction, ScanPolicy, Ignore Rules | ✅ Complete |
| 4. Home Assistant Model | Storage, registries, HomeAssistantModel | ✅ Complete |
| 5. YAML Analysis | YamlDocument, parsers, YamlRepository | ✅ Complete |
| 6. Relationship Analysis | Analyzers, RelationshipRepository, DependencyGraph | ✅ Complete |
| 7. Documentation Generation | Document models, generators, Markdown export | ✅ Complete |
| 8. Validation | Validators, ValidationRepository, Validation Report | ✅ Complete |
| 9. Reporting | Health, architecture, inventory, dependency reports | ✅ Complete |
| 10. Command Line Interface | Commands, logging, validation, incremental execution | ✅ Complete |
| 11. Testing | Unit, integration, snapshot, benchmarks | ✅ Complete |
| 12. Release | CI, versioning, distribution | ✅ Complete |
| 13. AI Context | Context models, prompts, AI export | ✅ Complete |
| 14. Scanner Improvements | ProjectTree consolidation, includes, diagnostics | ✅ Complete |
| 15. ESPHome | ESPHome domain model and context | ✅ Complete |
| 16. Reporting | Home Assistant inventory reporting | ✅ Complete |

Application modules 1–16 are complete. Remaining work is repository
migration; see [`roadmap.md`](roadmap.md).

---

# Module 1 — Foundation

## Purpose

Create the technical foundation of HA-DocGen.

### Responsibilities

- Project configuration
- Settings
- Datamodels
- Entry point
- Version handling

### Main Components

- config.py
- models.py
- main.py

### Status

✅ Complete

---

# Module 2 — Repository Discovery

## Purpose

Scan the repository and collect general statistics.

### Responsibilities

- Count files
- Detect folders
- Collect project statistics
- Initial scanner framework

### Main Components

- scanner.py
- scanners/

### Status

✅ Complete

---

# Module 3 — ProjectTree

## Purpose

Create an in-memory representation of the complete repository.

This becomes the central data source for every subsequent analysis.

### Responsibilities

- Walk repository
- Ignore excluded folders
- Build ProjectTree
- Create FilesystemEntry objects
- Cache repository structure
- Central ScanPolicy and IgnoreRules
- Logging and diagnostics

### Main Components

- project/
- walker.py
- builder.py
- tree.py
- filesystem_entry.py
- policy/
- logging.py
- diagnostics.py

### Status

✅ Complete

---

# Module 4 — Home Assistant Model

## Purpose

Analyse Home Assistant `.storage` registries into a typed aggregate.

### Main Components

- storage/ — StorageScanner, StorageInventory
- registries/ — registry parsers and HomeAssistantModel

### Output

HomeAssistantModel

### Status

✅ Complete

---

# Module 5 — YAML Analysis

## Purpose

Load and interpret Home Assistant YAML into immutable domain objects.

### Main Components

- yaml/ — YamlDocument, YamlLoader, YamlRepository
- packages/ — Package, PackageStructure, Section, PackageScanner, PackageParser
- automation/, script/, scene/, helper/, dashboard/, blueprint/, template/ — domain parsers

### Output

YamlRepository

### Status

✅ Complete

---

# Module 6 — Relationship Analysis

## Purpose

Understand relationships inside the Home Assistant configuration.

### Main Components

- relationships/ — models, analyzers, RelationshipRepository
- graph/ — DependencyGraph, DependencyGraphBuilder

### Output

RelationshipRepository and DependencyGraph

### Status

✅ Complete

---

# Module 7 — Documentation Generation

## Purpose

Convert analysed data into documentation.

### Deliverables

- Document / Section / DocumentItem models
- MarkdownBuilder
- Package, Entity, Automation, Dashboard and Configuration generators
- DocumentRepository
- MarkdownExporter (`index.md` and one file per document)

### Output

Markdown documents via format-neutral document models

### Status

✅ Complete

---

# Module 8 — Validation

## Purpose

Detect configuration problems and risks.

### Deliverables

- Validation models and severity
- Entity, Automation, Dashboard, Package and MQTT validators
- ValidationRepository
- Validation Report

### Status

✅ Complete

---

# Module 9 — Reporting

## Purpose

Generate health and architecture reports for the Home Assistant installation.

### Deliverables

- Report domain models
- Health, Configuration, Architecture, Inventory, Dependency,
  Performance and Documentation Index reports
- Console, Markdown and JSON renderers
- CLI `report` commands

### Status

✅ Complete

---

# Module 10 — Command Line Interface

## Purpose

Operational CLI for running HA-DocGen.

### Responsibilities

- Entrypoint and command dispatcher in `main.py`
- Commands: default scan, `validate`, `report`, `help` and `version`
- Help: `help`, `--help`, `-h`
- Version: `version`, `--version`, `-V`
- Logging modes: `--quiet`, `--verbose`, `--debug`
- Configuration options: `--config` (default: `examples/config.yaml`), `--output`
- Scan options: `--incremental`, `--force`, `--clean-cache`
- Progress reporting, execution timings and execution summary
- Runtime configuration validation before execution
- Deterministic incremental cache and unchanged-file skipping
- Exit codes `0`, `1` and `2`

### Status

✅ Complete

---

# Module 11 — Testing

## Purpose

Automated quality assurance.

### Deliverables

- Shared test infrastructure (`tests/support/`)
- Unit tests
- Integration and golden-file (snapshot) tests
- Informational performance benchmarks

### Status

✅ Complete

See [development/testing.md](development/testing.md).

---

# Module 12 — Release

## Purpose

Release engineering.

### Deliverables

- GitHub Actions CI
- Package build and distribution metadata
- Version management (`src/ha_docgen/version.py`)
- Release validation and GitHub Release automation
- Release documentation

### Status

✅ Complete

See [development/release.md](development/release.md).

---

# Module 13 — AI Context

## Purpose

Project analysed Home Assistant data into immutable AI-ready context.

### Deliverables

- AI context models and ContextGenerator
- Entity, Automation, Dashboard and Package context
- PromptBuilder
- Markdown, JSON and plain-text AI export

### Status

✅ Complete

---

# Module 14 — Scanner Improvements

## Purpose

Consolidate discovery on ProjectTree and improve YAML include handling.

### Deliverables

- Single ProjectTree discovery path
- Root YAML support (`automations.yaml`, `scripts.yaml`, `scenes.yaml`)
- Include resolution (`!include` and directory variants)
- Scanner diagnostics
- Pipeline integration

### Status

✅ Complete

---

# Module 15 — ESPHome

## Purpose

Represent ESPHome devices in analysis and AI context.

### Deliverables

- ESPHome domain model and repository integration
- ESPHome context projection

### Status

✅ Complete

---

# Module 16 — Reporting

## Purpose

Report parsed Home Assistant objects from a completed analysis
(inventory reporting; not a second filesystem scan).

### Deliverables

- Home Assistant inventory reporting from `AnalysisModel`
- Deterministic automation, script, scene, blueprint, helper and
  label inventories

### Status

✅ Complete

---

# Development Principles

Every module must:

- Have a single responsibility
- Be independently testable
- Be strongly typed
- Minimise dependencies
- Follow the ProjectTree architecture
- Never modify the Home Assistant configuration

---

# Long-Term Vision

HA-DocGen should evolve into a complete analysis platform for Home Assistant.

Future capabilities include:

- Interactive HTML documentation
- Filtered entity / package graph views
- Dashboard visualisation
- Plugin architecture
- Web interface
