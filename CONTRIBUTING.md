# Contributing

Thank you for your interest in contributing to HA-DocGen.

## Guidance

| Topic | Location |
|-------|----------|
| Project overview | [`docs/README.md`](docs/README.md) |
| Module status | [`docs/modules.md`](docs/modules.md) |
| Roadmap | [`docs/roadmap.md`](docs/roadmap.md) |
| Testing | [`docs/development/testing.md`](docs/development/testing.md) |
| Releases | [`docs/development/release.md`](docs/development/release.md) |

Also read:

- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SUPPORT.md](SUPPORT.md)
- [SECURITY.md](SECURITY.md)

## Local setup

From the repository root:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m pytest
```

Use `python -m ha_docgen --help` (or `ha-docgen --help`) after the
editable install. The default runtime configuration path is
`examples/config.yaml`.
