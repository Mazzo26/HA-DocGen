# Design Decisions

## Purpose

This document records the architectural decisions made during the development of HA-DocGen.

The objective is to document **why** specific design choices were made.

Implementation details belong in the source code.

Technical architecture belongs in `architecture.md`.

This document explains the reasoning behind important decisions.

---

# Decision Record Format

Each decision is documented using the following structure.

## Decision

A short description.

## Status

- Proposed
- Accepted
- Deprecated
- Replaced

## Motivation

Why was this decision made?

## Consequences

What are the advantages?

What are the trade-offs?

---

# ADR-001

## Title

HA-DocGen is Read-Only

## Status

Accepted

## Motivation

Documentation generation must never introduce changes to a production Home Assistant installation.

Read-only behaviour guarantees that running HA-DocGen cannot damage configuration or historical data.

## Consequences

Advantages:

- Safe to execute
- No risk of configuration corruption
- Can be used on production systems

Trade-offs:

- Configuration corrections must always be performed manually.

---

# ADR-002

## Title

Single Repository Scan

## Status

Accepted

## Motivation

Scanning the repository multiple times increases execution time and complicates synchronisation.

The repository should only be scanned once.

## Consequences

Advantages:

- Faster execution
- Consistent data
- Lower disk I/O

Trade-offs:

- Additional memory usage for ProjectTree.

---

# ADR-003

## Title

ProjectTree as Central Data Source

## Status

Accepted

## Motivation

Every scanner requires information about the repository.

Creating a shared ProjectTree avoids repeated filesystem access.

## Consequences

Advantages:

- Better performance
- Cleaner architecture
- Shared object model

Trade-offs:

- ProjectTree must remain synchronised.

---

# ADR-004

## Title

FilesystemEntry Dataclass

## Status

Accepted

## Motivation

Filesystem objects should expose a consistent interface.

Using dataclasses simplifies typing and testing.

## Consequences

Advantages:

- Strong typing
- Easier unit testing
- Cleaner code

Trade-offs:

- Slightly more abstraction.

---

# ADR-005

## Title

Separation of Scanners and Generators

## Status

Accepted

## Motivation

Scanning and documentation generation are separate concerns.

Scanners collect information.

Generators transform information.

## Consequences

Advantages:

- Better modularity
- Easier testing
- Easier future extensions

Trade-offs:

- More project structure.

---

# ADR-006

## Title

Markdown as Primary Output

## Status

Accepted

## Motivation

Markdown is human-readable, version-control friendly and supported by GitHub, Cursor and most documentation systems.

## Consequences

Advantages:

- Easy diffing
- Portable
- Lightweight

Trade-offs:

- Limited layout capabilities.

---

# ADR-007

## Title

Strong Typing Throughout the Application

## Status

Accepted

## Motivation

HA-DocGen is expected to become a large codebase.

Strong typing reduces bugs and improves maintainability.

## Consequences

Advantages:

- Better IDE support
- Easier refactoring
- Safer development

Trade-offs:

- Slightly more verbose code.

---

# ADR-008

## Title

One Responsibility per Module

## Status

Accepted

## Motivation

Modules should remain small and independently testable.

## Consequences

Advantages:

- Easier maintenance
- Better readability
- Simpler testing

Trade-offs:

- More files.

---

# ADR-009

## Title

Shared Constants Package

## Status

Accepted

## Motivation

Project-wide values such as extensions, ignore directory names and Home Assistant folder names were duplicated across scanners and utilities.

A dedicated constants package provides a single source of truth without introducing policy or parsing logic.

## Consequences

Advantages:

- No duplicated literals
- Clear split between generic filesystem constants and Home Assistant project constants
- Glob patterns stay derived from extension constants

Trade-offs:

- Additional package structure

---

# ADR-010

## Title

Central Logging Abstraction

## Status

Accepted

## Motivation

Direct Rich console usage coupled presentation to application logic and made
consistent log levels, diagnostics and exit handling impossible.

## Consequences

Advantages:

- Callers emit plain strings through a single Logger API
- Rich remains an implementation detail of `logging.py`
- Diagnostics and user-friendly errors share one reporting path
- Process exit codes are explicit and stable

Trade-offs:

- An additional diagnostics module is required for runtime metadata

---

# ADR-011

## Title

Central ScanPolicy

## Status

Accepted

## Motivation

Filesystem inclusion and exclusion decisions lived inside scanners (for example
`IGNORE_DIRS` checks in `FilesystemScanner`). That couples discovery with policy
and duplicates logic as more scanners appear.

A dedicated, read-only `ScanPolicy` owns path decisions. Constants remain pure
data; Module 3.7 extends the policy with richer ignore rules without
changing scanner code.

## Consequences

Advantages:

- Single place for include/exclude decisions
- Scanners stay free of hardcoded ignore logic
- Clear separation: constants (data) vs policy (evaluation)
- Ready for Ignore Rules (Module 3.7) via dependency injection

Trade-offs:

- An additional package and an injected dependency for scanners

---

# ADR-012

## Title

Ignore Rules as Policy Data

## Status

Accepted

## Motivation

`ScanPolicy` previously embedded a single directory-name set. Filename and
pattern exclusions, and future configuration sources, do not belong inline in
the policy API that scanners call.

A dedicated, immutable `IgnoreRules` value object holds directories, exact
filenames and filename patterns. `ScanPolicy` evaluates those rules. Defaults
are defined in `ignore_rules.py` and currently preserve the previous
directory-only behaviour (empty filename and pattern sets).

`.gitignore` parsing, include rules and user configuration are deferred so
this module stays focused and behaviour-compatible.

## Consequences

Advantages:

- Clear split: rule data (`IgnoreRules`) vs decision API (`ScanPolicy`)
- Scanners remain unchanged except for consuming the existing policy API
- Ready for configurable and gitignore-backed rules without scanner churn
- Defaults stay explicit and testable in one module

Trade-offs:

- An additional policy module
- Pattern matching (`fnmatch`) adds a small evaluation cost when patterns
  are configured later

---

# ADR-013

## Title

Separate Storage Discovery from Registry Parsing

## Status

Accepted

## Motivation

Home Assistant's `.storage` directory contains both opaque runtime files and
structured registries (entity, device, area, and related stores). Mixing
filesystem discovery with JSON/registry interpretation would couple Module 4.1
to later semantic parsers and invite duplicated I/O.

A dedicated, read-only `StorageScanner` therefore collects only file metadata
into a `StorageInventory`. Registry parsers consume that inventory later and
perform content-aware analysis in their own modules.

## Consequences

Advantages:

- Clear boundary between discovery and Home Assistant semantics
- No JSON parsing or registry knowledge in the storage package
- Reuse of ProjectTree / FilesystemEntry / ScanPolicy without a second full
  repository walk when a tree is already available
- Future Entity Registry and Device Registry parsers stay independent

Trade-offs:

- An additional package (`ha_docgen.storage`) before registry features land
- Callers must compose discovery and parsing explicitly

---

# ADR-014

## Title

Storage Inventory API

## Status

Accepted

## Motivation

Module 4.1 introduced storage discovery and a passive `StorageInventory`
container. Future registry parsers (entity, device, area, and related stores)
need a single, stable way to locate storage files by name without re-walking
the filesystem or embedding discovery logic in each parser.

`StorageInventory` therefore becomes the only query API over discovered
storage files: expose the collection, look up by filename in O(1), check
existence, and iterate. The scanner remains responsible solely for discovery;
the inventory owns querying. No JSON parsing and no Home Assistant semantics
belong in this layer.

## Consequences

Advantages:

- One access point for all future registry parsers
- O(1) filename lookup without repeated linear scans
- Clear separation: scanner discovers, inventory queries, parsers interpret
- Read-only surface (`tuple` + `MappingProxyType`) discourages mutation

Trade-offs:

- Filename collisions collapse to a single index entry (last write wins)
- Callers must obtain an inventory from `StorageScanner` before querying

---

# ADR-015

## Title

Entity Registry as a Pure Parser Package

## Status

Accepted

## Motivation

Module 4.1–4.2 discover `.storage` files but deliberately avoid JSON and
Home Assistant semantics. Entity analysis needs a typed model of
`core.entity_registry` without coupling to filesystem discovery,
`StorageInventory` mutation, filtering, or the unfinished
`HomeAssistantModel`.

A dedicated `ha_docgen.registries` package therefore owns a compact
`Entity` dataclass and a pure `EntityRegistryParser` that reads one
registry path and returns `Entity` objects. The public model mirrors HA
architecture (identity, relationships, display, visibility) rather than
every JSON key. Leftover fields stay in an immutable `extra` mapping so
the API remains stable while the parser can still retain opaque data.

## Consequences

Advantages:

- Clear boundary: storage discovers files; registries parse contents
- Compact, documentation-oriented `Entity` API with derived `domain`
- Orphaned and incomplete entries parse safely via defaults
- No premature wiring into devices, areas, config entries or relationships

Trade-offs:

- Callers must supply the registry path (config or inventory lookup)
- Fields such as `platform` / `options` are only available via `extra`
  until a later module promotes them intentionally

---

# ADR-016

## Title

Device Registry as a Pure Parser

## Status

Accepted

## Motivation

Module 4.3 established `ha_docgen.registries` as the home for typed
registry parsers that remain independent of filesystem discovery and of
the unfinished `HomeAssistantModel`. Device analysis needs the same
boundary for `core.device_registry`: a compact `Device` model and a
parser that reads one path and returns immutable `Device` objects.

The parser must not couple to `EntityRegistryParser`, areas, labels or
config-entry semantics. Relationship assembly belongs in Module 4.9.
Storage formats vary across Home Assistant versions (`config_entries`
lists versus a singular `config_entry_id`); normalising both into
`Device.config_entries` keeps the public API stable without promoting
opaque fields prematurely.

## Consequences

Advantages:

- Same architecture as the Entity parser: path in, `tuple[Device, ...]` out
- Clear separation from Entity parsing and future HomeAssistantModel wiring
- Safe defaults for missing or incomplete device entries
- Version-tolerant config-entry normalisation with leftover JSON in `extra`

Trade-offs:

- Callers must supply the registry path (config or inventory lookup)
- Fields such as `name_by_user` / `entry_type` remain in `extra` until
  a later module promotes them intentionally
- Small type-coercion helpers are duplicated per parser to keep
  registry modules independent

---

# ADR-017

## Title

Area Registry as a Pure Parser

## Status

Accepted

## Motivation

Modules 4.3–4.4 established pure registry parsers for entities and
devices. Area analysis needs the same boundary for
`core.area_registry`: a compact `Area` model and a parser that reads
one path and returns immutable `Area` objects.

The parser must not couple to devices, entities, floors, labels or
config-entry semantics. Fields such as `floor_id` and climate entity
IDs stay in `extra` until Module 4.9 assembles relationships. Keeping
the public API limited to identity, metadata and lifecycle preserves
stability across Home Assistant versions.

## Consequences

Advantages:

- Same architecture as Entity/Device parsers: path in, `tuple[Area, ...]` out
- Clear separation from relationship assembly in HomeAssistantModel
- Safe defaults for missing or incomplete area entries
- Version-tolerant retention of opaque fields via `extra`

Trade-offs:

- Callers must supply the registry path (config or inventory lookup)
- Fields such as `floor_id` / `icon` / climate entity IDs remain in
  `extra` until a later module promotes them intentionally
- Small type-coercion helpers are duplicated per parser to keep
  registry modules independent

---

# ADR-018

## Title

Label Registry as a Pure Parser

## Status

Accepted

## Motivation

Modules 4.3–4.5 established pure registry parsers for entities, devices
and areas. Label analysis needs the same boundary for
`core.label_registry`: a compact `Label` model and a parser that reads
one path and returns immutable `Label` objects.

The parser must not couple to entities, devices, areas or
HomeAssistantModel. Labels are referenced elsewhere via ID strings;
relationship assembly belongs in Module 4.9. Keeping the public API
limited to identity, display and lifecycle preserves stability across
Home Assistant versions.

## Consequences

Advantages:

- Same architecture as Entity/Device/Area parsers: path in,
  `tuple[Label, ...]` out
- Clear separation from relationship assembly in HomeAssistantModel
- Safe defaults for missing or incomplete label entries
- Version-tolerant retention of opaque fields via `extra`

Trade-offs:

- Callers must supply the registry path (config or inventory lookup)
- Home Assistant stores identity as `label_id`; the model exposes it as
  `registry_id` for consistency with other registry models
- Small type-coercion helpers are duplicated per parser to keep
  registry modules independent

---

# ADR-019

## Title

Floor Registry as a Pure Parser

## Status

Accepted

## Motivation

Modules 4.3–4.6 established pure registry parsers for entities, devices,
areas and labels. Floor analysis needs the same boundary for
`core.floor_registry`: a compact `Floor` model and a parser that reads
one path and returns immutable `Floor` objects.

The parser must not couple to areas, entities, devices or
HomeAssistantModel. Areas reference floors via ID strings;
relationship assembly belongs in Module 4.9. Keeping the public API
limited to identity, display (`level`, `icon`) and lifecycle preserves
stability across Home Assistant versions.

## Consequences

Advantages:

- Same architecture as Entity/Device/Area/Label parsers: path in,
  `tuple[Floor, ...]` out
- Clear separation from relationship assembly in HomeAssistantModel
- Safe defaults for missing or incomplete floor entries
- Version-tolerant retention of opaque fields via `extra`

Trade-offs:

