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

## Related Docs

- [README home](../../README.EN.md)
- [API docs index](../api/index.md)
- [Benchmark report](benchmark.en.md)
- [Development TODO](../../TODO.md)
