# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [1.1.0] - 2026-03-29

### 新增

- **DuckDB 批量插入优化**
  - Session 插入缓冲区：逐条 `INSERT` 自动缓冲，`commit()` 时批量提交
  - DuckDB 引擎新增 `COPY FROM CSV` 快速批量插入路径，100k 插入从 `277s` 降至 `1.5s`
  - native SQL 模式事务包裹 + `bulk_insert` 批量化，与 SQLite 插入性能持平

- **JSONL 引擎增量保存**
  - 参考 CSV 引擎增量方案，`save()` 拆分为 `_save_full()` + `_save_incremental()`
  - 多表场景下未变更的表直接从旧 ZIP 复制压缩字节，避免全量序列化
  - 加密 ZIP 自动回退全量保存，API 完全向后兼容

- **懒加载表完整记录访问**
  - 懒加载模式下支持 `len(table)`、`iter(table)` 等完整记录访问操作
  - 首次访问时自动从磁盘加载全部记录，后续操作与内存模式一致

### 修复

- **DuckDB WAL 未写入主文件**
  - DuckDB 原生 SQL 模式下 `commit()` 后数据留在 WAL 文件中，主数据库文件仅含 schema（~12KB）
  - 新增 `DuckDBConnector.checkpoint()` 方法，`flush()` 和 `close()` 时自动执行 `CHECKPOINT`
  - 修复后 100k 记录文件大小从 `12KB` 恢复为 `6.76MB`

- **SQLite `insert_records` 特殊类型处理**
  - `executemany` 批量插入时 `datetime` / `timedelta` / `list` / `dict` 等类型未经序列化，导致写入失败
  - 统一通过 `_serialize_value()` 处理所有字段值

- **DuckDB `rollback_transaction` 无活跃事务报错**
  - `CHECKPOINT` 结束事务后 `session.close()` 中的 rollback 抛出 `TransactionException`
  - `rollback_transaction()` 现在安全忽略"无活跃事务"异常

### 改进

- **README 文档拆分**
  - README 首页精简为项目定位、安装与最小示例
  - 详细说明拆分到 `docs/api/`（API 文档）与 `docs/guide/`（指南与 benchmark）

- **示例代码整理**
  - 重命名 `new_api_demo.py` → `session_api_demo.py`，命名更清晰
  - 所有示例添加 `if __name__ == '__main__'` 入口保护
  - 修复 `_common.py` 路径拼接和 `json_impl_demo.py` 异常捕获问题

### 测试

- 新增全引擎持久化完整性测试（500 条记录 flush→文件大小合理性→reopen→记录数+数据验证）
- 新增全引擎 flush-then-reopen 测试（flush 后直接 reopen 验证数据已写入文件）
- SQLite 中文列名用例从永久跳过改为 SQLite 兼容模式执行
- 优化 Pytuck 引擎测试以支持懒加载逻辑

### 性能基准（100k 记录）

| 引擎 | 插入 | 保存 | 加载 | 文件大小 |
|------|------|------|------|----------|
| DuckDB | 1.52s | 86.23ms | 29.24ms | 6.76MB |
| SQLite | 1.53s | 2.91ms | 389.5μs | 6.97MB |
| Pytuck | 834.38ms | 562.03ms | 337.28ms | 6.09MB |

> 完整 benchmark 见 [docs/guide/benchmark.md](./docs/guide/benchmark.md)
