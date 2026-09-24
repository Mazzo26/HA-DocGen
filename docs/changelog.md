# Changelog

Historical, module-oriented development notes. For the user-facing
Version 1.0.0 summary, see [`CHANGELOG.md`](../CHANGELOG.md) at the
repository root.

## Version 1.0.0 – First Stable Release

- Application version set to `1.0.0`
- User-facing changelog published at repository root
- Packaging metadata marked Production/Stable
- Release artifacts (wheel + sdist) prepared for the public release

## Module 16.1 – Home Assistant Inventory Reporting

- `HomeAssistantInventoryGenerator` projects an immutable `HomeAssistantInventory` from `AnalysisModel`
- `discovered_files` are package and blueprint paths already stored on `YamlRepository`; a path is not a Home Assistant object
- Automations, scripts, scenes, blueprints and helpers stay the original YAML objects; labels stay the original registry objects
- Repeated paths collapse to one file; object order is deterministic and does not follow repository insertion order
- `scanner_diagnostics` remains the `ProjectFile` inventory; Module 9 `InventoryReportGenerator` is unchanged
- Discovery, `ProjectTree`, `YamlLoader`, repositories, `AnalysisModel` and the production pipeline stay unchanged

## Module 15.2 – ESPHome Context

- `ESPHomeDeviceContext` projects each ESPHome device already stored on `YamlRepository`
- Sensor, binary sensor and switch overviews keep the original components
- Related Home Assistant entities come from existing relationships; missing targets stay unresolved ids
- Device order is name then path, with unnamed devices last; component order is identity, platform, name and id
- `ContextGenerator` emits `esphome_contexts`; `AnalysisModel` does not gain a field
- `PromptBuilder` does not select ESPHome contexts
- Discovery, `ProjectTree`, `YamlLoader`, scanners, the production pipeline and reporting stay unchanged

## Module 15.1 – ESPHome Domain Model

- Immutable `ESPHomeDevice`, `ESPHomeSensor`, `ESPHomeBinarySensor` and `ESPHomeSwitch` models
- `ESPHomeParser` reads one `YamlDocument` and does not retain the source mapping
- `YamlRepository` stores ESPHome devices in name and path order and looks them up by name
- `AnalysisModel` reaches those devices through the existing YAML aggregate
- `ObjectType` can name an ESPHome device, sensor, binary sensor or switch in a relationship
- Discovery, `ProjectTree`, `YamlLoader`, scanners, the production pipeline and reporting stay unchanged

## Documentation – Home Assistant Inventory Reporting

- Home Assistant Inventory Reporting is moved to a future Reporting module
- That module consumes existing analysis output through `AnalysisModel` and the existing repositories
- Scanner and discovery responsibilities stay unchanged
- `roadmap.md` records the planned module; existing module numbers stay the same
- Documentation only

## Module 14.5 – Pipeline Integration

- The production pipeline keeps one `ProjectTree` from `discover_project`
- Package and dashboard YAML is selected with `project_files()`
- `root_yaml_files()` is stored without loading or classifying those files
- Each loaded document is passed to `resolve_includes()`; references stay unchanged
- `scanner_diagnostics()` is stored as returned, with no pipeline-authored failures
- Parsers, repositories, validators and `AnalysisModel` stay unchanged

## Module 14.4 – Scanner Diagnostics

- `scanner_diagnostics` derives scan facts from `project_files()` plus a caller-supplied claim set and YAML load failures
- Repository inventory and unclaimed files reference the existing `ProjectFile` instances
- Claim membership is object identity; the derivation does not decide ownership
- Facts are frozen and ordered by diagnostic type, relative POSIX path and message
- Discovery, `YamlLoader`, `resolve_includes`, parsers, repositories, validators, the build pipeline and `AnalysisModel` stay unchanged

## Module 14.3 – Include Resolution

- `resolve_includes` maps include directives in one `YamlDocument` onto `ProjectTree` files
- `YamlLoader` records `!include`, `!include_dir_list`, `!include_dir_named`, `!include_dir_merge_list` and `!include_dir_merge_named` as `IncludeNode` values
- Included paths are not opened, merged or expanded
- A missing path, a path outside the repository, or the wrong entry kind stays unresolved
- Discovery, parsers, repositories, the build pipeline, `AnalysisModel`, AI Context, Prompt Builder, Export and Reporting stay unchanged

## Module 14.2 – Root YAML Discovery

- `root_yaml_files` projects root YAML files from the existing `ProjectTree`
- The query keeps relative POSIX order and does not walk, stat or load YAML
- Package YAML and dashboard YAML stay outside that collection
- An explicit file selection returns only the root YAML files already in the tree
- Parsers, repositories, scanners and the build pipeline stay unchanged

## Module 14.1 – Scanner Architecture

- Repository discovery is `FilesystemWalker`, then `ScanPolicy`, then `ProjectTreeBuilder`
- `ProjectTree` is the only repository representation consumed by the scanners
- `FilesystemScanner`, `FolderDiscoveryScanner`, `PackageScanner` and `StorageScanner` read that tree
- An explicit file selection is projected with `project_tree_from_files` and does not walk again
- Duplicate relative paths collapse to the first entry; folders and files are ordered by relative path
- Parsers, repositories, relationship analysis, `AnalysisModel`, AI Context, Prompt Builder and Export stay unchanged

