# Architecture Principles

These rules define the fixed design principles for HA-DocGen.

They apply to the entire project.

Deviations must only be introduced through a new Architecture Decision Record (ADR).

---

# 1. Layered Architecture

The architecture consists of the following layers, in order:

```text
Scanner
  ↓
Models
  ↓
Repositories
  ↓
Relationship Analysis
  ↓
Dependency Graph
  ↓
Document Generation
  ↓
Validation
  ↓
AI Context
```

Rules:

- Dependencies must flow downward only.
- Cyclic dependencies must not exist.
- Lower layers must not know about higher layers.

---

# 2. Immutability

All public models must be:

- frozen dataclasses
- slots-enabled (`slots=True`)
- based on tuples for collections
- free of mutable defaults
- exposed through an immutable API

Public models must not be mutated after construction.

---

# 3. Stateless Components

The following component types must be fully stateless:

- Analyzers
- Validators
- Generators
- Builders
- Exporters

Rules:

- They must not hold internal state.
- They must not cache results.
- They must not use singletons.

---

# 4. Repository Pattern

Repositories must contain only:

- immutable collections
- `MappingProxyType` indexes
- O(1) lookups
- deterministically sorted data

Repositories must never perform analysis.

Repositories must never contain business logic.

---

# 5. Validation Philosophy

Validation must report only objectively demonstrable configuration errors.

Validation must not report:

- unused entities
- unused automations
- orphan dashboards
- unused helpers
- optimisations
- refactoring suggestions
- performance advice

Those concerns belong in a future Analysis/Quality module.

---

# 6. Separation of Responsibilities

Each component has exactly one responsibility:

| Component   | Responsibility                         |
|-------------|----------------------------------------|
| Scanners    | Read data                              |
| Parsers     | Translate raw data into models         |
| Repositories| Store immutable collections            |
| Analyzers   | Discover relationships                 |
| Graph       | Build dependency structures            |
| Generators  | Build Document objects                 |
| Builders    | Render documents                       |
| Exporters   | Write files                            |

Components must not assume responsibilities of other layers.

---

# 7. Output Independence

Document models must not know about:

- Markdown
- HTML
- JSON
- the filesystem

Builders must not know about Home Assistant.

Exporters must not know about document structure.

---

# 8. Public API

The public API of a package must be exposed exclusively through `__init__.py`.

Private helpers must start with `_`.

Packages must not import internal modules from other packages.

---

# 9. Determinism

All output must be deterministic.

All collections must be:

- sorted
- immutable
- deduplicated when necessary

Output must not depend on dictionary insertion order.

---

# 10. Extensibility

New functionality must be added by extension.

Existing public APIs must not be changed unless necessary.

New features must not redesign existing modules.

---

# 11. Documentation Rules

When a new module is introduced:

- `roadmap.md` must be updated
- `changelog.md` must be updated
- a new ADR must be created if the architecture changes

An ADR must not be created for small refactors or type-hint-only changes.

---

# 12. Cursor Development Rules

Cursor must:

- follow the assigned scope strictly
- not add extra features
- not change architecture without explicit instruction
- not introduce business logic outside the target module
- always run `python -m tools.ha_docgen.main`
- always provide an architecture confirmation after implementation
