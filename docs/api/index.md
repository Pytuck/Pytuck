# Pytuck API 参考文档

本目录包含 Pytuck 库的完整 API 参考文档，旨在让使用者无需阅读源码即可高效使用本库。

> [!IMPORTANT]
> Pytuck 是纯 Python 嵌入式数据库，适合**中小规模数据**和**受限环境**。大数据量或高并发场景请使用 SQLAlchemy + SQLite/PostgreSQL 等成熟方案。详见 [最佳实践 - 适用场景与限制](best-practices.md)。

## 文档索引

| 文档 | 内容 |
|------|------|
| [模型定义](models.md) | `Column`、`PureBaseModel`、`CRUDBaseModel`、`declarative_base()`、`Relationship` |
| [存储引擎](storage.md) | `Storage` 类的完整 API（CRUD、表管理、事务、持久化） |
| [会话管理](session.md) | `Session` 类（执行语句、对象状态追踪、事务、Schema 操作） |
| [查询系统](query.md) | `select`/`insert`/`update`/`delete` 语句、`Query` 构建器、`Result` 结果集、逻辑操作符 |
| [引擎对比与特性](engines.md) | 八种引擎的特性、限制、选型建议、配置示例 |
| [配置选项](options.md) | 所有 `BackendOptions`、`SyncOptions`、`ConnectorOptions` 的字段说明 |
| [异常体系](exceptions.md) | 异常层次结构与每个异常的触发场景 |
| [工具与扩展](tools.md) | 数据迁移、事件钩子、关系预取、类型系统 |
| [最佳实践](best-practices.md) | 持久化策略、引擎选型、性能优化、常见陷阱 |
| [性能基准报告](../guide/benchmark.md) | 最新 benchmark 结果、测试环境与复现命令 |
| [开发与发布指南](../guide/development.md) | 安装细节、uv 工作流、贡献开发与打包发布 |

## 快速导入参考

```python
# 核心 API（最常用）
from pytuck import (
    Storage, Session, Column, declarative_base,
    PureBaseModel, CRUDBaseModel,
    select, insert, update, delete,
    or_, and_, not_,
    event, prefetch,
    Query, BinaryExpression, Result, CursorResult,
    SyncOptions, SyncResult,
)

# 配置选项
from pytuck.common.options import (
    BinaryBackendOptions, JsonBackendOptions, CsvBackendOptions,
    SqliteBackendOptions, DuckdbBackendOptions,
    DuckdbConnectorOptions, ExcelBackendOptions, XmlBackendOptions,
)

# 异常
from pytuck import (
    PytuckException, TableNotFoundError, RecordNotFoundError,
    DuplicateKeyError, ValidationError, QueryError,
    # ... 更多异常见 exceptions.md
)

# 迁移工具（不从根包导出，需单独导入）
from pytuck.tools.migrate import migrate_engine, import_from_database

# 关联关系
from pytuck.core.orm import Relationship
```

## 版本

当前版本：`1.2.0`

## 支持的 Python 版本

Python 3.7+