- Callers must supply the registry path (config or inventory lookup)
- Home Assistant stores identity as `floor_id`; the model exposes it as
  `registry_id` for consistency with other registry models
- Fields such as `aliases` remain in `extra` until a later module
  promotes them intentionally
- Small type-coercion helpers are duplicated per parser to keep
  registry modules independent

---

# ADR-020

## Title

Config Entry Registry as a Pure Parser

## Status

Accepted

## Motivation

Modules 4.3–4.7 established pure registry parsers for entities, devices,
areas, labels and floors. Config entry analysis needs the same boundary
for `core.config_entries`: a compact `ConfigEntry` model and a parser
that reads one path and returns immutable `ConfigEntry` objects.

The parser must not couple to entities, devices, areas, labels, floors
or HomeAssistantModel. Other registries reference config entries via ID
strings; relationship assembly belongs in Module 4.9. Keeping the public
API limited to identity, status, preferences and lifecycle preserves
stability across Home Assistant versions. Integration-specific `data`
and `options` remain opaque in `extra`.

## Consequences

Advantages:

- Same architecture as Entity/Device/Area/Label/Floor parsers: path in,
  `tuple[ConfigEntry, ...]` out
- Clear separation from relationship assembly in HomeAssistantModel
- Safe defaults for missing or incomplete config entries
- Version-tolerant retention of opaque fields via `extra`

Trade-offs:

- Callers must supply the registry path (config or inventory lookup)
- Home Assistant stores identity as `entry_id`; the model exposes it as
  `registry_id` for consistency with other registry models
- Fields such as `data`, `options`, `unique_id` and `subentries` remain
  in `extra` until a later module promotes them intentionally
- Small type-coercion helpers are duplicated per parser to keep
  registry modules independent

---

# ADR-021

## Title

HomeAssistantModel as Immutable Registry Aggregate

## Status

Accepted

## Motivation

Modules 4.3–4.8 deliver typed registry parsers but no shared container for
their results. Downstream modules (YAML analysis, relationships,
documentation, validation, reporting) need a stable, read-only public API
over all registry metadata without coupling to JSON, filesystem discovery
or relationship assembly.

`HomeAssistantModel` therefore accepts only already-parsed registry
objects, freezes them as tuples, and builds O(1) `MappingProxyType`
indexes in `__post_init__`. Relationship graphs (`entity.device`,
`device.entities`, orphan detection, dependency analysis) remain Module 6.
YAML and other configuration objects remain Module 5.

The Module 2 scaffold named `HomeAssistantModel` in `ha_docgen.models`
(scan statistics / folders) is left untouched; the registry aggregate lives
in `ha_docgen.registries` until a later wiring module unifies both surfaces.

## Consequences

Advantages:

- Single immutable API for all Module 4 registry data
- O(1) lookups without exceptions on missing identifiers
- Clear boundary: parsers produce objects; the model only stores and indexes
- No premature relationship or business logic

Trade-offs:

- Callers must assemble parser outputs before construction
- Two classes currently share the historical name `HomeAssistantModel`
  (Module 2 scaffold vs registry aggregate) until wiring consolidates them
- ID string references between objects are not resolved here

---

# ADR-022

## Title

YamlDocument as Generic YAML Representation

## Status

Accepted

## Motivation

Module 5 must analyse many YAML surfaces (packages, automations, scripts,
dashboards, blueprints, templates, and more). Those parsers must not each
reinvent how a loaded file is held in memory, and loading must stay
separate from domain interpretation.

`YamlDocument` is therefore the generic, immutable representation of
exactly one YAML document: source `path`, original `text`, and already-
parsed Python `data`. It performs no I/O, no parsing, no validation and
no Home Assistant logic. All subsequent YAML modules consume
`YamlDocument` instances; a dedicated loader (Module 5.2) will produce
them.

## Consequences

Advantages:

- Single shared contract for every YAML parser
- Clear separation between loading and interpreting YAML
- Immutable, testable data object with no side effects

Trade-offs:

- Callers must supply already-loaded text and parsed data
- Domain models (Package, Automation, …) remain later modules

---

# ADR-023

## Title

YamlLoader as Sole YAML File Reader

## Status

Accepted

## Motivation

Module 5.1 introduced `YamlDocument` but left filesystem I/O and YAML
parsing unspecified. Without a single loader, every future scanner
(packages, automations, scripts, dashboards, blueprints, templates)
would risk duplicating read/parse logic and mixing loading with domain
interpretation.

`YamlLoader` is therefore the only component that reads YAML files: it
opens a path with `DEFAULT_ENCODING`, retains the original text, parses
with `yaml.safe_load`, and returns an immutable `YamlDocument`. Failures
surface as `YamlLoadError` with exception chaining. Loading and
interpretation stay strictly separated; all subsequent YAML parsers
consume `YamlDocument` only and never open YAML files themselves.

## Consequences

Advantages:

- One place owns YAML I/O and safe parsing
- Clear boundary: loader produces `YamlDocument`; parsers interpret it
- Consistent error surface via `YamlLoadError`

Trade-offs:

- Existing helpers (e.g. config bootstrap) may still use PyYAML until a
  later consolidation
- Domain scanners remain responsible for discovering which paths to load

---

# ADR-024

## Title

Package Scanner Discovers and Loads Only

## Status

Accepted

## Motivation

Module 5.2 provides `YamlLoader` but does not decide which package files
to open. Home Assistant package YAML must be discovered before any
domain model can interpret it. Mixing discovery, loading and package
semantics in one component would couple filesystem traversal to future
PackageStructure / automation / script parsers.

`PackageScanner` is therefore responsible solely for discovering
`.yaml` / `.yml` files under a package directory and loading each via
an injected `YamlLoader` into an immutable `tuple[YamlDocument, ...]`.
YAML interpretation (entities, automations, helpers, relationships)
remains outside the scanner and is deferred to later modules.

## Consequences

Advantages:

- Clear single responsibility: discover + load, nothing else
- Reuses `YamlLoader` / `YamlDocument` without duplicating I/O
- Later parsers can consume documents without filesystem access

Trade-offs:

- No package domain model yet; callers receive raw `YamlDocument` only
- Invalid or semantically empty packages still load successfully

---

# ADR-025

## Title

Package as Immutable Package Representation

## Status

Accepted

## Motivation

Module 5.3 delivers `PackageScanner`, which returns raw `YamlDocument`
tuples. Callers and later parsers need a stable public type for one
Home Assistant package without yet interpreting YAML contents or
introducing automations, scripts, sensors, templates, or other domain
objects.

`Package` is therefore the immutable representation of exactly one
package: `name`, `path`, and the already-loaded `YamlDocument`. It
performs no I/O, no YAML interpretation and no Home Assistant
semantics. Wiring from scanner output to `Package` remains a later
step; `PackageScanner` stays discovery-and-load only.

## Consequences

Advantages:

- Clear public contract for a single package before deeper parsing
- Reuses `YamlDocument` without duplicating load state
- Keeps interpretation and scanner wiring out of this module

Trade-offs:

- Callers must still construct `Package` themselves until wiring lands
- YAML structure inside `document` remains uninterpreted

---

# ADR-026

## Title

Package Parser Detects Structure Only

## Status

Accepted

## Motivation

Module 5.4 provides `Package` as an immutable package representation, but
does not yet expose which Home Assistant components a package declares.
Callers need a structural view of top-level sections (for example
`automation`, `script`, `mqtt`, `template`) without interpreting the
contents of those sections.

`PackageParser` therefore inspects `package.document.data` only: it
checks that the root is a mapping (`dict`), collects every top-level
key, stores them as a sorted immutable `tuple[str, ...]`, and returns
an immutable `PackageStructure` (`package`, `sections`). Interpretation of
individual sections remains the responsibility of specialised parsers
(`AutomationParser`, `ScriptParser`, and similar) in later modules.
`PackageParser` itself stays fully generic.

## Consequences

Advantages:

- Clear separation between structure detection and domain interpretation
- Stable `PackageStructure` contract for later specialised parsers
- No premature coupling to automations, scripts, MQTT, templates, or entities

Trade-offs:

- Section names are opaque strings; validity is not checked
- Empty or non-mapping roots yield an empty `sections` tuple

---

# ADR-027

## Title

Section Model

## Status

Accepted

## Motivation

Module 5.5 exposes top-level package structure as opaque section *names*
(`tuple[str, ...]`). Specialised parsers (`AutomationParser`,
`ScriptParser`, `MQTTParser`, and similar) will need the raw YAML value
of each section, not only its name, while remaining decoupled from
`PackageParser`.

`Section` is therefore the generic immutable representation of exactly
one top-level package YAML section: `name` plus the raw YAML `data`.
It adds no Home Assistant semantics, parsing, or validation.
`PackageStructure.sections` becomes `tuple[Section, ...]`, with read-only
`has_section` / `get_section` helpers backed by a `MappingProxyType`
index built in `__post_init__` for O(1) lookup.

`PackageParser` remains responsible for structure detection only: it
creates one `Section` per top-level YAML key and stores the exact YAML
value as `data`. Specialised parsers work later exclusively on
`Section` instances; interpretation stays out of `PackageParser`.

## Consequences

Advantages:

- Stable generic contract between structural parsing and domain parsers
- Raw section data preserved without premature interpretation
- O(1) section lookup without mutating `PackageStructure`

Trade-offs:

- Section names remain opaque strings; validity is not checked
- Empty or non-mapping roots still yield an empty `sections` tuple

---

# ADR-028

## Title

Automation Parser

## Status

Accepted

## Motivation

Module 5.6 provides `Section` as a generic container for top-level
package YAML. Callers need a typed, immutable view of automations
without coupling to entities, devices, scripts, or
`HomeAssistantModel`.

`Automation` is therefore the immutable representation of exactly one
automation: first-class fields (`id`, `alias`, `description`, `mode`,
`triggers`, `conditions`, `actions`) plus a `MappingProxyType` `raw`
for unknown keys. Triggers, conditions and actions remain opaque YAML
values; no templates, services or schemas are interpreted.

`AutomationParser` is solely responsible for converting a
`Section("automation")` into `tuple[Automation, ...]`. It accepts both
Home Assistant shapes (YAML list and named mapping), uses safe defaults
for missing optional fields, and rejects any other section name.
Validation, relationship building and semantic interpretation belong
in later modules.

## Consequences

Advantages:

- Clear boundary between YAML structure and later domain analysis
- Stable `Automation` contract for script/scene parsers and graphs
- Both HA package forms supported without premature semantics

Trade-offs:

- Singular HA keys (`trigger` / `condition` / `action`) are aliases
  only; no schema validation of their contents
- Dict-form keys are not promoted to `id` (no identity inference)

---

# ADR-029

## Title

Script Parser

## Status

Accepted

## Motivation

Module 5.6 provides `Section` as a generic container for top-level
package YAML. Callers need a typed, immutable view of scripts without
coupling to entities, automations, devices, or `HomeAssistantModel`.

`Script` is therefore the immutable representation of exactly one
Home Assistant script: first-class fields (`id`, `alias`,
`description`, `icon`, `mode`, `sequence`, `fields`, `variables`)
plus a `MappingProxyType` `raw` that retains the complete original
YAML mapping. Unknown keys remain solely in `raw`. Sequence, fields
and variables stay opaque YAML values; no templates, services or
schemas are interpreted.

`ScriptParser` is solely responsible for converting a
`Section("script")` into `tuple[Script, ...]`. It accepts the
standard Home Assistant mapping form, uses the mapping key as `id`
when no explicit `id` is present, applies safe defaults for missing
optional fields, and rejects any other section name. Validation,
relationship building and semantic interpretation belong in later
modules.

## Consequences

Advantages:

- Clear boundary between YAML structure and later domain analysis
- Stable `Script` contract for dependency graphs and documentation
- Mapping-form identity matches Home Assistant entity_id suffixes

Trade-offs:

- List-form script sections are not interpreted (empty result)
- Sequence contents are not validated or expanded

---

# ADR-030

## Title

Scene Parser

## Status

Accepted

## Motivation

Module 5.6 provides `Section` as a generic container for top-level
package YAML. Callers need a typed, immutable view of scenes without
coupling to entities, devices, automations, scripts, or
`HomeAssistantModel`.

`Scene` is therefore the immutable representation of exactly one
Home Assistant scene: first-class fields (`id`, `name`, `icon`,
`entities`) plus a `MappingProxyType` `raw` that retains the complete
original YAML mapping. Unknown keys remain solely in `raw`. Entity
states and attributes stay opaque YAML values; no schemas or semantic
interpretation are applied.

`SceneParser` is solely responsible for converting a
`Section("scene")` into `tuple[Scene, ...]`. It accepts both the
standard Home Assistant list form and mapping forms when present,
uses the mapping key as `id` when no explicit `id` is present,
applies safe defaults for missing optional fields, and rejects any
other section name. Validation, relationship building and semantic
interpretation belong in later modules.

## Consequences

Advantages:

- Clear boundary between YAML structure and later domain analysis
- Stable `Scene` contract for dependency graphs and documentation
- List and mapping forms share one immutable model

Trade-offs:

- Entity state and attribute contents are not validated or normalised
- Scenes outside package YAML (for example root `scenes.yaml`) are
  not discovered by this module alone

---

# ADR-031

## Title

Generic Helper Parser

## Status

Accepted

## Motivation

Module 5.6 provides `Section` as a generic container for top-level
package YAML. Callers need a typed, immutable view of Home Assistant
helpers without coupling to entities, automations, scripts, or
`HomeAssistantModel`.