## Module 13.6 – AI Export

- `PromptExporter` renders an immutable `Prompt` as Markdown, JSON or plain text
- Exporters read `Prompt` only; they do not modify it and they do not write files
- JSON keeps stored fields, sorts object keys and preserves section order
- Markdown and plain text add a display title from `PromptType` and do not name a provider
- `Prompt`, `PromptBuilder`, `AIContext`, `ContextGenerator` and `AnalysisModel` stay unchanged

## Module 13.5 – Prompt Builder

- `PromptBuilder` organises an existing `AIContext` into an immutable `Prompt`
- Generic, programming, refactoring and documentation prompts each use a fixed section list
- Selected collections stay the original objects; empty collections are omitted
- Instructions are provider-neutral and do not choose an export format
- `AIContext`, `ContextGenerator` and `AnalysisModel` stay unchanged

## Module 13.4 – Package Context

- `PackageContext` keeps each package, including its name, path and document
- Automations, scripts, scenes, helpers and templates are the original objects that already reference that package
- Dashboards have no package reference, so they are not package members
- Referenced entities, scripts, scenes and dashboards come from existing relationships; missing targets stay unresolved ids
- Package ownership is not inferred from member contents or from an equal package copy
- Module 13.1 registry sections and Module 13.2 and 13.3 contexts stay unchanged

## Module 13.3 – Dashboard Context

- `DashboardContext` keeps each dashboard, including its metadata, and
  the same opaque view mappings
- View keys are not read, and no card model is introduced
- Referenced entities and related automations come from existing
  relationships; missing targets stay unresolved ids
- ESPHome Context is postponed: no ESPHome domain model, repository
  collection, relationship type or parser is available on
  `AnalysisModel`
- Module 13.1 registry sections and Module 13.2 entity and automation
  contexts stay unchanged

## Module 13.2 – Entity & Automation Context

- `EntityContext` keeps each registry entity, the relationships already
  stored for its entity id, and package objects those relationships name
- `AutomationContext` keeps each automation's triggers, conditions,
  actions and package, and resolves related entities, scripts and scenes
  from existing relationships
- Missing targets stay unresolved ids; package ownership is not inferred
- Module 13.1 registry sections and `ContextMetadata` stay unchanged
- No dashboard context, ESPHome context, package context, prompt builder,
  AI export or CLI wiring

## Module 13.1 – AI Context Foundation

- Immutable `AIContext`, `ContextMetadata` and `ContextSection` models
- `ContextGenerator` projects only `HomeAssistantModel` into category
  sections and keeps the original registry objects
- Empty categories are omitted; section order is deterministic
- Metadata stays empty when the model does not contain it
- No entity, automation, dashboard, ESPHome or package context,
  prompt builder, AI export or CLI wiring

## Module 12.6 – End-to-End Validation

- Validated checkout, editable install, Ruff, pytest with coverage,
  `python -m build`, wheel installation, CLI, and version consistency
- Stopped tracking `ha_docgen.egg-info/`; setuptools regenerates it and
  `.gitignore` already ignores `*.egg-info/`
- CI `push` runs for branches only, so a version tag does not start a
  second quality workflow
- CI concurrency group is prefixed with `ci-`, so a `workflow_call` from
  Release does not share `release-${{ github.ref }}`

## Module 12.5 – Release Documentation

- Contributor release guide in `docs/development/release.md`
- Versioning policy, tag format, recovery, troubleshooting, and checklist
- README links that guide for the release procedure

## Module 12.4 – Release Automation

- `.github/workflows/release.yml` on tags matching `v*.*.*`
- Reuses `.github/workflows/ci.yml` through `workflow_call`
- `.github/scripts/validate_release_version.py` checks the Git tag,
  installed metadata, wheel, and sdist against `VERSION`
- Uploads the wheel and sdist as workflow artifact
  `ha-docgen-distributions` and as GitHub Release assets
- Does not bump `VERSION`, generate a changelog, sign packages, or
  publish to PyPI

## Module 12.3 – Version Management

- Authoritative version is `tools.ha_docgen.version.VERSION`
- SemVer 2.0 is validated at import
- CLI, package `__version__`, and `get_version()` read that constant
- `pyproject.toml` reads the same attribute when building distributions
- Version discovery does not use Git

## Module 12.2 – Package Build & Distribution

- `pyproject.toml` is the setuptools build configuration
- `python -m build` produces one sdist and one wheel
- Distribution version comes from `tools.ha_docgen.version.VERSION`
- Package discovery includes `tools` and `tools.ha_docgen*`; tests,
  `tools.ha_tools`, and `tools/config.yaml` stay out of distributions
- Console script remains `ha-docgen`
- `requirements.txt` and `requirements-dev.txt` install that configuration

## Module 12.1 – CI Infrastructure

- `.github/workflows/ci.yml` on branch push and pull request
- Python 3.14 with pip cache from `requirements.txt`,
  `requirements-dev.txt`, and `pyproject.toml`
- Quality gates: Ruff, full pytest with coverage, and `python -m build`
- Coverage is collected without a numeric threshold
- Built distributions are not published

## Module 11.1 – Test Infrastructure

