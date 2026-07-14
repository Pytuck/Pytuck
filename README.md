# Pytuck - 轻量级 Python 文档数据库

<div align="center">
  <img src="https://raw.githubusercontent.com/Pytuck/Pytuck/master/logo.svg" width="120" alt="Pytuck logo">
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

- **Pytuck**：默认单文件引擎，零依赖，适合嵌入式与受限环境，当前新写入支持无加密 / `low` / `medium` / `high`；加密文件带 HMAC-SHA256 完整性认证，并兼容读取旧版 PTK7 加密文件

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