All helper domains are modelled as one generic `Helper` type. The
helper domain is stored in `Helper.type` (for example
`input_boolean`). First-class optional fields are `name` and `icon`;
`id` comes from the YAML mapping key. Unknown YAML keys remain solely
in a `MappingProxyType` `raw` that also retains the complete original
mapping.

`HelperParser` converts `tuple[Section, ...]` into
`tuple[Helper, ...]`. It processes only an extensible allow-list of
helper section names, ignores unknown top-level sections, applies safe
defaults for missing optional fields, and returns an immutable tuple.
New helper types require only an allow-list extension — no new parser
architecture. Validation and semantic interpretation belong in later
modules.

## Consequences

Advantages:

- One generic model covers every Home Assistant helper domain
- New helper types need no new parser architecture
- Clear boundary between YAML structure and later domain analysis
- Unknown top-level sections are safely ignored

Trade-offs:

- Helper-specific fields (min/max, options, duration, …) stay opaque
  in `raw` until later modules interpret them
- Helpers outside package YAML are not discovered by this module alone

---

# ADR-032

## Title

Dashboard Parser

## Status

Accepted

## Motivation

Module 5.2 provides `YamlDocument` as the generic representation of
loaded YAML. Callers need a typed, immutable view of Home Assistant
YAML dashboards without coupling to cards, entities, badges,
navigation, or `HomeAssistantModel`.

`Dashboard` therefore represents dashboard metadata only: optional
`id`, `title`, `mode`, source `path`, and a tuple of raw `views`.
Each view remains an opaque `MappingProxyType` with no card or
layout interpretation. Unknown YAML keys stay solely in `raw`, which
also retains the complete original dashboard mapping.

`DashboardParser` translates one `YamlDocument` into one immutable
`Dashboard`. It reads optional metadata safely (defaults of `None` or
empty tuples), freezes exposed mappings with `MappingProxyType`, and
performs no validation or semantic analysis. Card parsing, entity
detection, badge parsing, view models, navigation analysis,
conditional cards, template parsing, and relationship analysis belong
to later modules.

## Consequences

Advantages:

- Clear boundary between dashboard metadata and later card analysis
- Reuses `YamlDocument` without duplicating I/O or YAML loading
- Views stay available as raw structure for specialised follow-up parsers

Trade-offs:

- Cards, entities, badges and navigation remain uninterpreted
- UI-mode / storage dashboards are outside this YAML-only parser

---

# ADR-033

## Title

Blueprint Parser

## Status

Accepted

## Motivation

Module 5.2 provides `YamlDocument` as the generic representation of
loaded YAML. Callers need a typed, immutable view of Home Assistant
blueprint metadata without coupling to selectors, input validation,
automation generation, or `HomeAssistantModel`.

`Blueprint` therefore represents blueprint metadata only: optional
`name`, `description`, `domain`, `source_url`, source `path`, and a
raw `input` mapping. Inputs remain opaque with no selector
interpretation. Unknown YAML keys stay solely in `raw`, which also
retains the complete original blueprint document mapping.

`BlueprintParser` translates one `YamlDocument` into one immutable
`Blueprint`. It reads the standard Home Assistant `blueprint:` block,
applies safe defaults for missing optional fields (`None` or empty
immutable mappings), freezes exposed mappings with `MappingProxyType`,
and performs no validation or semantic analysis. Selector parsing,
input validation, automation generation, template parsing, and
relationship analysis belong to later modules.

## Consequences

Advantages:

- Clear boundary between blueprint metadata and later domain analysis
- Reuses `YamlDocument` without duplicating I/O or YAML loading
- Inputs stay available as raw structure for specialised follow-up parsers

Trade-offs:

- Selectors, input semantics and automation content remain uninterpreted
- Discovery of blueprint files is outside this YAML-only parser

---

# ADR-034

## Title

Template Parser

## Status

Accepted

## Motivation

Module 5 builds immutable representations of Home Assistant YAML. Callers
need a typed view of template strings found in packages without coupling
to Jinja interpretation, entity extraction, variable resolution, or
relationship analysis.

`Template` therefore represents a found template only: `kind` (origin
category such as `state`, `value`, or `availability`), exact `source`
string, optional source `path`, and the parent YAML mapping in `raw`.
No extra properties or business logic.

`TemplateParser` accepts a `PackageStructure` and returns
`tuple[Template, ...]`. It walks section data recursively, collects
strings under a fixed allow-list of known template field names, and
records unknown `*_template` field names for diagnostics. It does not
parse Jinja, evaluate templates, resolve variables, or build
dependencies. Jinja analysis and dependency graphs belong to
**Module 6 – Relationship Analysis**.

## Consequences

Advantages:

- Clear boundary between collecting template strings and understanding them
- Reuses `PackageStructure` without duplicating YAML loading
- Known-field allow-list keeps collection narrow and extensible

Trade-offs:

- Strings under ambiguous keys (e.g. `name`, `icon`, `state`) are
  collected whenever present; filtering by Jinja content is deferred
- No validation that `source` is well-formed Jinja

---

# ADR-035

## Title

YAML Repository

## Status

Accepted

## Motivation

Module 5 delivers typed parsers for packages, automations, scripts,
scenes, helpers, dashboards, blueprints and templates, but no shared
container for their results. Module 6 relationship analysis needs a
stable, read-only public API over all YAML domain objects — the YAML
counterpart of `HomeAssistantModel` — without coupling to scanners,
parsers or relationship assembly.

`YamlRepository` therefore accepts only already-parsed domain objects,
freezes them as tuples, and builds O(1) `MappingProxyType` indexes in
`__post_init__`. Lookups cover objects with a stable unique identifier
(package name, automation/script/scene/dashboard id, helper YAML key,
blueprint path). Templates are stored but not indexed: they have no
stable unique identifier. Relationships, entity linking, dependency
graphs and Home Assistant semantics remain **Module 6**.

## Consequences

Advantages:

- Single immutable API for all Module 5 YAML domain data
- O(1) lookups without exceptions on missing identifiers
- Clear boundary: parsers produce objects; the repository only stores
  and indexes
- Module 6 can depend solely on `HomeAssistantModel` and
  `YamlRepository`, not on scanners or parsers

Trade-offs:

- Callers must assemble parser outputs before construction
- Objects without an identifier (e.g. automations with `id is None`,
  templates) are retained in collections but are not lookup-indexed
- ID string references between objects are not resolved here

---

# ADR-036

## Title

Package Provenance on Domain Objects via PackageStructure

## Status

Accepted

## Motivation

Module 5 domain parsers produced `Automation`, `Script`, `Scene`,
`Helper` and `Template` objects without retaining their source
`Package`. `Section` must remain a pure YAML structure object
(`name`, `data` only). Callers need provenance on domain objects
without relationship analysis or enriching `Section`.

## Decision

- Add required `package: Package` to `Automation`, `Script`, `Scene`,
  `Helper` and `Template`
- Change specialised parsers to accept `PackageStructure` and set
  `package=structure.package` when constructing domain objects
- Keep `Section` free of package context
- Leave `Blueprint` and `Dashboard` unchanged (document-based, not
  package-section parsers)
- No business logic, linking or Module 6 relationship assembly

## Consequences

Advantages:

- Explicit provenance on package-derived domain objects
- `Section` stays a generic YAML container
- Single input type (`PackageStructure`) for package-section parsers

Trade-offs:

- Parsers no longer operate on a lone `Section`; missing sections
  yield an empty tuple instead of a section-name `ValueError`
- Import of `YamlRepository` from `ha_docgen.yaml` is lazy to avoid
  cycles between packages, yaml and domain parsers

---

# ADR-037

## Title

Relationship Models

## Status

Accepted

## Motivation

Module 6 relationship analysis needs a shared, immutable representation
of directed links between Home Assistant objects (entities, devices,
areas, automations, scripts, dashboards, packages, …). Later modules
(6.2–6.9) will discover and assemble those links; Module 6.1 must define
only the relational building blocks — without parsing, validation,
graph construction or domain coupling.

## Decision

- Introduce package `ha_docgen.relationships` with `Relationship` and
  `RelationshipCollection`
- `Relationship` is a frozen dataclass of identity fields only:
  `source_type`, `source_id`, `target_type`, `target_id`,
  `relationship_type`
- `source_type` / `target_type` use `ObjectType` (`StrEnum`);
  `relationship_type` uses `RelationshipType` (`StrEnum`);
  `source_id` / `target_id` remain plain `str`
- Enum members cover realistic Module 6 object and link kinds only
  (no Home Assistant-specific business vocabulary)
- No object references, no Home Assistant domain models, no graph edges
  beyond the identity tuple itself
- `RelationshipCollection` holds `tuple[Relationship, ...]` and builds
  read-only `MappingProxyType` indexes in `__post_init__`
- Public lookups: `by_source(type, id)` and `by_target(type, id)` for
  O(1) access; no filtering or analysis API
- Foundation for Modules 6.2–6.9; analysis and dependency graphs remain
  deferred

## Consequences

Advantages:

- Generic relational primitives reusable across all HA object kinds
- Type-safe object and relationship kinds via `StrEnum`
- Immutable, indexable collection without premature graph semantics
- Clear boundary: models only; discovery and assembly stay later

Trade-offs:

- New object or relationship kinds require an enum extension
- Indexes are identity-based only; relationship-type filtering is
  deferred to later modules

---

# ADR-038

## Title

Entity Relationship Analyzer

## Status

Accepted

## Motivation

Module 6.2 must derive entity relationships that are already explicit
in registry data (device, area, config entry, labels). Analyzers must
stay small, independent and free of aggregation concerns so later
analyzers (devices, areas, YAML, …) can compose without shared state.

## Decision

- Introduce `EntityRelationshipAnalyzer` with
  `analyze(model) -> tuple[Relationship, ...]`
- Analyzers produce only immutable `tuple[Relationship, ...]`; they do
  not return `RelationshipCollection`
- Analyzers know neither a graph nor a repository
- Analyzers are independent and composable; each owns one slice of
  relationship discovery
- Merging outputs from multiple analyzers is deferred to Module 6.8
- No YAML analysis, validation or business logic in this module
- `EntityRelationshipAnalyzer` analyseert uitsluitend expliciete
  relaties die in de registry aanwezig zijn. Afgeleide relaties
  (bijvoorbeeld Entity → Area via Device) worden bewust pas in
  latere modules opgebouwd.

## Consequences

Advantages:

- Clear single responsibility per analyzer
- Easy unit testing of pure relationship emission
- No premature coupling to collection, graph or repository layers

Trade-offs:

- Callers must hold raw tuples until Module 6.8 provides aggregation
- Cross-analyzer de-duplication is deferred

---

# ADR-039

## Title

Device Relationship Analyzer

## Status

Accepted

## Motivation

Module 6.3 must derive device relationships that are already explicit
in the Device Registry (area, config entries, labels). Analyzers must
stay small, independent and free of aggregation concerns so later
analyzers (packages, YAML, …) can compose without shared state.

## Decision

- Introduce `DeviceRelationshipAnalyzer` with
  `analyze(model) -> tuple[Relationship, ...]`
- Analyzers produce only immutable `tuple[Relationship, ...]`; they do
  not return `RelationshipCollection`
- Only explicit Device Registry fields are analysed; no inverse or
  derived relationships (e.g. Device → Entity, Area via Entity)
- Analyzers know neither a graph nor a repository
- Merging outputs from multiple analyzers is deferred to Module 6.8
- No YAML analysis, validation or business logic in this module

## Consequences

Advantages:

- Completes the explicit registry relationship surface for entities
  and devices
- Clear single responsibility; composable with Module 6.2 output
- Easy unit testing of pure relationship emission

Trade-offs:

- Callers must hold raw tuples until Module 6.8 provides aggregation
- Cross-analyzer de-duplication is deferred

---

# ADR-040

## Title

Automation Relationship Analyzer

## Status

Accepted

## Motivation

Module 6.4 must derive automation relationships that are already
explicit in automation YAML (entity, device, area, script, scene and
automation references). Analyzers must stay small, independent and
free of aggregation concerns so later analyzers (scripts, dashboards,
MQTT, …) can compose without shared state.

## Decision

- Introduce `AutomationRelationshipAnalyzer` with
  `analyze(automations) -> tuple[Relationship, ...]`
- Analyse exclusively explicit YAML references in `Automation.raw`
- Recursively traverse mappings and sequences via a private shared
  helper (`relationships._yaml_traversal`); no assumptions about
  Home Assistant YAML shape
- Emit only `AUTOMATION REFERENCES` edges using `ObjectType` and
  `RelationshipType` (no string literals for those fields)
- Script / scene / automation links require an explicit service call
  (`script.turn_on`, `scene.turn_on`, `automation.trigger` /
  `turn_on` / `turn_off`) plus a target `entity_id`
- Jinja (`{{ … }}`), templates, variables, choose-logic, triggers as
  a separate concern, MQTT, webhooks, blueprint-inputs and runtime
  validation are out of scope
- Deduplicate via an internal `set`; return a deterministically sorted
  immutable tuple
- Analyzers produce only `tuple[Relationship, ...]`; they do not
  return `RelationshipCollection`, build a graph or own a repository
- Automation analyzers werken op de volledige originele
  YAML-representatie (`Automation.raw`). Daarom bewaart
  `Automation.raw` de volledige mapping, consistent met Script en
  Scene

## Consequences

Advantages:

- Clear single responsibility for automation YAML references
- Reusable YAML traversal for Modules 6.5–6.7
- Easy unit testing of pure relationship emission
- No premature coupling to collection, graph or repository layers