- Pytest markers and `testpaths` in `pyproject.toml`
- Opt-in fixtures in `tools.ha_docgen.tests.conftest`
- Model builders, temporary project helpers, comparison and assertion helpers
- Snapshot and benchmark helpers only; no snapshot files or benchmark tests
- Testing layout documented in `docs/development/testing.md`

## Module 10 – Command Line Interface

- Operational entrypoint and dispatcher in `tools.ha_docgen.main`
- Commands: default scan, `validate`, `report`, `help` and `version`
- Report commands: `health`, `config`, `architecture`, `inventory`,
  `dependencies`, `performance`, `docs`
- Help requests: `help`, `--help`, `-h`
- Version requests: `version`, `--version`, `-V`
- Logging modes: `--quiet`, `--verbose`, `--debug`
- Configuration options: `--config`, `--output`
- `validate` and execution startup reject invalid runtime configuration
- Incremental scan options: `--incremental`, `--force`, `--clean-cache`
- Unchanged files are skipped and cache JSON is written deterministically
- Exit codes: `0` success, `1` configuration error, `2` runtime error

## Module 9.9 – Console Renderer

- Introduced stateless `ConsoleRenderer` in `ha_docgen.reporting`
- Renders existing `Report` models as deterministic plain text
- Supports ASCII tables, summary blocks and optional ANSI severity colours
- No report generation, CLI handling, logging or filesystem writes

## Module 9.8 – Documentation Index

- Introduced `DocumentationIndexReportGenerator` in `ha_docgen.reporting`
- Stateless `generate(model, yaml_repository, document_repository,
  relationship_repository, metadata) -> Report`
- Aggregates known documentation sources, generated documents, index entries
  and existing cross references from immutable repositories
- Reports documentation coverage statistics and recommendations derived only
  from demonstrably undocumented packages, entities and automations
- Omits generated-file and documentation-health sections because no existing
  project model provides that metadata
- No scanning, parsing, rendering, Markdown, JSON, console output, filesystem
  writes or CLI

## Module 9.7 – Performance Report

- Introduced `PerformanceReportGenerator` in `ha_docgen.reporting`
- Stateless `generate(metadata, operation_timings=()) -> Report`
- Aggregates `ReportMetadata.execution_time` and caller-supplied
  operation timings only — no benchmarking
- Sections: Summary, Performance, Statistics; recommendations when
  existing metrics exceed a one-second threshold
- No Markdown, JSON, console output, filesystem writes or CLI

## Module 9.6 – Dependency Report

- Introduced `DependencyReportGenerator` in `ha_docgen.reporting`
- Stateless `generate(dependency_graph, metadata,
  circular_dependencies=()) -> Report`
- Reuses existing `DependencyGraph` edges; circular findings only when
  already supplied by the caller
- Sections: Summary, Dependencies, Statistics
- No new dependency analysis, Markdown, JSON, filesystem or CLI

## Module 9.5 – Inventory Report

- Introduced `InventoryReportGenerator` in `ha_docgen.reporting`
- Stateless `generate(model, yaml_repository, project_tree, metadata)
  -> Report`
- Aggregates entities, integrations, domains, packages and files from
  existing `HomeAssistantModel`, `YamlRepository` and `ProjectTree`
- Sections: Summary, Inventory, Statistics
- No scanning, parsing, Markdown, JSON, filesystem writes or CLI

## Module 9.3 – Configuration Report

- Introduced `ConfigurationReportGenerator` in `ha_docgen.reporting`
- Stateless `generate(model, yaml_repository, metadata) -> Report`
- Aggregates packages, automations, scripts, helpers and entity-domain
  inventory from existing `HomeAssistantModel` and `YamlRepository`
- Sections: Summary, Configuration Inventory, Statistics
- No scanning, parsing, Markdown, JSON, filesystem writes or CLI

## Module 9.2 – Health Report

- Introduced `HealthReportGenerator` in `ha_docgen.reporting`
- Stateless `generate(repository, metadata) -> Report`
- Aggregates `ValidationRepository` findings into Report domain models
  (summary, statistics, sections, recommendations)
- Sections: Validation Summary, Errors, Warnings, Informational
- Recommendations derived only from validation severity and type totals
- No Markdown, JSON, console output, filesystem writes or CLI
- Documented as ADR-059

## Module 9.1 – Report Domain Models

- Introduced `ha_docgen.reporting` with immutable `Report`,
  `ReportSection`, `ReportMetadata` and `Severity`
- `Report` holds `title`, `description`, `metadata`, `sections`,
  `statistics`, `recommendations` and `summary`
- `ReportSection` holds `title`, optional `description`, `severity` and
  plain-text `items`
- `ReportMetadata` holds `generated_at`, `version`, `project_path` and
  `execution_time`
- `Severity` StrEnum: `INFO`, `WARNING`, `ERROR` — independent of
  `ValidationSeverity`
- Collections frozen as tuples; statistics as sorted `MappingProxyType`
- No renderers, generators, exporters, CLI, Markdown, JSON, filesystem
  or Home Assistant business logic
- Documented as ADR-058

## Module 8.3 – Automation Validation

- Introduced `AutomationValidator` in `ha_docgen.validation`
- Stateless `validate(automations, relationship_repository) ->
  tuple[ValidationResult, ...]`
