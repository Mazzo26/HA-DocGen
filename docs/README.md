# HA-DocGen

> Enterprise-grade documentation generator for Home Assistant.

---

# Overview

HA-DocGen is a standalone Python application that analyses a Home Assistant configuration and automatically generates technical documentation.

The application is **strictly read-only**.

It never modifies the Home Assistant configuration or any production data.

Its purpose is to improve maintainability, documentation and architectural insight for medium to large Home Assistant installations.

---

# Goals

HA-DocGen is designed to:

- Analyse the complete Home Assistant configuration.
- Build an internal representation of the project.
- Detect relationships between entities, packages and integrations.
- Generate consistent documentation.
- Provide architectural insights.
- Support long-term maintenance.
- Reduce manual documentation effort.

---

# Key Principles

- Read-only operation
- Strong typing
- Modular architecture
- SOLID design principles
- Testable components
- Enterprise-grade code quality

---

# Current Architecture

```
Filesystem
      │
      ▼
ProjectWalker / ProjectTreeBuilder
      │
      ▼
ProjectTree
      │
      ▼
Scanners / Registry Parsers / YAML Parsers
      │
      ├──────────────┐
      ▼              ▼
HomeAssistantModel  YamlRepository
      │              │
      └──────┬───────┘
             ▼
  Relationship Analyzers
             │
             ▼
  RelationshipRepository
             │
             ▼
       DependencyGraph
             │
             ▼
        Generators
             │
             ▼
          Writers
             │
             ▼
   Markdown / JSON
```

---

# Repository Structure

```
tools/
└── ha_docgen/
    ├── docs/
    ├── project/
    ├── policy/
    ├── storage/
    ├── registries/
    ├── yaml/
    ├── packages/
    ├── relationships/
    ├── graph/
    ├── scanners/
    ├── generators/
    ├── writers/
    ├── main.py
    └── ...
```

---

# Documentation

HA-DocGen documentation lives in this directory:

```
tools/ha_docgen/docs/
```

Available documents include:

- README.md (this file)
- architecture-principles.md (primary source for Cursor implementations)
- architecture.md
- modules.md
- roadmap.md
- design-decisions.md
- changelog.md
- [development/testing.md](development/testing.md)
- [development/release.md](development/release.md)

Home Assistant installation documentation lives in the repository `docs/` folder and is out of scope for this directory.

Additional documentation will be added as development progresses.

---

# Development Requirements

Minimum requirements:

- Python 3.14
- Virtual Environment (.venv)
- Git
- Cursor Pro

Recommended tools:

- Ruff
- Black
- Pyright
- pytest

---

# Running HA-DocGen

Activate the virtual environment.

Windows:

```powershell
.venv\Scripts\activate
```

Run the application from the repository root:

```bash
python -m tools.ha_docgen.main
python -m tools.ha_docgen.main --help
python -m tools.ha_docgen.main --version
```

The default command scans the repository. `validate` checks the runtime configuration. `report` generates `health`, `config`, `architecture`, `inventory`, `dependencies`, `performance` or `docs`.

`--quiet`, `--verbose` and `--debug` select the log level. `--config` and `--output` select paths. `--incremental`, `--force` and `--clean-cache` apply only to the default scan.

---

# Continuous Integration

Pushes and pull requests targeting `main` or `develop` run
`.github/workflows/ci.yml` on Python 3.14.

The workflow:

1. checks out the repository
2. sets up Python and upgrades pip
3. installs the package with development extras (`pip install -e ".[dev]"`)
4. runs `python -m pip check`
5. runs `python -m pytest`
6. runs `python -m build`
7. runs `twine check dist/*`
8. uploads the `dist/` directory as a workflow artifact

Any failed step fails the job. The workflow does not publish releases or
upload to PyPI.

## Local validation

From the repository root, after creating a virtual environment:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m pip check
python -m pytest
python -m build
twine check dist/*
```

---

# Release Automation

Automated GitHub Releases and a dedicated release workflow are not part of
the current CI pipeline. Contributor release notes in
[development/release.md](development/release.md) describe the intended
later process and should be treated as planning guidance until that
workflow exists.

---

# Version

The application version lives in exactly one place:

```
tools/ha_docgen/version.py
```

`VERSION` is a semantic version (`MAJOR.MINOR.PATCH`, with optional
prerelease and build metadata). `pyproject.toml` reads that constant at
build time. The CLI (`ha-docgen --version`), package `__version__` and
installed distribution metadata all use the same value.

Version discovery does not use Git. Source checkouts, editable installs
and installed wheels therefore report the same version.

To change the version, update `VERSION` in `version.py` only, then rebuild
distributions if you need new artifacts.

GitHub Releases are created from matching version tags. The full release
procedure is in [development/release.md](development/release.md). PyPI
publishing, changelog generation and automatic version bumps remain out
of scope.

---

# Package Build

`pyproject.toml` is the single authoritative build configuration.

Runtime dependencies and the `dev` extra are declared there. `requirements.txt` and `requirements-dev.txt` only install that configuration.

Build distributions from the repository root:

```bash
python -m build --sdist --wheel
```

Artifacts are written to `dist/`:

- source distribution (`.tar.gz`)
- wheel (`.whl`)

Install the wheel into a clean environment and run the console script:

```bash
python -m pip install dist/ha_docgen-*.whl
ha-docgen --version
```

The installed import path remains `tools.ha_docgen`. `python -m tools.ha_docgen.main` continues to work after installation.

Wheel and sdist metadata versions match `tools.ha_docgen.version.VERSION`.

Distributions include runtime package code only. Tests, documentation, caches and `tools/config.yaml` are not packaged.

PyPI publishing remains out of scope for this package build layer. GitHub
Releases attach the same wheel and sdist artifacts after version validation.

---

# Development Workflow

Development follows this general process:

1. Create a feature branch.
2. Implement functionality.
3. Validate code.
4. Update documentation.
5. Commit changes.
6. Merge into `develop`.
7. Test.
8. Merge into `main`.

---

# Current Development Status

Module 12 – Release is completed. The release procedure is in
[development/release.md](development/release.md).

See [`roadmap.md`](roadmap.md) for the status of every module.

---

# Relationship with Home Assistant

HA-DocGen is an independent application.

It analyses the Home Assistant repository but does not form part of the Home Assistant runtime.

```
Home Assistant Repository
           │
           ▼
      HA-DocGen
           │
           ▼
Documentation
```

---

# Future Development

Later work is recorded only in [`roadmap.md`](roadmap.md).

---

# License

Private project.

---

# Author

Alex Wolff

Developed as part of a professional Home Assistant engineering environment.