Trade-offs:

- Callers must hold raw tuples until Module 6.8 provides aggregation
- Template-only references remain invisible until a later module
- Automations without `id` or `alias` emit no relationships

---

# ADR-041

## Title

Script Relationship Analyzer

## Status

Accepted

## Motivation

Module 6.5 must derive script relationships that are already
explicit in script YAML (entity, script and scene references).
The analyzer must stay aligned with Module 6.4: small, independent,
free of aggregation, and must not duplicate YAML traversal or
generic reference detection.

## Decision

- Introduce `ScriptRelationshipAnalyzer` with
  `analyze(scripts) -> tuple[Relationship, ...]`
- Analyse exclusively explicit YAML references in `Script.raw`
- Reuse the shared helper (`relationships._yaml_traversal`) for
  recursive mapping/sequence walks and generic extraction of
  `entity_id`, service/action names and `target` entity ids
- Emit only `SCRIPT REFERENCES` edges using `ObjectType` and
  `RelationshipType` (no string literals for those fields)
- Script / scene links require an explicit service call
  (`script.turn_on`, `scene.turn_on`) plus a target `entity_id`
- Device, area, MQTT, blueprint-inputs, variables, Jinja,
  templates, package links, Entity Registry lookups and runtime
  validation are out of scope
- Deduplicate via an internal `set`; return a deterministically
  sorted immutable tuple
- Analyzers produce only `tuple[Relationship, ...]`; they do not
  return `RelationshipCollection`, build a graph or own a
  repository
- YAML-doorloop and generieke detectie blijven centraal in
  `_yaml_traversal`; analyzers stellen alleen `Relationship`-
  objecten samen

## Consequences

Advantages:

- Clear single responsibility for script YAML references
- Consistent detection stack for Modules 6.4–6.7
- Easy unit testing of pure relationship emission
- No premature coupling to collection, graph or repository layers

Trade-offs:

- Callers must hold raw tuples until Module 6.8 provides aggregation
- Template-only references remain invisible until a later module
- Scripts without `id` or `alias` emit no relationships

---

# ADR-042

## Title

Dashboard Relationship Analyzer

## Status

Accepted

## Motivation

Module 6.6 must derive dashboard relationships that are already
explicit in dashboard YAML (entity and device references).
The analyzer must stay aligned with Modules 6.4–6.5: small,
independent, free of aggregation, and must not interpret Lovelace
card types or duplicate YAML traversal.

## Decision

- Introduce `DashboardRelationshipAnalyzer` with
  `analyze(dashboards) -> tuple[Relationship, ...]`
- Analyse exclusively explicit YAML references in `Dashboard.views`
  (as stored by `DashboardParser`)
- Reuse the shared helper (`relationships._yaml_traversal`) for
  recursive mapping/sequence walks and generic extraction of
  explicit identity values; extend it only with generically reusable
  key constants (`entity`, `entities`, `device`)
- Detect only explicit identity fields (`entity`, `entities`,
  `entity_id`, `device`, `device_id`) — never derive links from
  card-type names (`type: entities`, `button`, `tile`,
  `history-graph`, …)
- Emit only `DASHBOARD REFERENCES` edges using `ObjectType` and
  `RelationshipType` (no string literals for those fields)
- No Lovelace rendering, frontend logic, templates, Jinja,
  auto-entities, browser_mod, custom-card semantics, markdown,
  navigation, MQTT, graph, repository or runtime validation
- Deduplicate via an internal `set`; return a deterministically
  sorted immutable tuple
- Analyzers produce only `tuple[Relationship, ...]`; they do not
  return `RelationshipCollection`, build a graph or own a
  repository

## Consequences

Advantages:

- Clear single responsibility for dashboard YAML references
- Card-type independence suits hobby installs with custom cards
- Consistent detection stack for Modules 6.4–6.7
- Easy unit testing of pure relationship emission
- No premature coupling to collection, graph or repository layers

Trade-offs:

- Callers must hold raw tuples until Module 6.8 provides aggregation
- Template-only / JavaScript / auto-entities references remain
  invisible
- Root-level `button_card_templates` outside `views` are not scanned
- Dashboards without `id` or `title` emit no relationships

---

# ADR-043

## Title

MQTT Relationship Analyzer

## Status

Accepted

## Motivation

Module 6.7 must derive MQTT relationships that are already
explicit in YAML (publish topics via `mqtt.publish` and subscribe
topics in package `mqtt` sections). The analyzer must stay aligned
with Modules 6.2–6.6: small, independent, free of aggregation, and
must not introduce broker, runtime or graph concerns.

## Decision

- Introduce `MQTTRelationshipAnalyzer` with
  `analyze(automations, scripts, helpers, package_structures)
  -> tuple[Relationship, ...]`
- Accept explicit immutable collections only — not
  `YamlRepository` — so dependencies stay narrow and Module 6.8
  remains responsible for aggregation
- Analyse exclusively explicit MQTT topic string references
- Reuse the shared helper (`relationships._yaml_traversal`) for
  recursive mapping/sequence walks; add no new walker
- Detect publish via explicit `mqtt.publish` service/action plus
  literal `data.topic` or `topic` (no Jinja, no normalisation)
- Detect subscribe via explicit keys under package `mqtt` sections:
  `state_topic`, `command_topic`, `availability_topic`,
  `json_attributes_topic`, `topic`
- Emit `AUTOMATION` / `SCRIPT` / `HELPER` `PUBLISHES` `MQTT_TOPIC`
  and `ENTITY` / `PACKAGE` `SUBSCRIBES` `MQTT_TOPIC` using
  `ObjectType` and `RelationshipType` (no string literals for those
  fields); use the topic string literally as `target_id`
- Prefer `ENTITY` as subscribe source only when `entity_id` is
  already present; otherwise `PACKAGE` — never derive entities
- No broker analysis, wildcard resolution, topic normalisation,
  QoS/retain/payload/discovery, trigger matching, dependency graph,
  repository or runtime validation
- Deduplicate via an internal `set`; return a deterministically
  sorted immutable tuple
- Analyzers produce only `tuple[Relationship, ...]`; they do not
  return `RelationshipCollection`, build a graph or own a
  repository

## Consequences

Advantages:

- Clear single responsibility for explicit MQTT topic references
- Consistent analyzer signature style with Modules 6.2–6.6
- Easy unit testing without constructing a full repository
- No premature coupling to collection, graph or repository layers

Trade-offs:

- Callers must pass the relevant collections until Module 6.8
  provides aggregation
- `command_topic` is recorded as `SUBSCRIBES` when listed as an
  explicit topic field (no publish/subscribe semantic refinement)
- Template-only topics and runtime subscriptions remain invisible
- Automations/scripts without a stable id/alias emit no publishes

---

# ADR-044

## Title

Relationship Repository

## Status

Accepted

## Motivation

Modules 6.2–6.7 each emit independent `tuple[Relationship, ...]`.
Callers need a single immutable place to store and look up those
edges without introducing graph semantics, analyzer coupling or
validation. The repository must follow the same storage philosophy
as `HomeAssistantModel` and `YamlRepository`.

## Decision

- Introduce `RelationshipRepository` as a frozen dataclass with
  `slots=True` holding `relationships: tuple[Relationship, ...]`
- Constructor accepts only already-computed relationships — never
  analyzer types, `HomeAssistantModel` or `YamlRepository`
- Merging analyzer outputs happens outside the repository (wiring /
  orchestration layer); the repository remains analyzer-independent
- During construction: remove duplicate `Relationship` objects and
  sort deterministically by `source_type`, `source_id`,
  `relationship_type`, `target_type`, `target_id`
- Build read-only `MappingProxyType` indexes in `__post_init__` for
  O(1) identity lookups; no mutation after construction
- Public lookup API returns immutable tuples only:
  `by_source`, `by_target`, `by_relationship`, `between`
- No analysis, graph construction, dependency calculation,
  runtime validation or business logic

## Consequences

Advantages:

- Single reproducible store for all analysed relationships
- Clear separation: analyzers produce edges; repository only stores
- O(1) lookups without premature graph or validation layers
- Easy to unit-test with hand-built relationship tuples

Trade-offs:

- Callers must concatenate analyzer outputs before construction
- Duplicate removal is identity-based only (no semantic merging)
- Graph views and dependency analysis remain deferred to Module 6.9

---

# ADR-045

## Title

Dependency Graph

## Status

Accepted

## Motivation

Module 6.8 centralises relationships in `RelationshipRepository`.
Callers need a pure structural graph view of that store — nodes and
edges only — without visualisation, traversal algorithms, dependency
scoring or Home Assistant domain coupling. Entity Graph and Package
Graph must not become separate graph implementations.

## Decision

- Introduce `ha_docgen.graph` with immutable `GraphNode`, `GraphEdge`
  and `DependencyGraph` (`frozen=True`, `slots=True`)
- `DependencyGraph` is exclusively a representation of an existing
  `RelationshipRepository`: nodes are `(ObjectType, object_id)`,
  edges carry `RelationshipType`
- `DependencyGraphBuilder` is fully stateless; `build(repository)`
  maps each `Relationship` to nodes/edge, deduplicates, and sorts
  deterministically
- Build read-only `MappingProxyType` indexes in `__post_init__` for
  `outgoing` / `incoming`; optional `contains` via node index
- No Graphviz, Mermaid, NetworkX, JSON/HTML/Markdown export,
  DFS/BFS/shortest-path/cycle detection, dependency scoring or
  business logic
- Entity Graph / Package Graph are not separate models; derive them
  later by filtering the single `DependencyGraph` on `ObjectType`

## Consequences

Advantages:

- One compact graph type for all relationship views
- Clear layering: analyzers → repository → graph representation
- Immutable, reproducible, easy to unit-test with hand-built repos
- Future filtered views without duplicating graph infrastructure

Trade-offs:

- Graph construction is orchestration outside this module (callers
  must supply a populated `RelationshipRepository`)
- No built-in visualisation or analysis — deferred to later modules
  that consume `DependencyGraph` read-only

---

# ADR-046

## Title

Output-Independent Documentation Models

## Status

Accepted

## Motivation

Module 7 must generate documentation in multiple formats (Markdown,
HTML, JSON). If document structure were modelled per format
(`MarkdownParagraph`, `HtmlTable`, …), generators would duplicate
content trees and writers could not share one intermediate
representation. Module 7.1 therefore defines format-neutral
document objects first; serialisation belongs in later modules
(starting with Markdown in Module 7.2).

## Decision

- Introduce package `ha_docgen.document` with immutable dataclasses
  (`frozen=True`, `slots=True`)
- `Document` holds `title` and `sections: tuple[Section, ...]`
- `Section` holds `heading` and `content: tuple[DocumentItem, ...]`
- `DocumentItem` is a polymorphic base; concrete kinds are
  `Paragraph`, `Table`, `CodeBlock` and `BulletList`
- Collections use `tuple` only; mappings would use
  `MappingProxyType` when needed (none required in 7.1)
- No Markdown, HTML, JSON, builders, exporters, repositories,
  rendering, validation or business logic

## Consequences

Advantages:

- One shared document tree for all output formats
- Clear layering: domain data → document models → format writers
- Immutable, easy to unit-test without I/O or rendering
- Same model philosophy as Modules 5–6

Trade-offs:

- Callers must construct document trees explicitly until generators
  land in later Module 7 steps
- Format-specific features (e.g. Markdown front matter) stay outside
  these models

---

# ADR-047

## Title

Document → MarkdownBuilder → str

## Status

Accepted

## Motivation

Module 7.1 defines format-neutral document models. Markdown is the
primary output format (ADR-006), but rendering must not leak into the
models and must not pull in Home Assistant domain knowledge. Mixing
generators, filesystem writers or HA types into the builder would
couple serialisation to content creation and make HTML/JSON writers
harder later.

## Decision

- Introduce a stateless `MarkdownBuilder` with a single public method
  `build(document: Document) -> str`
- The builder knows only `ha_docgen.document` models
  (`Document`, `Section`, `Paragraph`, `Table`, `CodeBlock`,
  `BulletList`)
- Private helpers own each item kind; no renderer interface, no
  abstract builders, no configuration object
- No YAML, registries, relationships, graph, generators,
  filesystem writes, HTML/JSON, links, images, TOC, front matter or
  Markdown extensions
- Document content assembly (PackageDocumentation, …) remains later
  Module 7 steps; this module only renders an existing tree

## Consequences

Advantages:

- Clear pipeline: domain data → Document → Markdown string → writer
- Format-neutral models stay free of Markdown syntax
- Deterministic, easy to unit-test without I/O or HA fixtures
- HTML/JSON builders can mirror the same Document input later

Trade-offs:

- Callers must supply a fully built `Document` before rendering
- Markdown-only features (front matter, admonitions) stay out of
  scope until explicitly added

---

# ADR-048

## Title

Generators Produce Document Models Only

## Status

Accepted

## Motivation

Module 7.1–7.2 established format-neutral document models and a
Markdown renderer. Package documentation (and later entity, dashboard
and repository docs) must assemble content without baking Markdown,
HTML, JSON or filesystem writes into the generator. Mixing rendering
or I/O into generators would duplicate format logic, couple content
assembly to one serialisation path, and break the Scanner → Generator
→ Writer layering already used elsewhere in HA-DocGen.

## Decision

- Introduce `PackageDocumentGenerator` with
  `generate(...) -> Document` for exactly one `Package`
- Generators accept already-parsed domain objects (Package,
  PackageStructure, and filtered collections) — never
  `YamlRepository`, `HomeAssistantModel` or filesystem paths