- Explicit checks only: empty automation ID (ERROR /
  `INVALID_CONFIGURATION`), empty alias (WARNING /
  `INVALID_CONFIGURATION`), empty relationship target (ERROR /
  `INVALID_CONFIGURATION`), duplicate automation ID (ERROR /
  `DUPLICATE`)
- Does not report unreferenced automations: absence of inbound
  relationships is not an objective configuration fault (triggers
  start automations independently); quality findings belong outside
  Module 8
- Results are deduplicated and deterministically sorted
- No validation engine, repository, reports, Markdown, filesystem,
  graph traversal or business logic beyond the stated rules
- Documented as ADR-057

## Module 8.2 – Entity Validation

- Introduced `EntityValidator` in `ha_docgen.validation`
- Stateless `validate(entities, relationship_repository) ->
  tuple[ValidationResult, ...]`
- Explicit checks only: unreferenced entity (INFO /
  `UNREFERENCED_OBJECT`), empty relationship target (ERROR /
  `INVALID_CONFIGURATION`), empty entity ID (ERROR /
  `INVALID_CONFIGURATION`), duplicate entity ID (ERROR / `DUPLICATE`)
- Results are deduplicated and deterministically sorted
- No validation engine, repository, reports, Markdown, filesystem,
  graph traversal or business logic beyond the stated rules
- Documented as ADR-056

## Module 8.1 – Validation Models

- Introduced `ha_docgen.validation` with immutable `ValidationResult`
  and `ValidationCollection`
- `ValidationResult` holds `object_type`, `object_id`, `validation_type`,
  `severity` and `message` (identity only)
- `ValidationSeverity` and `ValidationType` StrEnums; generic types only
  (`UNREFERENCED_OBJECT`, `DUPLICATE`, `INVALID_CONFIGURATION`,
  `UNSUPPORTED`, `CUSTOM`) — no Home Assistant-specific members
- Reuses `ObjectType` from `relationships.models` (no own enum)
- `ValidationCollection` deduplicates and sorts deterministically, then
  builds O(1) `MappingProxyType` indexes
- Lookup API: `by_object(type, id)`, `by_severity(severity)`,
  `by_type(validation_type)` return `tuple[ValidationResult, ...]`
- No validators, analysis, repository, reports, Markdown, filesystem
  or business logic
- Documented as ADR-055

## Module 7.9 – Markdown Export

- Introduced `MarkdownExporter` in `ha_docgen.document`
- Stateless `export(repository, output_directory) -> None` writes
  already-generated `Document` objects from a `DocumentRepository`
- Renders exclusively via existing `MarkdownBuilder`; one `.md` file
  per document
- Deterministic safe filenames from `Document.title` (lowercase,
  spaces → `-`, strip `:`, `/` → `-`, collapse repeated `-`)
- Creates `output_directory` when missing (`pathlib` only)
- Generates `index.md` with `# Documentation` and bullet links
  `[title](filename.md)` from repository documents only
- No generators, analysis, graph, HTML, JSON, PDF or business logic
- Documented as ADR-054

## Module 7.8 – Documentation Repository

- Introduced `DocumentRepository` in `ha_docgen.document`
- Central immutable store of already-generated `Document` objects
- Constructor accepts only `tuple[Document, ...]` (generator-agnostic)
- Deduplicates and sorts deterministically on construction
  (`Document.title`)
- Builds read-only `MappingProxyType` `_by_title` index in `__post_init__`
- Lookup API: `document(title) -> Document | None`,
  `documents_by_title(title) -> tuple[Document, ...]`; public field
  `documents` holds the immutable tuple
- No generation, rendering, Markdown, HTML, JSON, exporters, writers,
  filesystem, graph, analysis or business logic
- Same philosophy as `YamlRepository` and `RelationshipRepository`
- Documented as ADR-053

## Module 7.7 – Configuration Documentation

- Introduced `ConfigurationDocumentGenerator` in `ha_docgen.document`
- Stateless `generate(model, yaml_repository, relationship_repository)
  -> Document` for one configuration-wide overview
- Sections: Overview (Paragraph), Registries / YAML / Relationships
  (Table), Statistics (BulletList)
- Registries count `HomeAssistantModel` collections; YAML counts
  `YamlRepository` collections; Relationships count per
  `RelationshipType` via `RelationshipRepository.by_relationship`;
  Statistics show simple totals only
- Accepts only already-built immutable aggregates — no parsing,
  scanning, analysis, graph traversal or lookups beyond the given
  repositories
- No Markdown, filesystem, HTML, JSON, exporters, writers or
  business logic
- Documented as ADR-052

## Module 7.6 – Dashboard Documentation

- Introduced `DashboardDocumentGenerator` in `ha_docgen.document`
- Stateless `generate(dashboard, relationships) -> Document` for exactly
  one Dashboard
- Sections: Overview (Paragraph), Views / Relationships (BulletList)
- Overview shows present first-class fields (id, title, mode, path);
  Views list view titles from `Dashboard.views` (or ``Unnamed view``);
  Relationships render `{type} → {target_type}:{target_id}` in given order
- Accepts only `Dashboard` and `tuple[Relationship, ...]` — no
  HomeAssistantModel, YamlRepository, RelationshipRepository, graph or
  lookups
