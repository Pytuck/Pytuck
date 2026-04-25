# Pytuck - 轻量级 Python 文档数据库

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

中文 | [English](README.EN.md)

纯 Python 实现的轻量级文档数据库，支持多种存储引擎，无 SQL，通过对象和方法管理数据。

> **设计初衷**：为 Ren'Py 等阉割版 Python 环境提供零依赖的关系型数据库方案，让任何受限环境都能享受 SQLAlchemy 风格的 Pythonic 数据操作体验。

> [!IMPORTANT]
> **适用场景说明**：Pytuck 是纯 Python 实现的嵌入式数据库，专为**中小规模数据**和**受限环境**设计。
> - **数据量建议**：这里的“万级 / 十万级”主要按**单张热点表**记录数衡量。万级记录以内体验最佳；当单表接近或超过 10 万条时，优先使用 DuckDB / SQLite 引擎或评估其他方案，多表总量继续增长时也要同步关注整体 I/O 与加载时间
> - **性能定位**：纯 Python 实现意味着性能无法与 C 扩展数据库（如 SQLite、PostgreSQL）相比，不适合高并发或计算密集型场景
> - **并发限制**：定位单进程嵌入式数据库，不支持多进程并发访问
> - **如果你的环境没有特殊限制**，建议优先考虑 [SQLAlchemy](https://www.sqlalchemy.org/) + SQLite/PostgreSQL 等成熟方案，它们拥有更好的性能、更完善的生态和更广泛的社区支持

## 仓库镜像

- **GitHub**: https://github.com/Pytuck/Pytuck
- **Gitee**: https://gitee.com/Pytuck/Pytuck

## 核心特性

- **无 SQL 设计**：完全通过 Python 对象和方法操作数据
- **多引擎支持**：支持 Pytuck、JSON、JSONL、CSV、SQLite、DuckDB、Excel、XML
- **插件化架构**：默认零依赖，可选引擎按需安装
- **SQLAlchemy 2.0 风格 API**：支持 `select()` / `insert()` / `update()` / `delete()`
- **泛型类型提示**：IDE 和类型检查器可精确推断模型类型
- **索引优化**：哈希索引与有序索引自动参与等值查询、范围查询与排序
- **关系与预取**：支持 `Relationship` 和 `prefetch()`，缓解 N+1 问题
- **类型安全**：内置类型转换、严格模式、自定义 `validator`
- **可选持久化策略**：支持手动 `flush()` 与 `auto_flush=True`

## 近期重点更新

相较上一个公开版本，当前文档建议优先关注以下三点：

- **JSON / JSONL 文档与实现已不再包含 `ujson` 支持**：当前官方内置路径收敛为标准库 `json` 与可选 `orjson`，以减少实现分叉与行为差异
- **`Storage.flush()` 增加多线程写锁保护**：用于降低同一 `Storage` 实例在多线程场景下并发写盘时的竞态风险；这不改变项目“单进程嵌入式数据库”的总体定位
- **`Relationship` / `prefetch()` 支持跨 storage 关联加载**：适合“基础库 + 用户库”这类分库场景，且两个文件可以使用不同引擎；Pytuck 仍然**不支持 join**，跨表读取依旧依赖 `Relationship` 或分开查询后自行组合

## 文档导航

README 首页现在只保留项目定位、安装与最小上手示例；详细说明已拆分到 `docs/`：

| 文档 | 内容 |
|------|------|
| [API 文档索引](./docs/api/index.md) | API 总览与文档入口 |
| [引擎对比与配置](./docs/api/engines.md) | 各引擎特性、配置、限制与选型建议 |
| [最佳实践](./docs/api/best-practices.md) | 持久化、索引、事务、性能优化 |
| [Storage API](./docs/api/storage.md) | `Storage` / `Table` / `flush()` / `transaction()` |
| [Session API](./docs/api/session.md) | `Session`、事务、对象状态管理 |
| [查询系统](./docs/api/query.md) | `select` / `insert` / `update` / `delete` 与结果集 |
| [工具与迁移](./docs/api/tools.md) | `migrate_engine()`、`import_from_database()`、benchmark 脚本、事件钩子、prefetch |
| [性能基准报告](./docs/guide/benchmark.md) | 最新 benchmark 结果与复现命令 |
| [开发与发布指南](./docs/guide/development.md) | 安装细节、uv 工作流、贡献开发、打包发布 |
| [开发 TODO](./TODO.md) | 当前开发计划与路线图 |
| [版本记录](./CHANGELOG.md) | 最新变更与历史归档入口 |

## 快速开始

### 安装

```bash
# 基础安装（已包含 pytuck / json / jsonl / csv / sqlite，零外部依赖）
pip install pytuck

# 安装可选引擎 / 加速依赖
pip install pytuck[duckdb]  # DuckDB 引擎（需要 duckdb）
pip install pytuck[excel]   # Excel 引擎（需要 openpyxl）
pip install pytuck[xml]     # XML 引擎（需要 lxml）
pip install pytuck[orjson]  # JSON / JSONL 可选加速

# 安装所有可选依赖
pip install pytuck[all]

# 开发环境
pip install pytuck[dev]
```

### 基础使用

Pytuck 提供两种常见使用模式：

#### 模式 1：纯模型模式（默认，推荐）

```python
from typing import Type
from pytuck import Storage, declarative_base, Session, Column
from pytuck import PureBaseModel, select, insert

# 创建数据库（默认 Pytuck 引擎）
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

# 默认 auto_flush=False，显式 flush/close 后才写入磁盘
db.flush()
db.close()
```

#### 模式 2：Active Record 模式

```python
from typing import Type
from pytuck import Storage, declarative_base, Column
from pytuck import CRUDBaseModel

# 创建数据库
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

**如何选择？**
- **纯模型模式**：适合大型项目、团队开发、需要清晰的数据访问层分离
- **Active Record 模式**：适合小型项目、快速原型、简单 CRUD 操作

> **持久化提醒**：默认 `auto_flush=False`。`session.commit()` / `Model.save()` 默认只把数据提交到内存，直到 `db.flush()` 或 `db.close()` 才真正写入磁盘。更多说明见 [最佳实践 - 持久化策略](./docs/api/best-practices.md#持久化策略)。

## 存储引擎速览

- **Pytuck**：默认单文件引擎，零依赖，适合嵌入式与受限环境，当前新写入支持无加密 / `low` / `medium` / `high`

> **Pytuck 说明**：默认单文件路径当前更强调长期格式稳定、单文件持久化，以及打开 / 重开 / 主键点查体验；它不是“所有 benchmark 维度都领先”的通用最快引擎。如果你更看重原生 SQL、超大数据集或某些极端跑分，优先考虑 SQLite / DuckDB。
- **JSON**：适合调试、配置存储、可读性优先
- **JSONL**：适合多表文本归档、逐行交换、ZIP 容器分发表
- **CSV**：适合最小体积、表格交换、与其他工具共享
- **SQLite**：适合稳定 SQL 写路径、事务与快速加载
- **DuckDB**：适合分析查询、DuckDB 生态集成、多 schema 场景
- **Excel**：适合可视化编辑、报表与办公交付
- **XML**：适合标准化交换与企业集成

> **SQLite 特别说明**：`use_native_sql=True`（默认）时更接近原生 SQLite 行为，对中文列名等特殊标识符支持有限；如果需要 `Column.name='用户名'` 这类列名，可切换到 `SqliteBackendOptions(use_native_sql=False)` 兼容模式。详见 [docs/api/engines.md](./docs/api/engines.md#sqlite-引擎)。

## 性能与 benchmark

- 最新多引擎 benchmark 结果见 [docs/guide/benchmark.md](./docs/guide/benchmark.md)
- `json` / `jsonl` 下标准库 `json` 与 `orjson` 的专项对比也已补到同一文档；当前 `100000` 条记录口径下，`orjson` 在这两种文本引擎上的 `save` / `load` / `reopen` 都有稳定收益
- benchmark 文档汇总了各引擎在插入、索引查询、非索引查询、范围查询、保存、加载与文件体积上的直观对比
- 对 Session 写入路径，当前同机 100k 内存基线约为：`session.add_all() + commit()` `0.72s`，`session.bulk_insert()` `0.41s`；前者保留逐条 `before_insert` / `after_insert` 语义，后者提供最高吞吐
- benchmark 脚本说明见 [docs/api/tools.md](./docs/api/tools.md#benchmark-脚本)
- 如需在本机复现：

```bash
uv run python tests/benchmark/benchmark.py -n 100000 --extended --output-json /tmp/pytuck-benchmark.json
```

## 数据迁移

在不同引擎之间迁移数据：

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

也支持从 SQLite / DuckDB 等外部数据库导入现有数据到 Pytuck 支持的目标引擎。

更多迁移与导入说明见 [docs/api/tools.md](./docs/api/tools.md#数据迁移工具)。

## 项目状态与更多说明

- **详细路线图**：见 [TODO.md](./TODO.md)
- **版本变更**：见 [CHANGELOG.md](./CHANGELOG.md) 与 [docs/changelog/](./docs/changelog/)
- **完整 API 文档**：见 [docs/api/index.md](./docs/api/index.md)
- **开发与发布流程**：见 [docs/guide/development.md](./docs/guide/development.md)

## 示例代码

查看 `examples/` 目录获取更多示例：

- `sqlalchemy20_api_demo.py` - SQLAlchemy 2.0 风格 API 完整示例（推荐）
- `active_record_demo.py` - Active Record 模式示例
- `new_api_demo.py` - 纯模型模式示例
- `migration_tools_demo.py` - 数据迁移工具演示

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 致谢

灵感来自于 SQLAlchemy 和 TinyDB。
