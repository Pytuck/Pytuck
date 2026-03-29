# Pytuck 开发待办清单

本文件记录 Pytuck 项目的详细开发计划，供开发者参考。

> 版本发布记录请查看：[CHANGELOG.md](./CHANGELOG.md) | [历史版本](./docs/changelog/)

---

## 已完成

- [x] 核心 ORM 和内存存储
- [x] 插件化多引擎持久化（Pytuck、JSON、JSONL、CSV、SQLite、DuckDB、Excel、XML）
- [x] Pytuck 单文件引擎正式更名与格式切换（`binary` → `pytuck`、`.db` → `.pytuck`、仅支持 PTK5）
- [x] DuckDB 原生后端（多 schema、原生 SQL、原生注释、服务端分页）
- [x] JSONL 文件后端（ZIP 容器、每表 `.jsonl`、统一 `_metadata.json`）
- [x] SQLAlchemy 2.0 风格 API（select、insert、update、delete）
- [x] 基础事务支持
- [x] Identity Map（对象唯一性管理）
- [x] 自动脏跟踪（Dirty Tracking）
- [x] merge() 操作
- [x] 统一数据库连接器架构（pytuck/connectors/）
- [x] 数据迁移工具（migrate_engine、import_from_database）
- [x] 统一引擎版本管理（pytuck/backends/versions.py）
- [x] 表和列备注支持（comment 参数）
- [x] 泛型类型提示系统
- [x] 强类型配置选项系统（dataclass 替代 **kwargs）
- [x] Schema 同步与迁移功能（SyncOptions、SyncResult、三层 API）
- [x] Excel 行号映射功能（row_number_mapping）
- [x] SQLite 原生 SQL 模式优化
- [x] 异常系统重构（统一异常层次结构）
- [x] 后端自动注册机制（__init_subclass__）
- [x] 查询结果 API 简化（移除 scalars() 中间层）
- [x] 迁移工具延迟加载后端支持
- [x] 无主键模型支持（使用内部隐式 `_pytuck_rowid`）
- [x] 逻辑组合查询 OR/AND/NOT（`or_()`, `and_()`, `not_()`）
- [x] 外部文件加载功能 load_table（CSV/Excel → 模型对象列表）
- [x] ORM 事件钩子（Model 级 + Storage 级事件回调）
- [x] 关系预取 API（prefetch，批量加载关联数据解决 N+1 问题）
- [x] 查询索引优化（SortedIndex 范围查询加速 + order_by 索引排序 + Column 索引类型指定）
- [x] 批量操作优化（`bulk_insert` / `bulk_update`，批量主键分配 + 批量索引更新 + 批量事件）

---

## 近期计划

- [x] **Pytuck 单文件引擎按需查询优化**
  - 以 PTK5 / `.pytuck` 作为稳定格式继续演进，不再维护 v4 兼容分支
  - 在现有懒加载基础上继续强化按需查询 / 非全量加载能力
  - 优先保证数据准确与安全，其次性能，最后才是体积
  - 持续评估 data / index / WAL 的体积优化空间
- [ ] **jsonl 文件读写性能优化**：可参考csv引擎的优化方案，增量追加
- [ ] **duckdb 引擎优化**：可查看 `docs/guide/benchmark.md` 中的性能基准结果，`duckdb` 实现的插入性能非常慢，需要优化
- [x] **readme文档拆分**：README 首页现在聚焦项目定位、安装与最小上手示例，详细说明已拆分到 `docs/api/` 与 `docs/guide/`，兼顾首页入口与可维护性

---

## 中期计划

- [ ] **Pytuck 单格式精简库**
  - 复用同一 PTK5 / `.pytuck` 文件格式
  - 保留与 Pytuck ORM 兼容的核心 API 面
  - 舍弃多引擎、tools 等无关代码
  - 目标是尽量只改 import 即可切换

- [x] **to_dict() 增强**
  - 支持 `include` / `exclude` 字段筛选
  - 支持控制关联数据的序列化深度（`depth=1` 只展开一层 relationship）
  - 对接 JSON 序列化的常见需求（`to_json()` 方法）

- [x] **Column 级数据校验器（validator）**
  - 比 `strict` 模式更灵活：自定义校验函数、值范围约束
  - API：`Column(str, validator=lambda x: len(x) <= 100)`
  - 支持单个函数或函数列表，在类型转换后执行校验