- No Markdown, filesystem, HTML, JSON, exporters, dashboard index,
  multi-dashboard generation, YAML parsing, card/entity analysis or
  business logic
- Documented as ADR-051

## Module 7.5 – Automation Documentation

- Introduced `AutomationDocumentGenerator` in `ha_docgen.document`
- Stateless `generate(automation, relationships) -> Document` for exactly
  one Automation
- Sections: Overview (Paragraph), Triggers / Conditions / Actions /
  Relationships (BulletList)
- Overview shows present first-class fields (id, alias, mode, description);
  Triggers / Conditions / Actions list explicit YAML type or service names
  from `Automation.raw`; Relationships render
  `{type} → {target_type}:{target_id}` in given order
- Accepts only `Automation` and `tuple[Relationship, ...]` — no
  HomeAssistantModel, YamlRepository, RelationshipRepository, graph or
  lookups
- No Markdown, filesystem, HTML, JSON, exporters, automation index,
  multi-automation generation, YAML parsing, Jinja evaluation or
  business logic
- Documented as ADR-050

## Module 7.4 – Entity Documentation

- Introduced `EntityDocumentGenerator` in `ha_docgen.document`
- Stateless `generate(entity, relationships) -> Document` for exactly
  one Entity
- Sections: Overview (Paragraph), Registry (BulletList), Relationships
  (BulletList)
- Overview shows available registry identity fields (entity_id, friendly
  name, platform, domain); Registry lists present first-class fields;
  Relationships render `{type} → {target_type}:{target_id}` in given order
- Accepts only `Entity` and `tuple[Relationship, ...]` — no
  HomeAssistantModel, RelationshipRepository, graph or lookups
- No Markdown, filesystem, HTML, JSON, exporters, entity index,
  multi-entity generation, history, state, attributes or business logic
- Documented as ADR-049

## Module 7.3 – Package Documentation

- Introduced `PackageDocumentGenerator` in `ha_docgen.document`
- Stateless `generate(package, structure, automations, scripts, scenes,
  helpers, templates) -> Document` for exactly one Package
- Sections: Overview, Sections, Helpers, Automations, Scripts, Scenes,
  Templates (BulletList / Paragraph only)
- Filters input collections with `object.package == package`
- No Markdown, filesystem, HTML, JSON, repository, exporters, index,
  multi-package generation, relationships, graph or business logic
- Documented as ADR-048

## Module 7.2 – Markdown Builder

- Introduced `MarkdownBuilder` in `ha_docgen.document`
- Stateless `build(document: Document) -> str` — deterministic Markdown
- Supports `Document`, `Section`, `Paragraph`, `Table`, `CodeBlock`,
  `BulletList` via private helpers only
- Standard GitHub Markdown tables and fenced code blocks
- No HTML, JSON, links, images, TOC, front matter, filesystem,
  generators, exporters or Home Assistant domain knowledge
- Documented as ADR-047

## Module 7.1 – Documentation Models

- Introduced `ha_docgen.document` with immutable document structure models
- `Document`: `title` + `sections` (`tuple[Section, ...]`)
- `Section`: `heading` + `content` (`tuple[DocumentItem, ...]`)
- Polymorphic `DocumentItem` base with `Paragraph`, `Table`, `CodeBlock`,
  `BulletList` subtypes (`frozen=True`, `slots=True`; tuples only)
- Fully output-independent — no Markdown, HTML, JSON, builders, exporters,
  rendering, validation or business logic
- Documented as ADR-046

## Module 6.9 – Dependency Graph

- Introduced `ha_docgen.graph` with immutable graph models and builder
- `GraphNode`: `object_type` + `object_id` only (no labels/metadata)
- `GraphEdge`: `source`, `target`, `relationship_type` (no weights/attrs)
- `DependencyGraph`: immutable `nodes` / `edges` tuples with
  `MappingProxyType` indexes for `outgoing`, `incoming`, `contains`
- `DependencyGraphBuilder.build(repository)` — stateless conversion from
  `RelationshipRepository`; deduplicates and sorts deterministically
- Single graph representation only; Entity/Package graphs are future
  views by filtering on `ObjectType`, not separate models
- No visualisation (Graphviz/Mermaid/NetworkX), no traversal algorithms,
  no dependency analysis, no business logic, no repository mutation
- Documented as ADR-045

## Module 6.8 – Relationship Repository

- Introduced `RelationshipRepository` in `ha_docgen.relationships`
- Central immutable store of already-computed `Relationship` objects
- Constructor accepts only `tuple[Relationship, ...]` (analyzer-agnostic)
- Deduplicates and sorts deterministically on construction
  (`source_type`, `source_id`, `relationship_type`, `target_type`, `target_id`)
- Builds read-only `MappingProxyType` indexes in `__post_init__`
- Lookup API: `by_source`, `by_target`, `by_relationship`, `between`
  — all return immutable `tuple[Relationship, ...]`
- No analysis, graph, validation, HomeAssistantModel/YamlRepository
  lookups or analyzer knowledge
- Same philosophy as `HomeAssistantModel` and `YamlRepository`
- Documented as ADR-044
- Refined private helper typing: accurate sort-key return types;
  `_deduplicate_and_sort` accepts `Iterable[Relationship]` (no behaviour change)

