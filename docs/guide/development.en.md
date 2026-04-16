# Pytuck Development & Release Guide

This page collects installation details, contributor setup, and release workflow that are more maintainer-oriented than the README home page.

## Installation Options

### Install from PyPI

```bash
# Basic installation (includes pytuck / json / jsonl / csv / sqlite)
pip install pytuck

# With specific extras
pip install pytuck[all]      # All optional dependencies
pip install pytuck[duckdb]   # DuckDB support only
pip install pytuck[excel]    # Excel support only
pip install pytuck[xml]      # XML support only
pip install pytuck[orjson]   # Optional JSON / JSONL acceleration
pip install pytuck[ujson]    # Optional JSON / JSONL acceleration
pip install pytuck[dev]      # Development tools
```

### Add to a uv-managed Project (Recommended)

[uv](https://github.com/astral-sh/uv) is an extremely fast Python project and package manager. If your application already uses uv, add pytuck directly to your project dependencies:

```bash
# Basic installation (includes pytuck / json / jsonl / csv / sqlite)
uv add pytuck

# With specific extras
uv add "pytuck[all]"       # All optional dependencies
uv add "pytuck[duckdb]"    # DuckDB support only
uv add "pytuck[excel]"     # Excel support only
uv add "pytuck[xml]"       # XML support only
uv add "pytuck[orjson]"    # Optional JSON / JSONL acceleration
uv add "pytuck[ujson]"     # Optional JSON / JSONL acceleration
```

## Contributors: Sync the Development Environment

If you cloned the repository to contribute, do not manually install the project into the current environment with an editable install. Sync the project's development environment directly instead:

```bash
# Clone repository
git clone https://github.com/Pytuck/Pytuck.git
cd pytuck

# Sync development environment (includes test tools and optional engines)
uv sync --extra dev

# Run tests or examples
uv run pytest tests/ -v
uv run python examples/sqlalchemy20_api_demo.py
```

## Build and Publish

```bash
# Build wheel and source distribution
uv build

# Publish to PyPI (use configured credentials or pass a token explicitly)
uv publish
# uv publish --token $PYPI_TOKEN

# Publish to TestPyPI (configure the index in pyproject.toml first)
uv publish --index testpypi
# uv publish --index testpypi --token $TEST_PYPI_TOKEN
```

> `uv publish --index testpypi` requires a configured `[[tool.uv.index]]` entry with both `url` and `publish-url`.

> [!IMPORTANT]
> `pyproject.toml` intentionally keeps `license = {text = "MIT"}` for now. `uv build` will emit a setuptools deprecation warning for `project.license` as a TOML table, but do not switch to a SPDX string just to silence the warning, because that path depends on `setuptools>=77` and breaks the current Python `3.7` / `3.8` packaging compatibility. Only switch to `license = "MIT"` / `license-files` after the project raises its minimum supported Python version or intentionally upgrades the build chain.

## Release Checklist

Before publishing, run through this short checklist in order:

1. Get the actual release date from the system instead of typing it manually:

   ```bash
   date '+%Y-%m-%d'
   ```

2. Confirm the version and changelog layout:
   - Update the version in `pyproject.toml`
   - Update `CHANGELOG.md` and `CHANGELOG.EN.md`
   - If the previous release should be archived out of the root changelog, move it to `docs/changelog/{version}.md`

3. Sync every user-visible document:
   - `README.md` / `README.EN.md`
   - `CHANGELOG.md` / `CHANGELOG.EN.md`
   - If the development guide, benchmark docs, or other public docs changed, update the matching English file as well

4. Run pre-release verification (the default-dependency example baseline must stay aligned with the "Recommended getting started examples" section in `examples/README.md`):

   ```bash
   uv run pytest tests/ -v
   uv run python examples/session_api_demo.py
   uv run python examples/active_record_demo.py
   uv build
   ```

5. Publish only after verification succeeds:

   ```bash
   uv publish
   # Or publish to TestPyPI
   uv publish --index testpypi
   ```

> If this release adds new docs, examples, or other user-visible behavior, finish the Chinese and English updates before building and publishing.

## Related Docs

- [README home](../../README.EN.md)
- [API docs index](../api/index.md)
- [Benchmark report](benchmark.en.md)
- [Development TODO](../../TODO.md)