- Generators ontvangen momenteel expliciete domeincollecties. Een
  eventuele aggregatie (bijvoorbeeld een `DocumentationContext`)
  wordt pas overwogen wanneer meerdere generators aantoonbaar
  dezelfde parameterstructuur delen
- Output is exclusively an immutable `Document` tree
  (Paragraph / BulletList sections); no Markdown strings, no file
  writes, no exporters
- Rendering remains the sole responsibility of format builders
  (`MarkdownBuilder` today; HTML/JSON later)
- No package index, multi-package batching, relationships, graph,
  entity analysis, links, tables or statistics in this module

## Consequences

Advantages:

- Clear pipeline: domain data → Document → format string → writer
- One generator serves every output format without duplication
- Easy unit-testing of content structure without I/O or Markdown
- Matches Modules 5–6: pure transformation, no side effects

Trade-offs:

- Callers must invoke a builder (and later a writer) separately
- Multi-package indexes and richer package docs remain later modules

---

# ADR-049

## Title

Entity Generators Produce Document Models Without Repository or Graph Knowledge

## Status

Accepted

## Motivation

Module 7.3 established that documentation generators return immutable
`Document` trees and accept already-parsed domain objects. Entity
documentation must follow the same boundary: it must not reach into
`HomeAssistantModel`, `RelationshipRepository` or `DependencyGraph` to
discover related objects. Embedding repository or graph knowledge in a
generator would couple content assembly to analysis infrastructure,
hide data dependencies, and make unit tests require full scan fixtures.

## Decision

- Introduce `EntityDocumentGenerator` with
  `generate(entity, relationships) -> Document` for exactly one
  `Entity`
- Callers supply the `Entity` and an explicit
  `tuple[Relationship, ...]` — the generator never looks up, filters by
  meaning, sorts or traverses relationships
- Output is exclusively an immutable `Document` tree (Overview /
  Registry / Relationships); no Markdown strings, no filesystem writes,
  no exporters
- Generators remain free of repository, graph, YAML and aggregate HA
  model imports beyond the single `Entity` and `Relationship` types
- Rendering stays the responsibility of format builders
  (`MarkdownBuilder` today; HTML/JSON later)

## Consequences

Advantages:

- Same pipeline as package docs: domain data → Document → format → writer
- Explicit inputs make dependencies visible at the call site
- Easy unit-testing with hand-built Entity / Relationship fixtures
- Repositories and graphs stay owned by Modules 4–6; generators stay
  pure transformers

Trade-offs:

- Callers must resolve the Relationship tuple before generation
- Entity indexes and multi-entity batching remain later modules

---

# ADR-050

## Title

Automation Documentation Builds Document Objects Only

## Status

Accepted

## Motivation

Module 7.4 established that documentation generators return immutable
`Document` trees from already-parsed domain objects and an explicit
`Relationship` tuple. Automation documentation must follow the same
boundary: it must not reach into `HomeAssistantModel`,
`YamlRepository`, `RelationshipRepository` or `DependencyGraph`, and it
must not emit Markdown or write files. Embedding repository, graph or
rendering knowledge in a generator would couple content assembly to
analysis and output infrastructure, hide data dependencies, and make
unit tests require full scan fixtures.

## Decision

- Introduce `AutomationDocumentGenerator` with
  `generate(automation, relationships) -> Document` for exactly one
  `Automation`
- Callers supply the `Automation` and an explicit
  `tuple[Relationship, ...]` — the generator never looks up, filters,
  sorts or traverses relationships
- Overview uses only present first-class Automation fields; Triggers,
  Conditions and Actions read only explicit type/service strings from
  `Automation.raw` with no YAML re-parsing, Jinja evaluation or
  semantic analysis
- Output is exclusively an immutable `Document` tree; no Markdown
  strings, no filesystem writes, no exporters
- Generators remain free of repository, graph and aggregate HA model
  imports beyond the single `Automation` and `Relationship` types
- Rendering stays the responsibility of format builders
  (`MarkdownBuilder` today; HTML/JSON later)

## Consequences

Advantages:

- Same pipeline as package/entity docs: domain data → Document → format
  → writer
- Explicit inputs make dependencies visible at the call site
- Easy unit-testing with hand-built Automation / Relationship fixtures
- Repositories and graphs stay owned by Modules 4–6; generators stay
  pure transformers

Trade-offs:

- Callers must resolve the Relationship tuple before generation
- Automation indexes and multi-automation batching remain later modules

---

# ADR-051

## Title

Dashboard Documentation Builds Document Objects Only

## Status

Accepted

## Motivation

Module 7.5 established that documentation generators return immutable
`Document` trees from already-parsed domain objects and an explicit
`Relationship` tuple. Dashboard documentation must follow the same
boundary: it must not reach into `HomeAssistantModel`,
`YamlRepository`, `RelationshipRepository` or `DependencyGraph`, and it
must not emit Markdown or write files. Embedding repository, graph,
card analysis or rendering knowledge in a generator would couple
content assembly to analysis and output infrastructure, hide data
dependencies, and make unit tests require full scan fixtures.

## Decision

- Introduce `DashboardDocumentGenerator` with
  `generate(dashboard, relationships) -> Document` for exactly one
  `Dashboard`
- Callers supply the `Dashboard` and an explicit
  `tuple[Relationship, ...]` — the generator never looks up, filters,
  sorts or traverses relationships
- Overview uses only present first-class Dashboard fields; Views list
  only available view metadata from `Dashboard.views` with no card
  traversal, entity counting or type interpretation
- Output is exclusively an immutable `Document` tree; no Markdown
  strings, no filesystem writes, no exporters
- Generators remain free of repository, graph and aggregate HA model
  imports beyond the single `Dashboard` and `Relationship` types
- Rendering stays the responsibility of format builders
  (`MarkdownBuilder` today; HTML/JSON later)

## Consequences

Advantages:

- Same pipeline as package/entity/automation docs: domain data →
  Document → format → writer
- Explicit inputs make dependencies visible at the call site
- Easy unit-testing with hand-built Dashboard / Relationship fixtures
- Repositories and graphs stay owned by Modules 4–6; generators stay
  pure transformers

Trade-offs:

- Callers must resolve the Relationship tuple before generation
- Dashboard indexes and multi-dashboard batching remain later modules

---

# ADR-052

## Title

Configuration Documentation Aggregates Existing Models Only

## Status

Accepted

## Motivation

Modules 7.3–7.6 generate a `Document` for a single domain object plus
an explicit relationship tuple. Configuration-wide documentation must
still stay inside the Document pipeline: it must aggregate counts from
already-built immutable models and must not parse YAML, scan the
filesystem, analyse dependencies, build graphs or emit Markdown.
Embedding analysis or rendering in a configuration generator would
couple overview content to Modules 4–6 internals and to output format
details, hiding data dependencies and forcing full scan fixtures for
unit tests.

## Decision

- Introduce `ConfigurationDocumentGenerator` with
  `generate(model, yaml_repository, relationship_repository) -> Document`
- Aggregation uses only collection lengths on `HomeAssistantModel` and
  `YamlRepository`, and `RelationshipRepository.by_relationship` /
  `relationships` for type counts and totals
- No parsing, scanning, analysis, graph construction, repository
  mutation or lookups outside the three supplied aggregates
- Output is exclusively an immutable `Document` tree; no Markdown
  strings, no filesystem writes, no exporters
- Rendering remains the responsibility of format builders
  (`MarkdownBuilder` today; HTML/JSON later)

## Consequences

Advantages:

- Same pipeline as object-level docs: aggregates → Document → format →
  writer
- Explicit inputs keep Module 4–6 ownership of scanning and analysis
- Easy unit-testing with empty or hand-built aggregates
- Configuration overview stays a pure transformer

Trade-offs:

- Callers must assemble `HomeAssistantModel`, `YamlRepository` and
  `RelationshipRepository` before generation
- Registry rows reflect only collections present on
  `HomeAssistantModel` (no invented user/auth counts)

---

# ADR-053

## Title

Documentation Repository

## Status

Accepted

## Motivation

Modules 7.3–7.7 each produce independent `Document` trees. Callers need
a single immutable place to store and look up those documents without
introducing generation, rendering, filesystem writes or analysis. The
repository must follow the same storage philosophy as `YamlRepository`
and `RelationshipRepository`.

## Decision

- Introduce `DocumentRepository` as a frozen dataclass with
  `slots=True` holding `documents: tuple[Document, ...]`
- Constructor accepts only already-generated documents — never
  generators, builders, `HomeAssistantModel`, `YamlRepository` or
  `RelationshipRepository`
- Assembling generator outputs happens outside the repository
  (wiring / orchestration layer); the repository remains
  generator-independent
- During construction: remove duplicate `Document` objects and sort
  deterministically by `Document.title`
- Build a read-only `MappingProxyType` `_by_title` index in
  `__post_init__` for O(1) title lookups; no mutation after
  construction
- Public lookup API: `document(title) -> Document | None`,
  `documents_by_title(title) -> tuple[Document, ...]`; the public
  field `documents` exposes the immutable collection
- No partial/fuzzy matching, filtering, search, generation, rendering,
  Markdown/HTML/JSON, exporters, writers, filesystem, graph or
  business logic

## Consequences

Advantages:

- Single reproducible store for all generated documents
- Clear separation: generators produce documents; repository only
  stores
- O(1) title lookups without premature export or index-generation
  layers
- Easy to unit-test with hand-built document tuples

Trade-offs:

- Callers must concatenate generator outputs before construction
- Duplicate removal is identity-based only (no semantic merging)
- Markdown export and filesystem writers remain deferred to Module 7.9

---

# ADR-054

## Title

Markdown Export Writes Repository Documents Only

## Status

Accepted

## Motivation

Modules 7.2–7.8 produce and store immutable `Document` trees. Callers
need a single filesystem writer that turns a `DocumentRepository` into
Markdown files without reintroducing generation, analysis, graph
traversal or format-specific render logic outside `MarkdownBuilder`.
Embedding those concerns in an exporter would break the pipeline
Document → repository → builder → filesystem and couple I/O to content
assembly.

## Decision

- Introduce a stateless `MarkdownExporter` with
  `export(repository, output_directory) -> None`
- Accept only an already-built `DocumentRepository` and a
  `pathlib.Path` output directory — never generators,
  `HomeAssistantModel`, `YamlRepository`, `RelationshipRepository` or
  `DependencyGraph`
- Render each `Document` exclusively through the existing
  `MarkdownBuilder`; write exactly one `.md` file per document
- Derive filenames via a private deterministic helper from
  `Document.title` (lowercase; spaces → `-`; remove `:`; `/` → `-`;
  collapse repeated `-`)
- Create `output_directory` when needed using `pathlib` only
  (no `shutil`)
- Write a single `index.md` with heading `# Documentation` and a
  bullet list of `[Document.title](filename.md)` links sourced only
  from repository documents
- No HTML, JSON, PDF, Graphviz, Mermaid, filesystem scans, repository
  mutation, validation, analysis or duplicated Markdown render code

## Consequences

Advantages:

- Clear pipeline end: Document → DocumentRepository → MarkdownBuilder
  → MarkdownExporter → filesystem
- Export stays free of generation and domain analysis
- Deterministic filenames and index make output reproducible
- Easy to unit-test with a hand-built repository and temporary path

Trade-offs:

- Callers must assemble and populate `DocumentRepository` before export
- Filename collisions from distinct titles that sanitize identically
  are not resolved in this module
- Wiring into the CLI / orchestration layer remains a later concern

---

# ADR-055

## Title

Validation Models

## Status

Accepted

## Motivation

Module 8 validation needs a shared, immutable representation of
findings against Home Assistant objects (entities, automations,
dashboards, packages, …). Later modules (8.2–8.8) will produce and
store those findings; Module 8.1 must define only the validation
building blocks — without validators, analysis, repositories, reports,
Markdown or filesystem coupling.

## Decision

- Introduce package `ha_docgen.validation` with `ValidationResult` and
  `ValidationCollection`
- `ValidationResult` is a frozen dataclass of identity fields only:
  `object_type`, `object_id`, `validation_type`, `severity`, `message`
- `object_type` reuses `ObjectType` from `relationships.models`
  (no separate validation object enum)
- `validation_type` uses `ValidationType` (`StrEnum`) with generic
  members only (`MISSING_REFERENCE`, `DUPLICATE`,
  `INVALID_CONFIGURATION`, `UNSUPPORTED`, `CUSTOM`);
  `severity` uses `ValidationSeverity` (`StrEnum`: `INFO`, `WARNING`,
  `ERROR`); `object_id` / `message` remain plain `str`
- No inheritance beyond dataclass, no methods on `ValidationResult`,
  no Home Assistant domain models, no validator logic
- `ValidationCollection` holds `tuple[ValidationResult, ...]`,
  deduplicates and sorts deterministically in `__post_init__`, and
  builds read-only `MappingProxyType` indexes
- Public lookups: `by_object(type, id)`, `by_severity(severity)` and
  `by_type(validation_type)` for O(1) access; no filtering or analysis
  API
- Foundation for Modules 8.2–8.8; validators, repository and reports
  remain deferred

## Consequences

Advantages:

- Generic validation primitives reusable across all HA object kinds
- Type-safe severity and finding kinds via `StrEnum`
- Shared object identity vocabulary with Module 6 (`ObjectType`)
- Immutable, indexable collection without premature engine semantics
- Clear boundary: models only; validation logic stays later

Trade-offs:

- New finding kinds require a `ValidationType` enum extension
- Callers must assemble `ValidationResult` instances until validators
  land in later Module 8 steps

---

# ADR-056

## Title

Entity Validation

## Status

Accepted

## Motivation

Module 8.1 defined immutable validation result models. Module 8.2 must
introduce the first concrete validator — entity integrity checks —
without a validation engine, repository, reports, Markdown, filesystem
or graph traversal. The validator must follow the same stateless
transform pattern as Module 6 analyzers and Module 7 generators:
accept already-loaded inputs and emit immutable output tuples.

## Decision

- Introduce `EntityValidator` in `ha_docgen.validation`
- Fully stateless: no constructor state, no caching, no side effects
- Public API: `validate(entities, relationship_repository) ->
  tuple[ValidationResult, ...]`
- Accepts only `tuple[Entity, ...]` and `RelationshipRepository`
- Implements four explicit checks only:
  1. No relationships for the entity → `MISSING_REFERENCE` / WARNING /
     `"No relationships found."`
  2. Relationship with empty `target_id` → `INVALID_CONFIGURATION` /
     ERROR / `"Relationship has empty target."`
  3. Empty `entity_id` → `INVALID_CONFIGURATION` / ERROR /
     `"Entity ID is empty."`
  4. Duplicate `entity_id` within the input tuple → `DUPLICATE` /
     ERROR / `"Duplicate entity ID."`
- Relationships are read via
  `relationship_repository.by_source(ObjectType.ENTITY, entity_id)`
- Results are deduplicated and sorted with the same deterministic key
  style as `ValidationCollection` (`object_type`, `object_id`,
  `validation_type`, `severity`, `message`)
- No validation engine, repository, reports, Markdown, filesystem,
  HomeAssistantModel, YamlRepository, DocumentRepository,
  DependencyGraph or domain validators beyond entities

## Consequences

Advantages:

- Same architecture as analyzers and generators (stateless transform)
- Explicit, reviewable rules with no heuristics
- Reuses Module 8.1 models and Module 6 relationship lookups
- Clear foundation for later object-specific validators (8.3–8.6)

Trade-offs:

- Callers must supply entities and a relationship repository
- Cross-object and report aggregation remain deferred to later modules

---

# ADR-057

## Title

Automation Validation

## Status

Accepted

## Motivation

Module 8.2 introduced the first concrete validator for entities.
Module 8.3 must add the same pattern for automations — explicit
integrity checks only — without a validation engine, repository,
reports, Markdown, filesystem or graph traversal. The validator must
follow the same stateless transform pattern as Module 6 analyzers,
Module 7 generators and `EntityValidator`: accept already-loaded
inputs and emit immutable output tuples.

## Decision

- Introduce `AutomationValidator` in `ha_docgen.validation`
- Fully stateless: no constructor state, no caching, no side effects
- Public API: `validate(automations, relationship_repository) ->
  tuple[ValidationResult, ...]`
- Accepts only `tuple[Automation, ...]` and `RelationshipRepository`
- Implements four explicit checks only:
  1. Empty automation `id` → `INVALID_CONFIGURATION` / ERROR /
     `"Automation ID is empty."`
  2. Empty automation `alias` → `INVALID_CONFIGURATION` / WARNING /
     `"Automation has no alias."`
  3. Relationship with empty `target_id` → `INVALID_CONFIGURATION` /
     ERROR / `"Relationship has empty target."`
  4. Duplicate automation `id` within the input tuple → `DUPLICATE` /
     ERROR / `"Duplicate automation ID."`
- Relationships are read via
  `relationship_repository.by_source(ObjectType.AUTOMATION, id)`
- Results are deduplicated and sorted with the same deterministic key
  style as `EntityValidator` / `ValidationCollection`
  (`object_type`, `object_id`, `validation_type`, `severity`,
  `message`)
- No validation engine, repository, reports, Markdown, filesystem,
  HomeAssistantModel, YamlRepository, DocumentRepository,
  DependencyGraph or domain validators beyond automations
- Validation reports only objectively verifiable configuration faults.
  An automation without incoming relationships is valid: triggers
  start automations independently, so absence of inbound references
  is not a configuration error.
- Quality findings such as unused entities, unused automations,
  orphan dashboards, dead scripts and unused helpers are explicitly
  out of scope for Module 8 (including 8.4–8.6). They belong in a
  future Analysis/Quality module if implemented at all.
- Future object validators (8.4–8.6) must not introduce
  `UNREFERENCED_OBJECT` rules for objects that may legitimately exist
  without incoming relationships.

## Consequences

Advantages:

- Same architecture as `EntityValidator`, analyzers and generators
- Explicit, reviewable rules with no heuristics
- Reuses Module 8.1 models and Module 6 relationship lookups
- Clear foundation for later object-specific validators (8.4–8.6)
- Separates configuration validation from quality/analysis concerns

Trade-offs:

- Callers must supply automations and a relationship repository
- Cross-object and report aggregation remain deferred to later modules
- Unused-/orphan-style findings are deferred outside Module 8

---

# ADR-058

## Title

Report Domain Models

## Status

Accepted

## Motivation

Module 9 reporting must support multiple report kinds (health,
configuration, architecture, inventory, dependency, performance,
documentation index). If each report invented its own structure, or
if models embedded Markdown/JSON/console formatting, later modules
would duplicate trees and couple content to one output path.
Module 9.1 therefore defines format-neutral report objects first —
distinct from Module 8 `ValidationReport`, which aggregates validation
findings only.

## Decision

- Introduce package `ha_docgen.reporting` with immutable dataclasses
  (`frozen=True`, `slots=True`)
- `Report` holds `title`, `description`, `metadata`,
  `sections: tuple[ReportSection, ...]`,
  `statistics: Mapping[str, int | float]`,
  `recommendations: tuple[str, ...]` and `summary`
- `ReportSection` holds `title`, optional `description`, `severity` and
  `items: tuple[str, ...]`
- `ReportMetadata` holds `generated_at`, `version`, `project_path` and
  `execution_time`
- `Severity` is a dedicated `StrEnum` (`INFO`, `WARNING`, `ERROR`);
  it does not reuse `ValidationSeverity` so reporting stays independent
  of validation
- Collections use `tuple` only; statistics are frozen via
  `MappingProxyType` with deterministically sorted keys
- No Markdown, HTML, JSON, console formatting, renderers, generators,
  exporters, CLI, filesystem writes or Home Assistant domain logic

## Consequences

Advantages:

- One shared report tree for every future report type
- Clear layering: analysis/validation → Report models → format writers
- Immutable, easy to unit-test without I/O or rendering
- Same model philosophy as Modules 7–8 (`Document`, validation models)

Trade-offs:

- Callers must construct report trees until generators land in later
  Module 9 steps
- Section `items` are plain strings until a later module promotes richer
  item types intentionally
- Mapping `ValidationSeverity` → `Severity` remains a later concern

---

# ADR-059

## Title

Health Report Generator Aggregates Validation into Report Models

## Status

Accepted

## Motivation

Module 9.1 defined format-neutral `Report` models. Module 9.2 must prove
those models are usable by implementing one concrete report — Health —
without introducing a report registry, builder framework, renderers or
CLI. Mixing Markdown/JSON/console formatting into the generator would
couple content assembly to output and break the same pipeline used for
Module 7 documents (domain data → model → later writers).

## Decision

- Introduce `HealthReportGenerator` in `ha_docgen.reporting` with
  `generate(repository, metadata) -> Report`
- Fully stateless: no constructor state, no caching, no side effects
- Accept only an already-built `ValidationRepository` and
  `ReportMetadata` — never filesystem paths, validators, Markdown or
  CLI concerns
- Reuse Module 8.8 `ValidationReport` internally for severity, type and
  object-type totals; map findings into `Report` / `ReportSection`
- Populate `summary`, `statistics`, `sections` (Validation Summary,
  Errors, Warnings, Informational) and `recommendations`
- Recommendations are deterministic strings derived only from existing
  validation totals (severity and `ValidationType` counts) — no AI or
  invented advice
- No report registry, builder interface, renderer framework, factory
  hierarchy, Markdown, JSON, console output, filesystem writes or CLI

## Consequences

Advantages:

- Proves Report domain models suffice for a complete concrete report
- Clear pipeline: ValidationRepository → Report → later renderers
- Easy unit-testing without I/O or formatting
- No premature generic reporting infrastructure

Trade-offs:

- Callers must supply `ValidationRepository` and `ReportMetadata`
- Other report types (configuration, architecture, …) remain later
  modules and stay explicit until duplication justifies shared helpers

---

# ADR-060

## Title

Standard Python Packaging via pyproject.toml

## Status

Accepted

## Motivation

HA-DocGen is a standalone application that currently runs from the Home
Assistant repository. Distribution as a standard Python package must not
redesign the layered architecture or change runtime behaviour. Build
metadata was split across `pyproject.toml` and requirements files, the
declared package version lagged `version.py`, and package discovery could
include tests.

## Decision

- `pyproject.toml` is the single authoritative build configuration
- Use the existing setuptools backend; do not add a custom build script
- Keep the import path `tools.ha_docgen` so installed and in-repo usage match
- Read the distribution version dynamically from
  `tools.ha_docgen.version.VERSION`
- Declare runtime and development dependencies in `[project]` /
  `[project.optional-dependencies]`; requirements files only install those
- Discover `tools` and `tools.ha_docgen*` packages; exclude
  `tools.ha_docgen.tests`, nested test packages and `tools.ha_tools`
- Keep `tools/__init__.py` and `tools/generate_docs.py` as the existing
  `tools` package surface; they are not a second application architecture
- Do not ship tests, documentation (except the packaging README), caches
  or `tools/config.yaml`
- Preserve the existing `ha-docgen` console script
- Leave GitHub Releases, PyPI publishing, tagging and version automation
  to later Module 12 phases

## Consequences

Advantages:

- Standard `python -m build` produces sdist and wheel
- One metadata source for installers and CI
- Installed CLI uses the same package layout as local development
- Tests and development artifacts stay out of distributions

Trade-offs:

- The import path remains nested under `tools` rather than a top-level
  `ha_docgen` package
- Source distributions omit tests, so consumers cannot run the suite from
  the sdist alone

## Clarification (repository layout)

Historical context only: when this ADR was accepted, HA-DocGen lived
under `tools/` inside a Home Assistant configuration repository, and the
import path was `tools.ha_docgen`. The packaging principles above remain
in force. The standalone repository layout and top-level `ha_docgen`
import path are recorded in ADR-071.

---

# ADR-061

## Title

Authoritative Application Version Independent of Git

## Status

Accepted

## Motivation

Module 12.2 made `pyproject.toml` read the distribution version from
`tools.ha_docgen.version.VERSION`. Public surfaces (CLI, package
`__init__`, runtime diagnostics, wheel/sdist metadata) still needed one
runtime contract so source checkouts, editable installs and installed
wheels report the same value without consulting Git.

Git-based discovery would make builds non-reproducible in environments
without a repository. Duplicating the version in `pyproject.toml` or
reading `importlib.metadata` at runtime would create a second source
that can drift.

## Decision

- `tools.ha_docgen.version.VERSION` is the only authoritative application
  version
- Runtime code always reads that constant via `get_version()`
- `pyproject.toml` continues to stamp distribution metadata from the same
  attribute at build time
- Version strings must be valid SemVer 2.0 (`MAJOR.MINOR.PATCH` with
  optional prerelease and build metadata)
- Invalid `VERSION` values fail at import
- Version discovery must not use Git, tags, GitHub, or environment
  repository state
- Release tagging, changelog generation and publishing remain later
  Module 12 phases

## Consequences

Advantages:

- One location to update for every public version surface
- Identical version from source, editable install and wheel
- Reproducible builds without Git
- Invalid versions are rejected before packaging or CLI use

Trade-offs:

- Changing the version still requires a source edit (no automatic bump)
- Distribution metadata is a build-time copy; it is consistent only when
  artifacts are built from this module

## Clarification (repository layout)

Historical context only: paths such as `tools.ha_docgen.version.VERSION`
describe the layout at acceptance time. The single-source version rule
remains in force. The current path is `ha_docgen.version.VERSION` under
the standalone repository documented in ADR-071.

---

# ADR-062

## Title

Release Automation Lives in GitHub Actions

## Status

Accepted

## Motivation

Module 12.4 must create GitHub Releases from version tags without changing
runtime behaviour or introducing Git into the application (ADR-061). Putting
tag checks, artifact upload or release creation inside Scanner, CLI or
`version.py` would mix distribution infrastructure with documentation
generation and make local runs depend on GitHub.

CI already owns Ruff, pytest and `python -m build`. Duplicating those gates
in a second workflow would let the two pipelines drift.

## Decision

- Add `.github/workflows/release.yml`, triggered only by version tags
  (`v*.*.*`)
- Reuse CI as a called workflow (`workflow_call`) so release quality gates
  stay identical to push and pull-request CI
- Keep version validation and GitHub Release creation outside
  `tools.ha_docgen` runtime packages (`.github/scripts/validate_release_version.py`)
- Require the Git tag, `VERSION`, installed package metadata, wheel metadata
  and sdist metadata to match before a release is created
- Upload wheel and sdist as workflow artifacts and as GitHub Release assets
- Do not bump versions, generate changelogs, sign packages or publish to PyPI

## Consequences

Advantages:

- No runtime Git or GitHub dependency
- Quality gates cannot diverge from CI
- A version mismatch fails the workflow before a Release exists
- Layered application architecture is unchanged

