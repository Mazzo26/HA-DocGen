# HA-DocGen

HA-DocGen analyzes Home Assistant configuration repositories and generates structured documentation, inventories, and related project context from YAML configuration, packages, automations, and related assets.

**Status:** Repository Migration in Progress

## Repository layout

```
src/ha_docgen/   production package
tests/           test suite
docs/            project documentation
examples/        usage examples; default config (`examples/config.yaml`)
```

Install and run from the repository root:

```bash
pip install -e ".[dev]"
python -m ha_docgen --help
# or: ha-docgen --help
```

Documentation lives in the `docs/` directory.
