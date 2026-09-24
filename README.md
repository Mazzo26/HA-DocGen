# HA-DocGen

HA-DocGen analyzes Home Assistant configuration repositories and generates structured documentation, inventories, and related project context from YAML configuration, packages, automations, and related assets.

**Status:** Version 1.0.0 — release preparation

## Quick Start

1. Install:

```bash
pip install ha-docgen
```

2. Create a configuration from the example:

```bash
# Linux / macOS
cp examples/config.yaml my-config.yaml

# Windows (Command Prompt)
copy examples\config.yaml my-config.yaml
```

3. Edit `my-config.yaml` and set `paths.root` to your Home Assistant config directory.

4. Run:

```bash
ha-docgen --config my-config.yaml
```

Generated documentation is written under `paths.root` at the path configured in `output.docs` (default: `docs/generated`). Override with `--output` if needed.

For a full option list, see `examples/config.yaml` or run `ha-docgen --help`.

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