- [x] **模型继承支持**
  - 允许模型类继承以复用列定义（当前每个模型必须独立定义所有列）
  - 应用场景：基类定义 `created_at` / `updated_at` 等公共字段，子类继承复用

- [x] **非 Pytuck 后端增量保存**
  - Table 级别脏标记（`_data_dirty`、`_schema_dirty`）
  - Storage.flush() 传递 `changed_tables` 给后端
  - CSV 后端增量 ZIP 写入：未变更表直接从旧 ZIP 复制，仅重写变更表
  - 其他后端签名已扩展，行为不变（全量写入）

- [x] **Pytuck 加密懒加载兼容**
  - 三种 cipher（XOR/LCG/ChaCha20）均新增 `decrypt_at()` 方法，支持随机位置解密
  - 加密文件现在支持懒加载：加载时仅解密索引区获取 pk_offsets，读取记录时按需解密
  - 文件格式和写入流程完全不变，纯读路径优化

- [x] **临时文件安全改进**
  - 使用 `tempfile.mkstemp` 替代手动构造临时文件路径
  - 临时文件创建在目标文件同目录下，确保原子 `replace()` 在同一文件系统
  - 移除不必要的 `unlink()` + `replace()` 模式，直接用 `replace()` 原子替换

---

## 计划增加的引擎

（暂无。当前文件后端矩阵已包含 Pytuck、JSON、JSONL、CSV、SQLite、DuckDB、Excel、XML）

---

## 远期 / 可选

- [ ] **复合主键支持**（视用户需求，当前显式禁止多主键）
- [ ] **查询结果缓存**（可选的缓存机制，减少重复查询开销）
- [ ] **Pytuck-CLI** - 命令行工具（数据库管理、导入导出、Schema 迁移）
- [ ] **FastAPI 集成示例/插件**
- [ ] **Pandas DataFrame 互操作**
- [ ] **异步 API 支持**（基于 asyncio 的异步查询和事务）
- [ ] **SQLite/DuckDB 支持同时读写**：允许多个进程同时读写同一个数据库文件，避免锁冲突。
  + 示例场景：嵌入式程序正在运行，使用pytuck读写数据，另外的进程使用pytuck来对该数据库提供对外的数据读写服务，此时该服务的读写不能影响程序正常读写

---

## 技术债务

- [x] 完善单元测试覆盖率（特别是 WAL、lazy load、索引、关联关系场景）
- [x] 基准测试自动化（CI 集成，检测性能回归）
- [x] API 参考文档生成
- [x] 最佳实践指南（持久化策略选择、引擎对比建议）

---

## 生态系统

- [x] **Pytuck-view** - Web 数据浏览器（[GitHub](https://github.com/pytuck/pytuck-view) | [Gitee](https://gitee.com/pytuck/pytuck-view) | `pip install pytuck-view`）
- [ ] pytuck only（名称未定）：将本库中`pytuck`引擎单独拆分，提供更有针对性的轻量级的数据库功能
  + 和本库使用同一个格式的`pytuck v5+`引擎
  + 免去众多选择，仅支持 `pytuck` 引擎，专为针对受限Python环境使用；只保留核心功能，不再需要tools等无关模块
  + 优化 `pytuck` 引擎的使用，就像sqlite那样高性能读写，不再每次全量加载到内存、全量保存
  + 对于基本的orm使用，最好能达到仅仅更改 import 语句就能从`pytuck`库切换到新库（比如readme中的`基础使用`章节）

---

## 不做的事（设计决策）

以下功能经过评估，不纳入 Pytuck 核心开发计划：

| 功能 | 理由 |
|------|------|
| **JOIN（多表关联查询）** | 已有 Relationship 实现关联查询（延迟加载+缓存），文档数据库不需要 SQL JOIN |
| **聚合函数（COUNT/SUM/AVG 等）** | Pytuck 定位是数据读写，不做计算引擎。用户可用 Python 原生 `len()` / `sum()` / `min()` / `max()` 处理查询结果 |
| **TinyDB / PyDbLite3 / diskcache 引擎** | 与 Pytuck 功能高度重叠或偏离核心定位 |
| **Django ORM 兼容层** | 维护成本高，需求不明确 |
| **SQLite 连接池** | Pytuck 定位嵌入式单进程，连接池意义不大 |
| **跨进程文件锁 / 并发访问** | 定位单进程嵌入式数据库，受限环境（如 Ren'Py）无法使用平台特定 API |

---

**注意**：此文档为开发者内部使用，功能优先级可能根据实际情况调整。
