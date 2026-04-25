# Pytuck - Lightweight Python Document Database

<div align="center">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1516 1516" width="120" height="120" role="img" aria-label="Pytuck logo">
    <path fill="#0d2647" d="m1166 73 40 1 28 13 17 15 23 33 32 12 12 10 11 27-1 28-8 19-13 13-7 15-11 13-33 18 28 12 19 14 12 15 8 24v294l-3 14-9 16 9 8 4 14-1 331-8 24-20 22 19 16 9 19 1 227-7 46-19 38-19 22-32 24-39 17-36 8h-808l-30-5-34-11-26-12-28-20-22-23-17-26-8-19-4-30 1-235 9-18 14-13 9-4-23-24-6-10-4-17v-280l7-22 13-13 12-7-25-27-7-28v-293l4-21 11-19 27-25 24-13 38-14 46-9 586-2 13-47 18-38 21-31 36-34 26-15 25-10 25-4h51z"/>
    <path fill="#195c94" d="m1194 300h35l23 8 32 18 14 18-1 10-8 10-35 18-59 16-78 11 5-73 10-31 3-3zm-947 418 86 26 58 10 102 10 144 4 7 3-30 24-108-3-117-11-69-13-55-18-21-13-1-8zm2 371 62 22 52 11 71 10 102 7 13 24-1 3h-5l-97-6-73-9-45-9-54-16-26-13-6-6v-6zm1024 2h4l10 11-1 7-5 5-23 12-36 12-20 3-18-11-22-7 2-3 64-12z"/>
    <path fill="#f0bd15" d="m1178 90 25 2 22 11 14 13 26 33 34 13 11 17 1 25-4 12-7 8-20 1-22 14-14 3-21-1-17-6-3 3 1 8 15 7 30 2 36-15 5 4-5 8-23 18-24 8-24 3-90 1-31-3-28-7-4 5 1 5 11 7 20 7 21 3-12 40-5 72-160 6 2-79 11-77 16-54 28-51 31-32 39-22 30-7h51zm120 604 4 1 1 5v155l-5 9-22 19-44 18-45 8-372 2-38 14-27 22-20 31-8 29 3 37 15 31 27 26 32 15 43 5h229l27 3 30 6 41 14 36 20 31 24 28 31 24 42 13 43 2 43-8 37-16 30-26 27-32 19-29 10-37 4v-84l-5-26-18-31-17-15-24-13-41-8-265-1-51-10-34-12-34-17-46-34-30-33-17-26-23-49-14-68v-49l6-38 10-36 20-44 31-45 31-32 27-21 39-22 50-19 69-12 379-1 67-16z"/>
    <path fill="#3c8ec4" d="m368 276h560v5l-8 54-3 82h-360l-94-3-91-9-82-17-51-22-14-13-3-12 10-16 16-14 50-23 35-8zm-152 96 25 18 28 12 86 21 127 12 140 3 361-1 110-6 79-9 50-10 40-12 27-13 11-10 2 3-1 270-4 14-17 18-20 10-32 10-49 8-386 2-63 14-60 25-170-5-117-12-49-9-48-13-31-12-23-15-11-12-5-14zm2 370 20 15 23 11 43 14 44 10 105 14 143 8-21 24-21 33-22 49-11 40-5 30-1 51 4 37 11 42-99-7-84-13-49-12-36-13-26-15-18-22zm1081 148 3 2-3 151-18 21-12 8-56 20-84 17-56-8-252-1-30-8-21-13-17-20-10-27 1-32 15-33 20-20 32-15 26-3 360-1 30-5 36-11 23-11zm-1080 226 19 14 21 10 76 22 96 14 128 6 26 34 47 43 55 31 61 20 52 7h253l28 5 32 20 18 27 4 20v84l-767 1-26-4-33-10-36-19-31-28-12-18-12-30zm1081 1 2 129-20-34-20-25-24-22-14-8v-3l16-3 38-15 13-8z"/>
    <path fill="#0d2647" d="m1128 148 16 1 14 10 6 14v15l-6 13-15 11h-15l-18-13-6-14 2-17 11-15zm97 51 9 3 1 8-2 3-6-2-3-5zm-723 348h514l12 4 9 8 5 11v13l-5 11-8 8-20 6-506-1-16-9-9-16v-11l5-11 8-8z"/>
    <path fill="#ffffff" d="m1127 162 6 1 4 7-5 6-7-1-3-7z"/>
    <path fill="#3c8ec4" d="m506 562h498l16 3 6 7v10l-10 10h-510l-12-11 1-11z"/>
  </svg>
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

- **Pytuck**: Default single-file engine, zero dependencies, a good fit for embedded and restricted environments, with current new writes supporting `None` / `low` / `medium` / `high`

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
