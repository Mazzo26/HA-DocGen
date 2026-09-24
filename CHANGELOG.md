# Changelog

All notable user-facing changes to HA-DocGen are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Module-level implementation history remains in [`docs/changelog.md`](docs/changelog.md).

---

## [1.0.0] — 2026-09-24

First stable public release of HA-DocGen as a standalone package.

### Added

- **Home Assistant analysis** — discover and model configuration repositories, including storage registries, YAML packages, root YAML, includes, and ESPHome devices
- **Relationship analysis** — entity, device, automation, script, dashboard and MQTT relationship graphs with an immutable dependency graph
- **Documentation generation** — package, entity, automation, dashboard and configuration documents exported as Markdown
- **Validation** — entity, automation, dashboard, package and MQTT validators with an immutable validation repository and report
- **Reporting** — health, configuration, architecture, inventory, dependency, performance, documentation-index and Home Assistant inventory reports with console, Markdown and JSON renderers
- **AI Context** — immutable context models, entity/automation/dashboard/package/ESPHome projections, prompt builder and Markdown/JSON/plain-text export
- **CLI** — `ha-docgen` entrypoint with scan, `validate`, `report`, `init`, `help` and `version`; quiet/verbose/debug modes; incremental scanning
- **Project initialization** — `ha-docgen init` creates a fully documented default `config.yaml` without overwriting an existing file
- **Packaging** — installable wheel and source distribution with console script `ha-docgen`

### Notes

- Requires Python 3.14 or newer
- Does not modify the analysed Home Assistant installation
- GitHub Release notes and PyPI publishing are handled separately from this changelog