## Module 6.7 – MQTT Relationships

- Introduced `MQTTRelationshipAnalyzer` in `ha_docgen.relationships`
- Derives explicit MQTT topic references from automations, scripts, helpers and package `mqtt` sections
- Emits `PUBLISHES` for `mqtt.publish` service/action calls (literal `topic` / `data.topic`)
- Emits `SUBSCRIBES` for explicit subscribe-topic keys (`state_topic`, `command_topic`, `availability_topic`, `json_attributes_topic`, `topic`)
- Source is `ENTITY` when `entity_id` is already present; otherwise `PACKAGE`
- Uses existing `ObjectType.MQTT_TOPIC`; adds `RelationshipType.PUBLISHES` and `SUBSCRIBES`
- Accepts explicit collections (not `YamlRepository`) for consistency with Modules 6.2–6.6
- Reuses shared `_yaml_traversal` helpers; public API returns sorted immutable `tuple[Relationship, ...]`
- Stateless, read-only, no broker, wildcards, normalisation, graph, repository, runtime validation or business logic
- Documented as ADR-043

## Module 6.6 – Dashboard Relationships

- Introduced `DashboardRelationshipAnalyzer` in `ha_docgen.relationships`
- Derives explicit YAML references from `Dashboard.views` only (recursive walk)
- Emits `DASHBOARD REFERENCES` for entity and device targets
- Detects only explicit identity keys (`entity`, `entities`, `entity_id`, `device`, `device_id`) — no card-type knowledge
- Reuses shared `_yaml_traversal` helpers; added generic `entity` / `entities` / `device` key constants
- Public API returns sorted immutable `tuple[Relationship, ...]` (not a collection)
- Stateless, read-only, no Lovelace rendering, graph, repository, runtime validation or business logic
- Documented as ADR-042

## Module 6.5 – Script Relationships

- Introduced `ScriptRelationshipAnalyzer` in `ha_docgen.relationships`
- Derives explicit YAML references from `Script.raw` only (recursive walk)
- Emits `SCRIPT REFERENCES` for entity, script and scene targets
- Reuses shared `_yaml_traversal` helpers for mapping walks, `entity_id`, service/action and `target` extraction (also used by Module 6.4)
- Public API returns sorted immutable `tuple[Relationship, ...]` (not a collection)
- Stateless, read-only, no graph, repository, runtime validation, Jinja or business logic
- Documented as ADR-041

## Module 6.4 – Automation Relationships

- Introduced `AutomationRelationshipAnalyzer` in `ha_docgen.relationships`
- Derives explicit YAML references from `Automation.raw` only (recursive walk)
- Emits `AUTOMATION REFERENCES` for entity, device, area, script, scene and automation targets
- Shared private `_yaml_traversal` helper for recursive mapping/sequence walks (reuse in 6.5–6.7)
- Aligned `Automation.raw` with Script/Scene: full original YAML mapping (not leftovers only)
- Public API returns sorted immutable `tuple[Relationship, ...]` (not a collection)
- Stateless, read-only, no graph, repository, runtime validation, Jinja or business logic
- Documented as ADR-040

## Module 6.3 – Device Relationships

- Introduced `DeviceRelationshipAnalyzer` in `ha_docgen.relationships`
- Derives explicit device registry links from `HomeAssistantModel` only
- Emits `DEVICE BELONGS_TO` for area, each config entry and each label
- Public API returns immutable `tuple[Relationship, ...]` (not a collection)
- Stateless, read-only, no YAML, graph, repository, validation or business logic
- Documented as ADR-039

## Module 6.2 – Entity Relationships

- Introduced `EntityRelationshipAnalyzer` in `ha_docgen.relationships`
- Derives explicit entity registry links from `HomeAssistantModel` only
- Emits `ENTITY BELONGS_TO` for device, area, config entry and each label
- Public API returns immutable `tuple[Relationship, ...]` (not a collection)
- Stateless, read-only, no YAML, graph, repository, validation or business logic
- Documented as ADR-038

## Module 6.1 – Relationship Models

- Introduced `ha_docgen.relationships` with immutable `Relationship` and `RelationshipCollection`
- `Relationship` holds source/target type+id and `relationship_type` (identity only)
- `ObjectType` and `RelationshipType` StrEnums replace free strings for type-safe identity fields
- `RelationshipCollection` freezes relationships as a tuple and builds O(1) `MappingProxyType` indexes
- Lookup API: `by_source(type, id)` and `by_target(type, id)` return `tuple[Relationship, ...]`
- No parsing, analysis, graph, validation or Home Assistant coupling
- Documented as ADR-037

## Module 5.15 – Domain Package Provenance

- Added required `package: Package` to `Automation`, `Script`, `Scene`, `Helper` and `Template`
- `AutomationParser`, `ScriptParser`, `SceneParser` and `HelperParser` now accept `PackageStructure` and forward `structure.package`
- `TemplateParser` sets `package=structure.package` (still accepts `PackageStructure`)
- `Section` remains pure YAML (`name`, `data` only); Blueprint and Dashboard unchanged
- Lazy `YamlRepository` import in `ha_docgen.yaml` to avoid import cycles
- Documented as ADR-036

## Module 5.14 – YAML Repository

