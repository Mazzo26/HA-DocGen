# HA-DocGen Architecture

> Normative design rules live in [`architecture-principles.md`](architecture-principles.md).
> That document is the primary source for all Cursor implementations.

## Purpose

HA-DocGen is a standalone Python application that analyses a Home Assistant configuration and generates technical documentation.

The application is strictly **read-only**.

Its primary objectives are:

- analyse the repository structure
- understand relationships between configuration files
- collect Home Assistant metadata
- generate consistent technical documentation
- support long-term maintenance of large Home Assistant installations

HA-DocGen never modifies the Home Assistant configuration.

---

# Repository Layout

HA-DocGen is a standalone repository. Production code lives under
`src/ha_docgen/` (import name `ha_docgen`). Tests live outside the package.

The decision to extract this layout from the former nested `tools.ha_docgen`
package is recorded in [ADR-071](design-decisions.md#adr-071).

```text
src/ha_docgen/     production package
tests/             test suite (outside the package)
docs/              project documentation
examples/          usage examples; default runtime config
```

Package-relative paths in this document (for example
`policy/ignore_rules.py`) resolve under `src/ha_docgen/`.

---

# High-Level Architecture

```text
                 Home Assistant Repository
                          │
                          ▼
                  FilesystemWalker
                          │
                          ▼
                     ScanPolicy
                          │
                          ▼
                  ProjectTreeBuilder
                          │
                          ▼
                     ProjectTree
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
  Filesystem Scanner  Storage Scanner  Package Scanner
          │               │                │
          │               ▼                ▼
          │        Registry Parsers   YAML Loader / Parsers
          │               │                │
          │               ▼                ▼
          │      HomeAssistantModel   YamlRepository
          │               │                │
          └───────────────┴────────────────┘
                          │
                          ▼
               Relationship Analyzers
                          │
                          ▼
               RelationshipRepository
                          │
                          ▼
                   DependencyGraph
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
     Statistics      Dependency       Documentation
     Generator       Generator         Generator
                          │
                          ▼
                     Markdown Writers
                          │
                          ▼
                   docs/generated/
```

---

# Core Components

## FilesystemWalker

Responsible for traversing the Home Assistant repository.

Responsibilities:

- walk the repository only once
- collect filesystem metadata
- avoid unnecessary disk access

`ScanPolicy` filters the walked entries before `ProjectTreeBuilder` creates the `ProjectTree`. Downstream scanners read that tree instead of walking the repository again.

---

## ProjectTreeBuilder

Builds an in-memory representation of the repository.

The ProjectTree becomes the central data source for the remainder of the application.

---

## ProjectTree

Represents the complete repository structure.

Contains:

- folders
- files
- metadata

All subsequent scanners work from the ProjectTree instead of scanning the filesystem again.

`discover_project` is the only complete discovery path: `FilesystemWalker`, then `ScanPolicy`, then `ProjectTreeBuilder`. `Scanner`, `FilesystemScanner`, `FolderDiscoveryScanner`, `PackageScanner` and `StorageScanner` read that tree. An explicit file selection is projected with `project_tree_from_files` and does not walk the repository.

`root_yaml_files` is a pure query over that tree. It returns YAML files whose relative parent is the repository root, in the existing relative POSIX order. Package and dashboard YAML stay in their directory queries. The query does not walk, stat, open or load files.

`resolve_includes` reads the same tree. It does not call `discover_project`, `FilesystemWalker` or `Path.rglob`.

---

## Scanners

Scanners discover information. They never generate documentation and never write files.

Examples:

- Filesystem Scanner
- Storage Scanner
- Package Scanner

Each scanner has a single responsibility.

Configuration inventory is not a scanner responsibility and not a discovery responsibility. Counts and listings of parsed Home Assistant objects belong to Home Assistant Inventory Reporting. Scanners keep discovering files. They do not inventory those objects.

---

## Scanner Diagnostics

`scanner_diagnostics` derives informational scan facts from an existing `ProjectTree`.

It reads `project_files()` and two caller-supplied inputs: a claim set and YAML load failures. A stored file is claimed only when that `ProjectFile` instance is in the claim set. The caller decides membership. The derivation does not classify packages, dashboards, root YAML or storage.

The result is a frozen collection sorted by diagnostic type, relative POSIX path and message. Each fact references an existing `ProjectFile`:

- repository inventory references every file from `project_files()`
- unclaimed files are the stored instances absent from the claim set
- YAML load failures reference the `ProjectFile` and message supplied by the caller

Repository inventory lists discovered files. It does not list parsed objects.

`ProjectTree` stays the repository representation. The derivation does not walk the repository, load YAML, expand includes or report validation findings.

---

## Production Pipeline

`_build_project_analysis` consumes this scanner architecture. It calls `discover_project` once and passes that `ProjectTree` to every later step.

Configured package and dashboard YAML is selected with `project_files()`. The pipeline does not walk again, call `project_tree_from_files`, or build another tree.

`root_yaml_files()` is stored as returned. The query does not load those files and does not classify them further.

Each selected YAML file is loaded once with `YamlLoader`. `resolve_includes()` runs on that document and the same tree. The resulting `IncludeReference` values are stored unchanged. Includes are not expanded or merged.

`scanner_diagnostics()` receives the same tree and the `ProjectFile` instances that were loaded. The pipeline does not supply load failures, and it stores the returned collection as-is.

Parsers, repositories, validators and `AnalysisModel` keep their existing responsibilities.

---

## Registry Parsers

Pure parsers under `ha_docgen.registries` read individual `.storage` registry files.

Examples:

- EntityRegistryParser
- DeviceRegistryParser
- AreaRegistryParser
- LabelRegistryParser
- FloorRegistryParser
- ConfigEntryRegistryParser

They return typed dataclasses. They do not discover files and do not assemble relationships.

---

## YAML Layer

YAML loading and domain parsing are separated.

- `YamlLoader` / `YamlDocument` — sole file reader and generic document
- `IncludeNode` / `resolve_includes` — include locations only
- `Package` / `PackageStructure` / `Section` — package structure only
- Domain parsers — Automation, Script, Scene, Helper, Dashboard, Blueprint, Template, ESPHome

Interpretation stays out of the loader and out of `PackageScanner`.

---

## Include Resolution

`resolve_includes` discovers Home Assistant include directives in one already loaded `YamlDocument` and resolves their paths against `ProjectTree`.

`YamlLoader` remains the only component that reads YAML. An include tag becomes an `IncludeNode` in `YamlDocument.data`. The loader does not open the referenced path and does not merge its contents into the document.

Supported directives:

- `!include`
- `!include_dir_list`
- `!include_dir_named`
- `!include_dir_merge_list`
- `!include_dir_merge_named`

Relative paths join to the directory of the containing document. `!include` matches one stored `ProjectFile`. Directory directives match YAML files stored directly in that folder, in relative POSIX order. A known directory with no YAML children is resolved and empty. A path that is missing, outside the repository, or the wrong kind of entry is unresolved.

Resolution does not recursively expand includes, merge YAML, expand packages, or build a configuration model.

---

## HomeAssistantModel

Immutable aggregate of already-parsed registry objects (entities, devices, areas, labels, floors, config entries).

Provides O(1) read-only lookups. Performs no parsing and no relationship assembly.

Generators never access the filesystem directly.

---

## YamlRepository

Immutable aggregate of already-parsed YAML domain objects (packages, structures, automations, scripts, scenes, helpers, dashboards, blueprints, templates, ESPHome devices).

ESPHome devices are `ESPHomeDevice` values, sorted by name then path. `get_esphome_device` looks up a device by `name`. A device without a name stays in the collection and is not indexed. Sensors, binary sensors and switches are component models on the device. The repository does not store the source YAML mapping.

Provides O(1) read-only lookups. Performs no parsing and no relationship assembly.

---

## ESPHome Domain

`ESPHomeParser` translates one `YamlDocument` into one immutable
`ESPHomeDevice`. The device holds `name`, `friendly_name`, the
document path, and tuples of `ESPHomeSensor`, `ESPHomeBinarySensor`
and `ESPHomeSwitch`.

A component stores `identity`, `platform`, `id` and `name`.
`identity` is `{device-name}:{id}` when the ESPHome id is present,
otherwise `{device-name}:{name}`. Without a device name the identity
is the id, or the name when the id is absent. A block with neither id
nor name is omitted. Nested mappings under `sensor`,
`binary_sensor` and `switch` are included, and they keep the nearest
`platform`. Components are ordered by identity, platform, name and
id. Duplicate identities collapse to one component.

Substitutions are not expanded. An include directive is skipped and
its target is not loaded. Other YAML keys are not retained. The
parser does not discover files and does not call `YamlLoader`.

`ObjectType` includes `ESPHOME_DEVICE`, `ESPHOME_SENSOR`,
`ESPHOME_BINARY_SENSOR` and `ESPHOME_SWITCH`. `RelationshipRepository`
can store edges that use those kinds. This layer does not discover
those edges.

---

## Relationship Analysis

Analyzers derive explicit directed links as `tuple[Relationship, ...]`.

Examples:

- EntityRelationshipAnalyzer
- DeviceRelationshipAnalyzer
- AutomationRelationshipAnalyzer
- ScriptRelationshipAnalyzer
- DashboardRelationshipAnalyzer
- MQTTRelationshipAnalyzer

`RelationshipRepository` stores merged relationships with read-only identity lookups (`by_source`, `by_target`, `by_relationship`, `between`).

---

## AnalysisModel

Immutable aggregate of one completed analysis. Holds references to the existing `HomeAssistantModel`, `YamlRepository` and `RelationshipRepository`.

It does not copy, merge or interpret those aggregates. Registry, YAML and relationship responsibilities stay where they are. ESPHome devices are not a fourth field; they are reached through `YamlRepository`. `DependencyGraph` remains a separate structure.

---

## DependencyGraph

Immutable node/edge representation of a `RelationshipRepository`.

Built by the stateless `DependencyGraphBuilder`. Lookup API: `outgoing`, `incoming`, `contains`.

No visualisation, traversal algorithms or dependency scoring.

---

## Generators

Generators transform analysed data into documentation.

Examples:

- Statistics Generator
- Dependency Generator
- Entity Generator
- Dashboard Generator
- Integration Generator

Generators contain no file I/O.

---

## Home Assistant Inventory Reporting

`HomeAssistantInventoryGenerator` projects an already-built `AnalysisModel`
into an immutable `HomeAssistantInventory`.

`discovered_files` are source paths already stored on packages and
blueprints in `YamlRepository`. Each `DiscoveredFile.path` is that
existing `Path`. A discovered file is not a Home Assistant object. A
path does not mean the file produced an automation, script, scene,
blueprint, helper or label.

Parsed objects are the original repository instances:

- automations, scripts, scenes, helpers and blueprints come from `YamlRepository`
- labels come from `HomeAssistantModel`

An object keeps the package or path already stored on it. The projection
does not copy the object and does not add relationship state. A label
has no YAML path. Several parsed objects may share one package path. A
package path remains in `discovered_files` when that package contains
none of these objects.

Files are ordered by POSIX path. Repeated paths collapse to one entry.
Automations and scripts are ordered by id, alias, package name and
package path, with missing ids and aliases last. Scenes use id, name,
package name and path. Blueprints use path, name and domain, with a
missing path last. Helpers use type, id, package name and path. Labels
use registry id and name.

The generator does not read `ProjectTree`, walk the filesystem, parse
YAML or modify the analysis. `scanner_diagnostics` remains the inventory
of discovered `ProjectFile` instances. Module 9 `InventoryReportGenerator`
is unchanged. Dashboards, templates, ESPHome devices and relationships
are not projected.

---

## AI Context

`ContextGenerator` projects an already-built `AnalysisModel` into an
immutable `AIContext`.

Registry sections are unchanged from Module 13.1: one section per
non-empty `HomeAssistantModel` collection, items are the original
registry objects, and metadata stays empty because the aggregate does
not carry repository name, project path, version or a generation
timestamp.

`EntityContext` is one object per registry entity. It keeps that
entity, the relationships already stored for its `entity_id`, and
package objects those relationships name when the package is already
in `YamlRepository`.

`AutomationContext` is one object per automation in `YamlRepository`.
Triggers, conditions, actions and package come from that automation
object. Related entities, scripts and scenes are existing objects
resolved from relationships. Missing targets stay unresolved ids.

`DashboardContext` is one object per dashboard in `YamlRepository`.
It keeps that dashboard, including its metadata, and the same opaque
`views` tuple. No view key is read. Referenced entities and related
automations are existing objects resolved from relationships already
stored for the dashboard id, or the title when the id is absent.
Missing targets stay unresolved ids.

`PackageContext` is one object per package in `YamlRepository`. It
keeps that package. Name, path and document stay on the package object.
Automations, scripts, scenes, helpers and templates are the original
objects whose package reference is that same package. Dashboards have
no package reference, so they are not members. Referenced entities,
scripts, scenes and dashboards are existing objects resolved from
relationships already stored for the package name. Missing targets stay
unresolved ids. A reference stored on an automation, script or scene is
not copied onto the package, and an equal package copy is not treated
as the same owner.

The generator does not parse files, discover relationships, validate
configuration or write output. It does not render a prompt.

### ESPHome Context

`ESPHomeDeviceContext` is one object per ESPHome device in
`YamlRepository`. The device object is the overview: `name`,
`friendly_name` and `path` stay on that object.

`ESPHomeSensorContext`, `ESPHomeBinarySensorContext` and
`ESPHomeSwitchContext` are one object per component stored on that
device. Identity, platform, id and name stay on the component.

Related Home Assistant entities are existing `Entity` objects. They
come from relationships already stored for the device `name`, or for
the component `identity` together with that component's `ObjectType`.
A device without a name contributes no relationships. Edges whose
other endpoint is not an entity stay in `RelationshipRepository`.
Missing entity ids stay unresolved ids. A component reference is not
copied onto the device, and a component name is not matched to an
entity id.

Device contexts are ordered by name, then POSIX path, with unnamed
devices last. Component contexts are ordered by identity, platform,
name and id. `ContextGenerator` emits `esphome_contexts`.
`AnalysisModel` does not gain a field.

`PromptBuilder` does not select these contexts. `scanners/esphome.py`
stays empty. The legacy mutable `ESPHomeNode` on the scan model is
unchanged and is not the domain model. The production pipeline does
not load ESPHome YAML.

---

## Prompt Builder

`PromptBuilder` organises an existing `AIContext` into an immutable
`Prompt`. It is a presentation layer. It reads `AIContext` only.

It does not read repositories, `AnalysisModel`, YAML or the filesystem.
It does not discover relationships, validate configuration or interpret
dashboard views. It does not modify `AIContext`.

Each `PromptType` has a fixed section list, in `AIContext` field order:

- Generic keeps metadata, registry sections, entity contexts, automation
  contexts, dashboard contexts and package contexts.
- Programming keeps entity, automation and package contexts.
- Refactoring keeps entity, automation, dashboard and package contexts.
- Documentation keeps dashboard and package contexts.

`esphome_contexts` is stored on `AIContext` and is not part of these
lists.

Empty collections are omitted. Selected collections are the original
tuples. Instructions name the task and forbid invented facts. They do
not name a language-model provider, and they do not choose an export
format.

---

## AI Export

Exporters in `ha_docgen.export` render an existing `Prompt`. The public
entry points are `PromptExporter`, `MarkdownExporter`, `JsonExporter`
and `PlainTextExporter`. `ExportFormat` is `markdown`, `json` or
`plain_text`.

`PromptExporter.export` accepts a `Prompt` and an `ExportFormat`. Each
format exporter accepts a `Prompt` only. They do not read
`AnalysisModel`, `AIContext`, repositories or YAML, and they do not
modify the prompt.

Markdown and plain text include a display title taken from
`PromptType`, the prompt type, the system instructions, the task
description and each stored section. JSON emits the stored prompt
fields only. It does not add that display title. Object keys are
sorted. Section order and other sequence order are kept. Paths are
POSIX strings. Dates are ISO-8601. Enums are their values. Properties
and private fields are omitted.

These exporters return text. They do not write files. Document
`MarkdownExporter` remains the file writer for `Document` objects.

---

## Writers

Writers are responsible for writing output to disk.

Supported formats include:

- Markdown
- JSON
- HTML (future)

Generators produce content.

Writers persist content.

---

# Design Principles

The architecture follows several core principles.

## Read-only

The Home Assistant configuration is never modified.

---

## Single Responsibility

Each component has exactly one responsibility.

---

## One Repository Scan

The filesystem is scanned only once.

All later processing uses the ProjectTree. Production code calls `discover_project` for that scan. The production pipeline then reads `project_files()`, `root_yaml_files()`, `resolve_includes()` and `scanner_diagnostics()` from that tree. Consumers do not call `Path.rglob` or `Path.iterdir` to rediscover the repository.

---

## Separation of Concerns

Scanning, modelling, generating and writing are fully separated.

---

## Strong Typing

All shared data is represented by typed dataclasses.

---

## Central Logging

All console output goes through the application Logger.

Rich is isolated behind the logging implementation.

Runtime diagnostics and process exit codes are handled at the entry point.

---

## Central ScanPolicy

Filesystem inclusion and exclusion decisions belong to `ScanPolicy`.

Scanners must not embed hardcoded ignore logic.

`IgnoreRules` supply the rule sets (directories, filenames, patterns);
the policy evaluates them.

---

## Ignore Rules

Default ignore data lives in `policy/ignore_rules.py` as an immutable
`IgnoreRules` value object.

`ScanPolicy` consumes these rules. Scanners never see the rule sets
directly.

Later modules may extend rules with `.gitignore` parsing, include rules
and user configuration without changing scanner code.

---

## Modular Design

Every module should be independently testable.

---

## Extensibility

New scanners and generators can be added without changing existing components.

---

# Future Architecture

Documentation generation (Module 7) and later completed modules are
recorded in `roadmap.md`. AI Context consumes analysed models and does
not write files.

Home Assistant Inventory Reporting is a projection of the completed
`AnalysisModel`. Discovered `ProjectFile` instances remain on
`ProjectTree` and in `scanner_diagnostics`. Parsed objects remain on
the repositories.

Still planned:

- Duplicate Detection
- Unused Entity Detection
- HTML Documentation
- Interactive Documentation