Trade-offs:

- CI YAML gains a `workflow_call` trigger so release can reuse it
- GitHub must execute the workflow; local validation is static plus unit tests
- Tagging remains a manual step that must match `version.py`

## Clarification (repository layout)

Historical context only: the phrase `tools.ha_docgen` runtime packages
describes the layout at acceptance time. Release automation remaining
outside the application package is unchanged. The current package name
is `ha_docgen` under the standalone repository documented in ADR-071.

---

# ADR-063

## Title

AI Context Projects HomeAssistantModel by Reference

## Status

Accepted

## Motivation

Module 13.1 must turn the existing analysis model into an immutable
`AIContext` without parsing, relationship discovery, validation,
prompt building or export. `HomeAssistantModel` (ADR-021) already
holds the registry objects. Reading `YamlRepository`,
`RelationshipRepository`, the filesystem or `get_version()` would
pull data that the model does not contain.

## Decision

- Introduce package `ha_docgen.context` with `AIContext`,
  `ContextMetadata`, `ContextSection` and `ContextSectionKind`
- Models are frozen dataclasses (`slots=True`); collections are tuples
- `ContextGenerator.generate` accepts only a `HomeAssistantModel`
- Each non-empty top-level collection becomes one section whose items
  are the original objects, ordered by their existing identifier
- `ContextMetadata` fields stay `None` unless that value is already on
  the model; the current model has no repository name, project path,
  version or generation timestamp
- No filesystem access, parsers, validators, YAML, JSON, relationship
  discovery, prompt builder, AI export or CLI wiring
- Entity, automation, dashboard, ESPHome and package context documents
  remain later modules

## Consequences

Advantages:

- The generator is a pure, idempotent projection of one model
- Domain data is not copied into a second representation
- Future modules can add sections without changing `AIContext`
- Deterministic and unit-testable without I/O

Trade-offs:

- Packages, automations, scripts, scenes, dashboards, templates,
  helpers, ESPHome and the relationship graph are absent from
  `HomeAssistantModel`, so Module 13.1 does not project them
- Callers cannot attach a generation timestamp without that value
  existing on the model

---

# ADR-064

## Title

AnalysisModel Aggregate

## Status

Accepted

## Context

Module 13.1 projects one immutable `AIContext` from registry objects.
`ContextGenerator.generate` accepts a single `HomeAssistantModel`
(ADR-063). That model is the registry aggregate only (ADR-021).
YAML domain objects live in `YamlRepository` (ADR-035). Analysed
relationships live in `RelationshipRepository` (ADR-044).
Configuration documentation already receives those three aggregates
as separate arguments (ADR-052).

Module 13.2 and later AI Context modules need registry, YAML and
relationship facts together. This record adds the aggregate those
modules will consume. It does not implement Entity Context,
Automation Context, dashboard context, ESPHome context, package
context, prompt building or AI export.

## Problem Statement

`HomeAssistantModel` does not contain automations, packages or the
relationship graph. Projecting Entity Context and Automation Context
from that model alone would require one of the following:

- moving YAML or relationships into `HomeAssistantModel`
- giving `ContextGenerator` extra repository parameters
- letting `ContextGenerator` load repositories, parse YAML or discover
  relationships

Each option conflicts with an accepted ADR or with the rule that the
generator is a pure transformation of one already-built input.

## Decision

- Introduce `AnalysisModel` in `ha_docgen.analysis`
- `AnalysisModel` is a frozen dataclass (`slots=True`) with three
  fields, stored by reference and created with empty aggregates when
  omitted:
  - `home_assistant_model: HomeAssistantModel`
  - `yaml_repository: YamlRepository`
  - `relationship_repository: RelationshipRepository`
- The aggregate does not copy, merge, index or interpret those
  objects. It has no lookups and no business logic
- `HomeAssistantModel` remains the registry aggregate (ADR-021)
- `YamlRepository` remains the YAML aggregate (ADR-035)
- `RelationshipRepository` remains the relationship aggregate
  (ADR-044)
- No existing aggregate changes responsibility
- `DependencyGraph` stays separate. ADR-052 document generators keep
  their existing parameters
- `ContextGenerator.generate` accepts only an `AnalysisModel`
- The generator stays stateless and side-effect free. It does not
  touch the filesystem, parse YAML, load registries, discover
  relationships or validate configuration
- ADR-063 remains the authority for what is projected. The generator
  still emits one section per non-empty registry collection, keeps
  the original registry objects, and leaves `ContextMetadata` empty
- YAML objects and relationships are not projected yet. Entity
  Context and Automation Context are not part of this decision
- Callers build `AnalysisModel` from aggregates they already have.
  There is no compatibility overload that still accepts
  `HomeAssistantModel`

## Consequences

Advantages:

- Higher layers depend on one analysis result instead of a growing
  parameter list
- Registry, YAML and relationship modules keep their current
  responsibilities
- Domain objects stay single instances; the new aggregate only holds
  references
- `AIContext` and the Module 13.1 projection stay unchanged
- The generator remains a pure, deterministic function of its input

Trade-offs:

- `ContextGenerator.generate` no longer accepts `HomeAssistantModel`.
  The only in-repository callers are unit tests. Production wiring
  does not call the generator yet
- Callers must assemble `AnalysisModel` before generation
- `AnalysisModel` does not include `DependencyGraph`, validation
  results or document output
- Holding `YamlRepository` and `RelationshipRepository` does not by
  itself create Entity Context or Automation Context

## Alternatives Considered

- Extend `HomeAssistantModel` with YAML and relationships. Rejected:
  ADR-021 limits that model to registry objects
- Add `YamlRepository` and `RelationshipRepository` parameters to
  `ContextGenerator.generate`. Rejected: Module 13 needs one analysis
  result, and further context modules would keep extending the same
  signature. ADR-052 stays the pattern for document generators
- Let `ContextGenerator` read repositories or rediscover
  relationships. Rejected: that breaks the pure projection required
  by ADR-063
- Copy registry, YAML and relationship data into a new root context
  model. Rejected: that duplicates data and redesigns `AIContext`

---

# ADR-065

## Title

Entity and Automation Context Project AnalysisModel by Reference

## Status

Accepted

## Context

ADR-064 introduced `AnalysisModel` and kept `ContextGenerator.generate`
limited to the Module 13.1 registry sections. Entity Context and
Automation Context were explicitly deferred. Module 13.2 projects those
two contexts from the same aggregate.

## Decision

- Add `EntityContext` and `AutomationContext` as frozen child models on
  `AIContext`. Do not add a new root model and do not change
  `ContextSection` or `ContextSectionKind`
- `entity_contexts` and `automation_contexts` default to empty tuples,
  so existing `AIContext` construction stays valid
- `ContextGenerator.generate` still accepts only an `AnalysisModel`
- Entity context keeps the original `Entity`. Relationships are the
  edges already stored for `entity.entity_id`. Packages are included
  only when such an edge names a package that `YamlRepository` already
  holds. Automation package membership is not copied onto the entity
- Automation context keeps the original `Automation`, including
  triggers, conditions, actions, raw metadata and its package reference
- Related entities, scripts and scenes are existing objects found
  through relationships whose other endpoint has that type. The
  automation identity is `id` when present, otherwise `alias`
- Ids that do not resolve stay strings. The generator does not create
  objects and does not strip domain prefixes
- Collections are sorted and duplicate ids collapse to one object
- No filesystem access, YAML parsing, relationship discovery, validation,
  dashboard context, ESPHome context, package context, prompt builder,
  AI export or CLI wiring
- ADR-064 remains authoritative for `AnalysisModel`. This record
  supersedes only its statement that YAML objects and relationships
  are not projected yet

## Consequences

Advantages:

- Registry sections from Module 13.1 stay a pure projection
- Domain objects remain single instances
- Missing links stay visible as ids
- Later context modules can add their own child collections

Trade-offs:

- `AIContext` equality now includes entity and automation contexts
- An automation is matched by one relationship key, not by both `id`
  and `alias`
- Package membership exists only when a relationship already names the
  package

## Alternatives Considered

- Copy registry fields into a second entity record. Rejected: that
  duplicates `Entity` and drifts from the registry object
- Add entity and automation data as new `ContextSectionKind` values.
  Rejected: section items are original registry objects, and widening
  that union would change the Module 13.1 section contract
- Infer package ownership from an automation that references the
  entity. Rejected: the automation package is not entity membership
- Resolve `script.evening` to a script whose id is `evening`.
  Rejected: that invents an identifier the relationship does not store

---

# ADR-066

## Title

Dashboard Context Projects Metadata, Opaque Views and Existing Relationships

## Status

Accepted

## Context

ADR-064 introduced `AnalysisModel`. ADR-065 projects entity and
automation context from that aggregate and leaves dashboard context
for a later module. ADR-032 defines `Dashboard` as metadata plus
opaque `views`. Each view stays a `MappingProxyType`. Card
interpretation, a card model and reading keys inside a view are
outside that parser.

`YamlRepository.dashboards` already holds those `Dashboard` objects.
`RelationshipRepository` already holds dashboard relationships.
Module 13.3 projects context from those objects only.

## Decision

- Add `DashboardContext` as a frozen child model on `AIContext`. Do not
  add a new root model and do not change `ContextSection` or
  `ContextSectionKind`
- `dashboard_contexts` defaults to an empty tuple, so existing
  `AIContext` construction stays valid
- `ContextGenerator.generate` still accepts only an `AnalysisModel`
- Dashboard context keeps the original `Dashboard`. Metadata is that
  object's `id`, `title`, `mode` and `path`. `views` is that object's
  view tuple. No view key is read
- Do not add a `Card` model. Do not copy card mappings out of a view
- The relationship key is `id` when present, otherwise `title`. This is
  the key `DashboardRelationshipAnalyzer` already uses. A dashboard
  with neither id nor title contributes no relationships
- Referenced entities and related automations are existing objects
  found through relationships whose other endpoint has that type.
  Other relationship kinds, including device edges, stay in
  `RelationshipRepository` and are not copied onto the dashboard
  context
- Ids that do not resolve stay strings. Automation lookup uses
  `YamlRepository.get_automation`, which matches `Automation.id`. Alias
  is not a second key. Nothing is inferred from view contents
- Collections are sorted and duplicate ids collapse to one object
- No filesystem access, YAML parsing, relationship discovery or
  validation
- ADR-032 remains unchanged and remains authoritative for `Dashboard`
  and for opaque views
- ADR-064 remains authoritative for `AnalysisModel`. This record does
  not add a field to that aggregate
- ESPHome Context waits until an ESPHome domain model exists. This
  record does not add an ESPHome aggregate, an ESPHome field on
  `AnalysisModel`, or a placeholder context collection

## Consequences

Advantages:

- Registry, entity and automation projections stay unchanged
- Dashboard and view objects remain single instances
- View contents stay uninterpreted
- Missing links stay visible as ids
- ADR-032 stays intact

Trade-offs:

- `AIContext` equality now includes dashboard contexts
- Card structure stays inside the opaque view mappings
- Device relationships discovered by ADR-042 are not repeated on
  `DashboardContext`
- A dashboard is matched by one relationship key, not by both `id` and
  `title`

ESPHome Context stays a later module. The aggregates still have no
ESPHome device, sensor, binary sensor or switch model, no ESPHome
collection on `YamlRepository`, and no ESPHome member of `ObjectType`.

## Alternatives Considered

- Read the `cards` key and expose those mappings. Rejected: ADR-032
  keeps each view opaque, and this module does not inspect views
- Add a `Card` domain model. Rejected: that changes dashboard parsing
  and ADR-032
- Infer entity or automation links from values inside a view. Rejected:
  only relationships already stored in `RelationshipRepository` are
  used
- Extend `AnalysisModel` or add an empty ESPHome context. Rejected:
  ADR-064 fixes the aggregate, and there is no ESPHome domain model to
  project

---

# ADR-067

## Title

Prompt Builder Organises AIContext by a Fixed Section List

## Status

Accepted

## Context

ADR-064 keeps `AnalysisModel` as the aggregate `ContextGenerator`
consumes. ADR-065 and ADR-066 project entity, automation and dashboard
context onto `AIContext` by reference. Module 13.4 adds package context
the same way. Those records leave prompt building for a later module.

Module 13.5 must turn an existing `AIContext` into a deterministic
prompt without a second analysis pass.

## Decision

- Add package `ha_docgen.prompt` with `Prompt`, `PromptType`,
  `PromptSection`, `PromptSectionKind` and `PromptBuilder`
- Models are frozen dataclasses (`slots=True`); collections are tuples
- `PromptBuilder.build` accepts only an `AIContext` and a `PromptType`
- The builder is stateless. It does not modify `AIContext`
- It does not import repositories, `AnalysisModel`, parsers or
  relationship discovery
- Section selection is a fixed list per prompt type, in `AIContext`
  field order. Empty collections are omitted. Metadata is included
  only by the generic prompt, and it is always included there
  - Generic: metadata, registry sections, entity, automation,
    dashboard and package contexts
  - Programming: entity, automation and package contexts
  - Refactoring: entity, automation, dashboard and package contexts
  - Documentation: dashboard and package contexts
- A selected collection is the original tuple. Domain objects are not
  copied
- System instructions and task descriptions are fixed strings. They
  tell the reader to use only the supplied context. They do not name
  a language-model provider
- `formatting_hints` exists on `Prompt` and the builder leaves it
  empty. Choosing Markdown, JSON or plain text is not prompt building