- Added immutable `YamlRepository` as the central YAML domain aggregate
- Holds packages, package structures, automations, scripts, scenes, helpers, dashboards, blueprints and templates as tuples
- Builds O(1) `MappingProxyType` lookup indexes at construction time
- Lookup API returns `Object | None` (never raises); templates have no lookup (no stable unique id)
- No parsing, relationships, validation or Home Assistant semantics
- Documented as ADR-035

## Module 5.13 – Template Parser

- Introduced `ha_docgen.template` with immutable `Template` and `TemplateParser`
- Collects template strings from `PackageStructure` via known template fields only
- `Template` holds `kind`, `source`, optional `path`, and parent YAML in `raw`
- Recursive walk of mappings and lists; no Jinja parsing or evaluation
- No entity extraction, variable resolution, dependency analysis or HomeAssistantModel links
- Documented as ADR-034

## Module 5.12 – Blueprint Parser

- Introduced `ha_docgen.blueprint` with immutable `Blueprint` and `BlueprintParser`
- Parses one `YamlDocument` into a single `Blueprint` (name, description, domain, source_url, input, path)
- `input` holds raw input mappings only; selectors and automation semantics stay uninterpreted
- Unknown fields remain solely in `raw`, which also keeps the full blueprint YAML
- No selector parsing, input validation, automation generation or HomeAssistantModel links
- Documented as ADR-033

## Module 5.11 – Dashboard Parser

- Introduced `ha_docgen.dashboard` with immutable `Dashboard` and `DashboardParser`
- Parses one `YamlDocument` into a single `Dashboard` (title, mode, views, path)
- `views` holds raw view mappings only; cards and navigation stay uninterpreted
- Unknown fields remain solely in `raw`, which also keeps the full dashboard YAML
- No card/entity/badge parsing, view models, validation or HomeAssistantModel links
- Documented as ADR-032

## Module 5.10 – Helper Parser

- Introduced `ha_docgen.helper` with immutable `Helper` and `HelperParser`
- Parses supported helper Sections from `tuple[Section, ...]` into `tuple[Helper, ...]`
- Section name becomes `type`; mapping key becomes `id`; unknown fields stay in `raw`
- Extensible allow-list for helper domains; unknown top-level sections are ignored
- No entity/automation/script lookup, validation, relationships or HomeAssistantModel links
- Documented as ADR-031

## Module 5.9 – Scene Parser

- Introduced `ha_docgen.scene` with immutable `Scene` and `SceneParser`
- Parses `Section("scene")` only (list and mapping forms) into `tuple[Scene, ...]`
- Mapping key becomes `id` when no explicit `id` is present; `raw` keeps full YAML
- No entity/automation/script lookup, state validation, template evaluation or HomeAssistantModel links
- Documented as ADR-030

## Module 5.8 – Script Parser

- Introduced `ha_docgen.script` with immutable `Script` and `ScriptParser`
- Parses `Section("script")` only (HA mapping form) into `tuple[Script, ...]`
- Mapping key becomes `id` when no explicit `id` is present; `raw` keeps full YAML
- No entity/automation/device lookup, template evaluation, validation or HomeAssistantModel links
- Documented as ADR-029

## Module 5.7 – Automation Parser

- Introduced `ha_docgen.automation` with immutable `Automation` and `AutomationParser`
- Parses `Section("automation")` only (list and mapping forms) into `tuple[Automation, ...]`
- No entity/device/script lookup, template evaluation, validation or HomeAssistantModel links
- Documented as ADR-028

## Module 5.6 – Section Model

- Introduced immutable `Section` dataclass (`name`, `data`)
- `PackageStructure.sections` is now `tuple[Section, ...]` with O(1) lookup helpers
- `PackageParser` creates one `Section` per top-level YAML key; no interpretation
- Documented as ADR-027

## Module 5.5 – Package Parser

- Introduced `PackageParser` and immutable `PackageStructure` (`package`, `sections`)
- Detects top-level Home Assistant sections from `package.document.data` only
- No interpretation of section contents; specialised parsers deferred
- Documented as ADR-026

## Module 5.4 – Package Model

- Introduced immutable `Package` dataclass (`name`, `path`, `document`)
- Public representation of one Home Assistant package; holds `YamlDocument` only
- No YAML interpretation; no automations, scripts, sensors or other HA objects
- `PackageScanner` unchanged; no wiring yet
- Documented as ADR-025

## Module 5.3 – Package Scanner

- Introduced `ha_docgen.packages` with `PackageScanner`
- Discovers `.yaml` / `.yml` files under a package directory
- Loads each file via injected `YamlLoader` into immutable `YamlDocument` tuples
- No package models, HA semantics, validation or dependency analysis
- Documented as ADR-024

## Module 5.2 – YAML Loader

- Introduced `YamlLoader` as the sole component that reads YAML files
- Loads one file into an immutable `YamlDocument` (`path`, `text`, `data`)
- Raises `YamlLoadError` (with chaining) for missing files, I/O errors and parse failures
- Documented as ADR-023

## Module 5.1 – YAML Document

- Introduced `ha_docgen.yaml` with immutable `YamlDocument`
- Holds source `path`, original `text` and parsed `data` only
- No I/O, no YAML parser, no Home Assistant or domain logic
- Documented as ADR-022

