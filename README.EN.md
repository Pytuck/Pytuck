# Pytuck - Lightweight Python Document Database

<div align="center">
  <img src="https://raw.githubusercontent.com/Pytuck/Pytuck/master/logo.svg" width="120" alt="Pytuck logo">
</div>

[![Gitee](https://img.shields.io/badge/Gitee-Pytuck%2FPytuck-red)](https://gitee.com/Pytuck/Pytuck)
[![GitHub](https://img.shields.io/badge/GitHub-Pytuck%2FPytuck-blue)](https://github.com/Pytuck/Pytuck)

[![PyPI version](https://badge.fury.io/py/pytuck.svg)](https://badge.fury.io/py/pytuck)
[![Python Versions](https://img.shields.io/pypi/pyversions/pytuck.svg)](https://pypi.org/project/pytuck/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文](README.md) | English

A lightweight, pure Python document database with multi-engine support. No SQL required — manage your data through Python objects and methods.

> **Design Philosophy**: Provide a zero-dependency relational database solution for restricted Python environments like Ren'Py, enabling SQLAlchemy-style Pythonic data operations in limited environments.

> [!IMPORTANT]
> **When to use Pytuck**: Pytuck is a pure Python embedded database designed for **small-to-medium datasets** and **restricted environments**.
> - **Data volume**: The "~10K / 100K+" guidance mainly refers to the row count of a **single hot table**. Best for up to ~10K rows; when one table approaches or exceeds 100K rows, prefer DuckDB / SQLite or evaluate alternatives. As total row count across tables grows, overall I/O and load time will also rise
> - **Performance**: Pure Python means it cannot match C-extension databases (SQLite, PostgreSQL, etc.) — not suitable for high-concurrency or compute-intensive scenarios
> - **Concurrency**: Designed for single-process embedded use; no multi-process concurrent access support
> - **If your environment has no special restrictions**, consider [SQLAlchemy](https://www.sqlalchemy.org/) + SQLite/PostgreSQL first — they offer better performance, a more mature ecosystem, and broader community support

## Repository Mirrors

- **GitHub**: https://github.com/Pytuck/Pytuck
- **Gitee**: https://gitee.com/Pytuck/Pytuck

## Key Features

- **No SQL required**: Work entirely with Python objects and methods
- **Multi-engine support**: Pytuck, JSON, JSONL, CSV, SQLite, DuckDB, Excel, XML
- **Pluggable architecture**: Zero dependencies by default, optional engines on demand
- **SQLAlchemy 2.0 style API**: `select()` / `insert()` / `update()` / `delete()`
- **Generic type hints**: Precise model-aware IDE and type-checker inference
- **Index optimization**: Hash and sorted indexes accelerate equality, range, and ordering queries
- **Relationships and prefetch**: `Relationship` and `prefetch()` help with N+1 scenarios
- **Type safety**: Built-in conversion, strict mode, and custom `validator`
- **Flexible persistence**: Manual `flush()` or `auto_flush=True`

## Recent Highlights

Compared with the previous public release, these are the three updates worth noticing first:

- **`ujson` is no longer part of the documented or built-in JSON / JSONL support path**: the supported built-in path is now the standard-library `json` plus optional `orjson`, which keeps behavior more predictable and reduces implementation branching
- **`Storage.flush()` now uses a multi-thread write lock**: this lowers the risk of concurrent disk-write races when the same `Storage` instance is flushed from multiple threads; it does not change Pytuck's overall single-process embedded-database positioning
- **`Relationship` / `prefetch()` now support cross-storage relationship loading**: this fits split-database layouts such as a read-mostly base catalog plus a user-data database, even when the two files use different engines; Pytuck still **does not support joins**, so cross-table reads remain relationship-driven or manually composed from separate queries

## Documentation Map

The README home page now focuses on project positioning, installation, and minimal getting-started examples. Detailed explanations have been split into `docs/`:

| Document | Content |
|----------|---------|
| [API docs index](./docs/api/index.md) | API overview and entry point |
| [Engine comparison & configuration](./docs/api/engines.md) | Engine features, configuration, limits, and selection advice |
| [Best practices](./docs/api/best-practices.md) | Persistence, indexing, transactions, performance tuning |
| [Storage API](./docs/api/storage.md) | `Storage` / `Table` / `flush()` / `transaction()` |
| [Session API](./docs/api/session.md) | `Session`, transactions, object state management |
| [Query system](./docs/api/query.md) | `select` / `insert` / `update` / `delete` and result handling |
| [Tools & migration](./docs/api/tools.md) | `migrate_engine()`, `import_from_database()`, benchmark scripts, hooks, prefetch |
| [Benchmark report](./docs/guide/benchmark.en.md) | Latest benchmark results and reproduction commands |
| [Development & release guide](./docs/guide/development.en.md) | Installation details, uv workflow, contributing, build & release |
| [Development TODO](./TODO.md) | Current roadmap and development tasks |
| [Changelog](./CHANGELOG.EN.md) | Latest changes and archive entry points |

## Quick Start

### Installation

```bash
# Basic installation (includes pytuck / json / jsonl / csv / sqlite, zero external deps)
pip install pytuck

# Install optional engines / accelerators
pip install pytuck[duckdb]  # DuckDB engine (requires duckdb)
pip install pytuck[excel]   # Excel engine (requires openpyxl)
pip install pytuck[xml]     # XML engine (requires lxml)
pip install pytuck[orjson]  # Optional JSON / JSONL acceleration

# Install all optional dependencies
pip install pytuck[all]

# Development environment
pip install pytuck[dev]
```

### Basic Usage

Pytuck offers two common usage modes:

#### Mode 1: Pure Model (Default, Recommended)

```python
from typing import Type
from pytuck import Storage, declarative_base, Session, Column
from pytuck import PureBaseModel, select, insert

# Create database (default: pytuck engine)
db = Storage(file_path='mydb.pytuck')
Base: Type[PureBaseModel] = declarative_base(db)

class Student(Base):
    __tablename__ = 'students'

    id = Column(int, primary_key=True)
    name = Column(str, nullable=False, index=True)
    age = Column(int)

session = Session(db)
session.execute(insert(Student).values(name='Alice', age=20))
session.commit()

alice = session.execute(
    select(Student).where(Student.name == 'Alice')
).first()
print(alice.name)

# Default auto_flush=False: data reaches disk only after flush/close
db.flush()
db.close()
```

#### Mode 2: Active Record

```python
from typing import Type
from pytuck import Storage, declarative_base, Column
from pytuck import CRUDBaseModel

# Create database
db = Storage(file_path='mydb.pytuck')
Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

class Student(Base):
    __tablename__ = 'students'

    id = Column(int, primary_key=True)
    name = Column(str, nullable=False)
    age = Column(int)

alice = Student.create(name='Alice', age=20)
adults = Student.filter(Student.age >= 18).all()

alice.age = 21
alice.save()

db.flush()
db.close()
```

**How to choose?**
- **Pure Model mode**: Better for larger projects, team development, and clear data-access layering
- **Active Record mode**: Better for small projects, rapid prototyping, and simple CRUD flows

> **Persistence note**: The default is `auto_flush=False`. `session.commit()` / `Model.save()` only commit to in-memory state by default; data reaches disk after `db.flush()` or `db.close()`. See [Best Practices - Persistence Strategy](./docs/api/best-practices.md#持久化策略) for details.

## Storage Engines at a Glance

- **Pytuck**: Default single-file engine, zero dependencies, a good fit for embedded and restricted environments, with current new writes supporting `None` / `low` / `medium` / `high`; encrypted files include HMAC-SHA256 integrity authentication while legacy encrypted PTK7 files remain readable

> **Pytuck note**: The default single-file path currently prioritizes long-term format stability, true single-file persistence, and the open / reopen / primary-key lookup experience. It is not meant to be the universally fastest engine across every benchmark dimension. If you care more about native SQL, very large datasets, or specific peak benchmark numbers, prefer SQLite / DuckDB.
- **JSON**: Best when readability and debugging matter most
- **JSONL**: Good for multi-table text archives and line-oriented exchange
- **CSV**: Good for minimum size and spreadsheet-style interchange
- **SQLite**: Good for stable SQL write paths, transactions, and fast loading
- **DuckDB**: Good for analytical queries, DuckDB ecosystem integration, and multi-schema use
- **Excel**: Good for visual editing, reports, and office handoff
- **XML**: Good for standardized exchange and enterprise integration

> **SQLite note**: With `use_native_sql=True` (default), behavior is closer to native SQLite and support for Chinese column names / special identifiers is limited. If you need names like `Column.name='用户名'`, switch to `SqliteBackendOptions(use_native_sql=False)` compatibility mode. See [docs/api/engines.md](./docs/api/engines.md#sqlite-引擎).

## Performance & Benchmarking

- The latest multi-engine benchmark results are in [docs/guide/benchmark.en.md](./docs/guide/benchmark.en.md)
- The same guide now also includes a focused `json` / `jsonl` comparison between the standard-library `json` and `orjson`; at the current `100000`-record scale, `orjson` shows a consistent gain on `save` / `load` / `reopen` for both text-oriented engines
- The benchmark guide gives a direct comparison across engines for insert, indexed query, non-indexed query, range query, save, load, and file size
- For Session write paths on the same local 100k in-memory benchmark, `session.add_all() + commit()` is about `0.72s` and `session.bulk_insert()` is about `0.41s`; the former keeps per-row `before_insert` / `after_insert` semantics, while the latter gives the highest throughput
- Benchmark script documentation lives in [docs/api/tools.md](./docs/api/tools.md#benchmark-脚本)
- To reproduce locally:

```bash
uv run python tests/benchmark/benchmark.py -n 100000 --extended --output-json /tmp/pytuck-benchmark.json
```

## Data Migration

Migrate data between engines:

```python
from pytuck.tools.migrate import migrate_engine
from pytuck.common.options import JsonBackendOptions

json_opts = JsonBackendOptions(indent=2, ensure_ascii=False)

migrate_engine(
    source_path='data.pytuck',
    source_engine='pytuck',
    target_path='data.json',
    target_engine='json',
    target_options=json_opts,
)
```

You can also import existing databases from SQLite / DuckDB into any supported Pytuck target engine.

For more migration and import details, see [docs/api/tools.md](./docs/api/tools.md#数据迁移工具).

## Project Status & Further Reading

- **Detailed roadmap**: [TODO.md](./TODO.md)
- **Version history**: [CHANGELOG.EN.md](./CHANGELOG.EN.md) and [docs/changelog/](./docs/changelog/)
- **Complete API docs**: [docs/api/index.md](./docs/api/index.md)
- **Development & release workflow**: [docs/guide/development.en.md](./docs/guide/development.en.md)

## Examples

See the `examples/` directory for more examples:

- `sqlalchemy20_api_demo.py` - Complete SQLAlchemy 2.0 style API example (recommended)
- `active_record_demo.py` - Active Record example
- `new_api_demo.py` - Pure model example
- `migration_tools_demo.py` - Data migration demo

## Contributing

Issues and Pull Requests are welcome.

## License

MIT License

## Acknowledgments

Inspired by SQLAlchemy and TinyDB.