- `AIContext`, `ContextGenerator`, `AnalysisModel`, repository models
  and relationship models stay unchanged
- No filesystem access, YAML parsing, validation, AI export, ESPHome
  context or CLI wiring
- `PromptBuilder` is not the document `MarkdownBuilder`. Document
  builders still render `Document` objects and still do not interpret
  Home Assistant models. This builder only chooses which `AIContext`
  fields to hold

## Consequences

Advantages:

- Prompt text cannot drift from a second analysis
- Domain objects remain single instances
- The same input always yields an equal prompt
- Provider and export choices stay outside this module

Trade-offs:

- A programming prompt does not repeat registry sections
- A refactoring prompt includes dashboard context and excludes registry
  sections
- Overlap already present on `AIContext`, such as an automation that
  also appears inside its package context, is kept when both sections
  are selected
- Empty metadata fields are still present on a generic prompt

## Alternatives Considered

- Read `AnalysisModel` or the repositories from the builder. Rejected:
  the presentation layer consumes `AIContext` only
- Copy context fields into prompt-specific records. Rejected: that
  duplicates domain objects
- Rank or score sections per task. Rejected: selection is a fixed list
- Emit provider-specific instructions. Rejected: the prompt stays
  provider-neutral
- Render Markdown or JSON from the builder. Rejected: export formats
  belong to a later module

---

# ADR-068

## Title

AI Export Renders an Immutable Prompt

## Status

Accepted

## Context

ADR-067 builds an immutable `Prompt` from `AIContext` and leaves
Markdown, JSON and plain text to a later module. Principle 7 keeps
those formats out of the prompt model. Document `MarkdownExporter`
writes already rendered `Document` files and is not this layer.

Module 13.6 renders a `Prompt`. It does not write files, and it does
not read `AnalysisModel`, repositories or `AIContext`.

## Decision

- Add package `ha_docgen.export`
- Public API: `ExportFormat`, `PromptExporter`, `MarkdownExporter`,
  `JsonExporter` and `PlainTextExporter`
- `ExportFormat` is `markdown`, `json`, then `plain_text`
- `PromptExporter.export` accepts a `Prompt` and an `ExportFormat`
- Each format exporter accepts a `Prompt` only
- Exporters are stateless and do not modify the prompt
- They do not import `AnalysisModel`, `AIContext`, `ContextGenerator`,
  repositories or relationship discovery, and they do not touch the
  filesystem
- JSON contains the stored prompt fields only. It does not add a
  display title, a property or a private field
- Object keys are sorted. Section order and other sequence order stay
  as stored
- Paths become POSIX strings, datetimes become ISO-8601 strings, and
  enums become their values
- The same shared object is expanded at each stored occurrence. A
  cycle raises `TypeError` instead of emitting a synthetic reference
- Markdown and plain text use one display title per `PromptType`:
  Generic Prompt, Programming Prompt, Refactoring Prompt or
  Documentation Prompt. That title is rendering, not a `Prompt` field
- Plain text uses no Markdown syntax
- Instructions stay provider-neutral
- `Prompt`, `PromptBuilder`, `AIContext`, `ContextGenerator` and
  `AnalysisModel` stay unchanged
- No ESPHome model, CLI wiring or reporting changes
- Document exporters still write files. This record does not change
  them

## Consequences

Advantages:

- Export format cannot drift into `Prompt` or `PromptBuilder`
- The same prompt always yields the same text
- Domain objects stay on the prompt; export copies them only into the
  returned text
- File writing remains a separate, already completed document concern

Trade-offs:

- A display title exists in Markdown and plain text and is absent from
  JSON, because JSON does not gain computed fields
- Overlap already stored on the prompt is repeated in the export
- Cyclic content cannot be exported
- These exporters know `Prompt` structure. Document exporters remain
  file writers and are not reused here

## Alternatives Considered

- Render inside `Prompt` or `PromptBuilder`. Rejected: ADR-067 and
  principle 7 keep formats out of those types
- Write the rendered text to disk in this module. Rejected: this
  module has no filesystem access, and CLI integration is a later
  concern
- Accept `AIContext` or `AnalysisModel`. Rejected: the dependency flow
  ends at `Prompt`
- Drop repeated nested objects. Rejected: that would omit fields the
  prompt stores
- Add a reference id for shared objects. Rejected: that is a computed
  field

---

# ADR-069

## Title

Include Directives Resolve Against ProjectTree

## Status

Accepted

## Context

ADR-002 scans the repository once. ADR-003 makes `ProjectTree` the
shared source for later reads. ADR-023 makes `YamlLoader` the only
component that reads YAML, using a safe loader and returning
`YamlDocument`.

Home Assistant configuration refers to other files with `!include` and
the four directory include tags. `yaml.safe_load` rejects those tags, so
a document that contains them never becomes a `YamlDocument`. Opening
the referenced path inside the loader would merge configuration and
perform a second read. Walking the filesystem again to find those paths
would bypass `ProjectTree`.

Module 14.3 discovers include locations only. It does not merge YAML,
expand packages, or build a configuration model.

## Decision

- `YamlLoader` remains the only YAML reader
- Parsing stays on a `SafeLoader` subclass. The five include tags
  become `IncludeNode` values. Every other tag still fails closed
- `IncludeNode` stores the directive and the raw path. It does not
  contain the included document
- `resolve_includes(tree, document)` is the public resolution entry
  point. It reads `ProjectTree` and one `YamlDocument`
- Relative paths join to the directory of `document.path`
- `!include` matches one stored `ProjectFile`
- Directory directives match YAML files stored directly in that folder,
  in the existing relative POSIX order
- A known directory with no YAML children is resolved and empty
- A missing path, a path outside the repository, or the wrong entry
  kind is unresolved
- Resolution does not call `discover_project`, `FilesystemWalker` or
  `Path.rglob`, and it does not open included paths
- Included documents are not loaded, so nested includes are not expanded
- No new repository type is introduced
- `FilesystemWalker`, `ScanPolicy`, `ProjectTreeBuilder`, `ProjectTree`,
  `Scanner`, the build pipeline, `AnalysisModel`, AI Context, Prompt
  Builder, Export and Reporting stay unchanged

## Consequences

Advantages:

- Include locations are available without a second repository walk
- Loaded documents keep their original text and do not gain merged
  contents
- Existing documents without include tags still parse as before
- Domain parsers that expect a list or mapping skip an `IncludeNode`
  and do not treat it as configuration content

Trade-offs:

- `YamlDocument.data` can now contain `IncludeNode` where an include
  tag appeared
- Documents that use other custom tags, such as `!secret`, still fail
  to load
- Unresolved includes are data on the reference. They are not scanner
  diagnostics
- Nested includes appear only when the included file is loaded as its
  own document

## Alternatives Considered

- Scan `YamlDocument.text` with a regular expression. Rejected: a
  string or comment can contain the same characters
- Keep `yaml.safe_load` and skip files that contain include tags.
  Rejected: those documents would never be available to resolve
- Open included paths inside `YamlLoader`. Rejected: that merges YAML
  and reads files the loader was not asked to load
- Search the filesystem for a missing path. Rejected: ADR-002 and
  ADR-003 keep `ProjectTree` as the only repository source
- Build a dependency graph or detect cycles. Rejected: that is a later
  module

---

# ADR-070

## Title

ESPHome Devices Belong to YamlRepository

## Status

Accepted

## Context

ADR-023 makes `YamlLoader` the only YAML reader and keeps domain
interpretation in parsers that consume `YamlDocument`. ADR-035 makes
`YamlRepository` the YAML aggregate. ADR-064 makes `AnalysisModel` the
single aggregate of registry, YAML and relationships, with exactly
those three fields. ADR-002 and ADR-003 keep one repository scan and
one `ProjectTree`. ADR-069 resolves include directives against that
tree and does not merge included YAML.

Module 15.1 needs an ESPHome device, sensor, binary sensor and switch
model, repository storage, and relationship identities. ESPHome Context
and reporting stay later modules. `scanners/esphome.py` is empty. The
legacy `ESPHomeNode` is a mutable scan value and is not part of
`AnalysisModel`.

## Decision

- Add package `ha_docgen.esphome` with frozen models `ESPHomeDevice`,
  `ESPHomeSensor`, `ESPHomeBinarySensor` and `ESPHomeSwitch`
- Models store typed fields only. They do not retain the source YAML
  mapping
- `ESPHomeParser.parse` accepts one `YamlDocument` and returns one
  `ESPHomeDevice`. It does not open files, call `YamlLoader`, expand
  substitutions, or load include targets
- Component `identity` is `{device-name}:{id}` when the id is present,
  otherwise `{device-name}:{name}`. Without a device name the identity
  is that id or name. Blocks with neither are omitted
- Nested mappings under `sensor`, `binary_sensor` and `switch` are
  components and inherit the nearest `platform`
- Component order is identity, platform, name, then id. Duplicate
  identities collapse to the component that sorts first
- `YamlRepository.esphome_devices` stores the devices, ordered by name
  then POSIX path. Devices without a name are retained and are not
  indexed. `get_esphome_device` looks up by name
- `AnalysisModel` does not gain a field. Callers reach devices through
  `yaml_repository`
- `ObjectType` gains `ESPHOME_DEVICE`, `ESPHOME_SENSOR`,
  `ESPHOME_BINARY_SENSOR` and `ESPHOME_SWITCH`. Existing
  `RelationshipType` values name the edges. This module does not add
  an analyzer
- Discovery, `ProjectTree`, `YamlLoader`, scanners, the production
  pipeline, AI Context and reporting stay unchanged

## Consequences

Advantages:

- ESPHome uses the existing YAML aggregate and the existing analysis
  aggregate
- Higher layers receive domain objects rather than YAML dictionaries
- Include targets and substitutions are not interpreted here
- Relationship storage can already name ESPHome endpoints

Trade-offs:

- The production pipeline does not populate `esphome_devices` yet
- A component identity is not discovered from Home Assistant entity ids
- Nested keys that happen to contain `name` or `id` become components
- The legacy `ESPHomeNode` remains on the scan model

## Alternatives Considered

- Add an ESPHome field to `AnalysisModel` or a second repository.
  Rejected: ADR-064 keeps three aggregates, and ADR-035 already stores
  YAML domain objects
- Retain the raw document mapping on `ESPHomeDevice`. Rejected: that
  leaks YAML into higher layers
- Load ESPHome files from the scanner or the production pipeline.
  Rejected: discovery and the scanner stay unchanged, and current
  ESPHome files use tags `YamlLoader` does not accept
- Add an analyzer that emits ESPHome relationships. Rejected: this
  module only makes those endpoints representable

---

# ADR-071

## Title

Standalone Repository Extraction

## Status

Accepted

## Context

HA-DocGen was developed as an application package nested under `tools/`
inside a Home Assistant configuration repository (`tools.ha_docgen`).
ADR-060 established standard Python packaging while retaining that nested
layout. ADR-061 and ADR-062 fixed version authority and release
automation against the same paths.

Functional development through Modules 1–16 was complete. Remaining work
was repository migration for standalone distribution: a dedicated
repository, a top-level import path, and a conventional `src` layout,
without changing the layered application architecture or runtime
behaviour.

## Decision

- Extract HA-DocGen into its own standalone Git repository
- Place production code under `src/ha_docgen/` with import name
  `ha_docgen` (replacing `tools.ha_docgen` for current packaging and
  imports)
- Keep the test suite in `tests/` outside the production package
- Preserve project documentation under `docs/`
- Keep usage examples and the default runtime configuration under
  `examples/`
- Retain `pyproject.toml` as the authoritative build configuration
  (ADR-060 principles), reading the version from
  `ha_docgen.version.VERSION` (ADR-061 principles)
- Introduce no new application architecture, pipeline redesign, or
  behavioural change as part of the extraction

## Consequences

Advantages:

- The project can be versioned, packaged and released independently of
  any Home Assistant configuration repository
- Installed and in-repo usage share the top-level `ha_docgen` import
  path
- Tests, documentation and examples stay outside the distributed
  runtime package
- Prior ADRs that define application layers and domain models remain
  authoritative

Trade-offs:

- Historical ADRs and changelog entries that name `tools.ha_docgen`
  describe the former layout and must be read with that context
- Consumers and documentation that still assumed the nested `tools/`
  path require a path migration (completed in documentation Phases
  4.1–4.3)

## Relationship to previous decisions

- ADR-060: packaging authority and exclusion of tests from distributions
  remain; the nested `tools.ha_docgen` layout decision is superseded for
  current repository structure by this ADR
- ADR-061: single authoritative `VERSION` independent of Git remains;
  the module path is now `ha_docgen.version`
- ADR-062: release automation stays outside the application package;
  workflow details continue to target the standalone repository
- ADR-001 through ADR-070: application architecture and domain decisions
  are unchanged by the extraction

## Alternatives Considered

- Keep HA-DocGen nested under `tools/` inside the Home Assistant
  repository. Rejected: blocks independent distribution and a standard
  top-level package
- Redesign layers or the analysis pipeline during extraction. Rejected:
  migration scope is repository layout only
- Rename or split packages beyond `ha_docgen`. Rejected: unnecessary for
  standalone extraction and would rewrite accepted architecture

---

# Future Decisions

Future architectural decisions should be recorded here.

Examples include:

- Plugin architecture
- Incremental scanning
- Parallel scanning
- HTML documentation
- Graph visualisation / filtered Entity and Package views
- Database support
- REST API
- Web interface

---

# Maintenance

This document should be updated whenever a significant architectural decision is made.

The goal is to preserve architectural knowledge for future development.