## Module 4.9 – HomeAssistantModel

- Added immutable `HomeAssistantModel` as the central registry aggregate
- Holds entities, devices, areas, labels, floors and config entries as tuples
- Builds O(1) `MappingProxyType` lookup indexes at construction time
- Lookup API returns `Object | None` (never raises); no parsing or relationships
- Documented as ADR-021

## Module 4.8 – Config Entry Registry

- Extended `ha_docgen.registries` with `ConfigEntry` and `ConfigEntryRegistryParser`
- Pure parser for `.storage/core.config_entries` (no discovery, no relationships)
- Models identity, status, preferences and lifecycle timestamps
- Keeps non-first-class JSON (e.g. `data`, `options`, `unique_id`) in read-only `ConfigEntry.extra` (`MappingProxyType`)
- Documented as ADR-020

## Module 4.7 – Floor Registry

- Extended `ha_docgen.registries` with `Floor` and `FloorRegistryParser`
- Pure parser for `.storage/core.floor_registry` (no discovery, no relationships)
- Models identity, level, icon and lifecycle timestamps
- Keeps non-first-class JSON (e.g. `aliases`) in read-only `Floor.extra` (`MappingProxyType`)
- Documented as ADR-019

## Module 4.6 – Label Registry

- Extended `ha_docgen.registries` with `Label` and `LabelRegistryParser`
- Pure parser for `.storage/core.label_registry` (no discovery, no relationships)
- Models identity, color, icon, description and lifecycle timestamps
- Keeps non-first-class JSON in read-only `Label.extra` (`MappingProxyType`)
- Documented as ADR-018

## Module 4.5 – Area Registry

- Extended `ha_docgen.registries` with `Area` and `AreaRegistryParser`
- Pure parser for `.storage/core.area_registry` (no discovery, no relationships)
- Models identity, aliases, labels, picture and lifecycle timestamps
- Keeps non-first-class JSON (e.g. `floor_id`, `icon`) in read-only `Area.extra`
- Documented as ADR-017

## Module 4.4 – Device Registry

- Extended `ha_docgen.registries` with `Device` and `DeviceRegistryParser`
- Pure parser for `.storage/core.device_registry` (no discovery, no relationships)
- Normalises identifiers, connections, labels and config entry IDs to tuples
- Accepts both `config_entries` and singular `config_entry_id` storage formats
- Keeps non-first-class JSON in read-only `Device.extra` (`MappingProxyType`)
- Documented as ADR-016

## Module 4.3 – Entity Registry

- Introduced `ha_docgen.registries` with `Entity` and `EntityRegistryParser`
- Pure parser for `.storage/core.entity_registry` (no discovery, no filtering)
- Supports normal and orphaned entries with safe defaults for missing fields
- Keeps non-first-class JSON in read-only `Entity.extra` (`MappingProxyType`)
- Derives `domain` via `@property` from `entity_id`
- Documented as ADR-015

## Module 4.2 – Storage Inventory

- Extended `StorageInventory` into the central read-only access layer for storage files
- Added filename lookup (`get` / `has` / `__contains__`), iteration and length
- Built an O(1) filename index at construction time (no duplicated lookups)
- Remains free of JSON parsing and Home Assistant registry semantics
- Documented as ADR-014

## Module 4.1 – Storage Scanner

- Introduced `ha_docgen.storage` with `StorageFile`, `StorageInventory` and `StorageScanner`
- Storage discovery is read-only filesystem metadata only (no JSON parsing)
- Reuses `FilesystemWalker`, `FilesystemEntry`, `ProjectTree` and `ScanPolicy`
- Remains independent from future Entity Registry / Device Registry parsers
- Documented as ADR-013

## Module 3.7 – Ignore Rules

- Introduced `IgnoreRules` as the configurable rule set consumed by `ScanPolicy`
- Moved default ignored directories, filenames and filename patterns into `policy/ignore_rules.py`
- `ScanPolicy` now evaluates directory names, exact filenames and filename patterns
- Behaviour preserved: defaults still exclude only `IGNORE_DIRS` path components
- Deferred: `.gitignore` parsing, include rules and user configuration

## Module 3.6 – ScanPolicy

- Introduced a dedicated `ha_docgen.policy` package with a central `ScanPolicy`
- Moved filesystem inclusion/exclusion decisions out of scanners into the policy layer
- Scanners now depend on `ScanPolicy` instead of hardcoded ignore logic
- Behaviour preserved: exclusion still matches any path component in `IGNORE_DIRS`

## Module 3.5 – Logging & Diagnostics

- Introduced a central `Logger` abstraction with DEBUG, INFO, WARNING and ERROR levels
- Isolated Rich behind the logger implementation
- Added runtime diagnostics (version, Python, platform, timings)
- Replaced raw console printing and raw tracebacks with user-friendly error reporting
- Entry point now returns process exit codes (`0` / `1` / `2`)

## Module 3.4 – Shared Constants

- Replaced `constants.py` with the `ha_docgen.constants` package
- Grouped constants by responsibility: files, folders, yaml, project
- Separated generic filesystem constants from Home Assistant project constants
- Derived glob patterns from extension constants
- Wired shared constants into filesystem scanner, utils, config and ProjectTreeBuilder
