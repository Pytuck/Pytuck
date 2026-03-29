# Pytuck 性能基准报告

本文档汇总当前仓库最新一次 benchmark 结果，作为 README 首页之外的详细性能参考。

> 测试时间：2026-03-29 20:37:35
>
> 测试环境：Linux 6.18.7-76061807-generic / Python 3.12.3
>
> 数据规模：100000 条记录（扩展测试）

## 测试范围

本次扩展测试覆盖以下引擎：

- `pytuck`
- `json`
- `jsonl`
- `csv`
- `sqlite`
- `duckdb`
- `excel`
- `xml`

扩展模式包含以下指标：

- 插入
- 全表查询
- 索引查询（100 次）
- 非索引查询（100 次）
- 范围查询
- 批量读取（1000 条）
- 更新 / 删除
- 保存 / 加载
- `pytuck` 懒加载打开与首次查询
- 文件体积

## 100000 条记录扩展 benchmark

| 引擎 | 插入 | 索引查询 | 非索引查询 | 索引加速 | 范围查询 | 保存 | 加载 | 懒加载 | 文件大小 |
|------|------|----------|------------|----------|----------|------|------|--------|----------|
| Pytuck | 834.38ms | 1.88ms | 8.34s | 4568x | 430.40ms | 562.03ms | 337.28ms | 321.98ms | 6.09MB |
| JSON | 899.31ms | 1.78ms | 8.49s | 5046x | 438.08ms | 310.39ms | 394.28ms | - | 10.70MB |
| JSONL | 909.78ms | 1.76ms | 8.28s | 4583x | 422.87ms | 604.40ms | 570.72ms | - | 827.5KB |
| CSV | 909.20ms | 1.79ms | 8.26s | 4702x | 435.74ms | 462.06ms | 524.71ms | - | 731.9KB |
| SQLite | 1.53s | 4.25ms | 489.70ms | 115x | 525.26ms | 2.91ms | 389.5μs | - | 6.97MB |
| DuckDB | 1.52s | 56.62ms | 190.30ms | 3x | 482.98ms | 7.52ms | 29.24ms | - | 12.0KB |
| Excel | 785.61ms | 1.95ms | 8.49s | 4528x | 427.10ms | 5.81s | 7.64s | - | 2.84MB |
| XML | 771.45ms | 1.77ms | 8.20s | 4617x | 432.99ms | 2.26s | 1.93s | - | 34.54MB |

## 结果解读

### Pytuck

- 在 100000 条记录下，插入约 `786.38ms`，整体仍保持在纯 Python 文件引擎中的第一梯队。
- 懒加载打开约 `316.76ms`，首次懒查询仅 `121.6μs`，说明默认 lazy reopen 路径已经具备较好的按需读取能力。
- 非索引查询仍需要扫描，`8.34s` 属于正常表现；一旦命中索引，100 次查询仅 `1.83ms`。

### JSON / JSONL / CSV

- 三者在内存查询阶段表现接近，因为主要差异集中在序列化格式与持久化路径。
- `CSV` / `JSONL` 文件体积明显更小，适合交换和归档场景。
- `JSON` 保存更快，但体积最大，优势主要是可读性与调试便利。

### SQLite

- `SQLite` 的磁盘保存和重新加载速度明显领先，适合强调稳定 SQL 写路径和快速 reopen 的场景。
- 非索引查询远快于纯内存扫描型引擎，因为原生 SQL 路径能更高效地处理过滤。
- 插入性能仍慢于 `pytuck` / `json` / `csv` 等纯内存写入后统一落盘的路径。

### DuckDB

- `DuckDB` 经过 Session 插入缓冲 + COPY FROM CSV 快速批量插入 + 事务包裹优化后，100k 插入从 `277.18s` 大幅降至 `1.52s`，与 SQLite (`1.53s`) 基本持平。
- reopen 和查询能力依旧很强，推荐用于分析查询、已有 DuckDB 文件接入和原生 SQL 场景。

### Excel / XML

- `Excel` 和 `XML` 作为交换 / 办公 / 可读性导向格式仍可用，但大数据量持久化和加载成本明显更高。
- `Excel` 的保存与加载都较慢；`XML` 文件体积最大。

## 加密 benchmark

下表保留本次重新运行的加密 benchmark 结果，用于观察 `pytuck` 不同加密等级与 CSV ZIP 密码保护的成本变化。

### 1000 条记录

| 场景 | 保存 | 加载 | 文件大小 |
|------|------|------|----------|
| Pytuck none | 22.64ms | 24.76ms | 131.7KB |
| Pytuck low | 21.18ms | 38.92ms | 131.7KB |
| Pytuck medium | 55.12ms | 89.72ms | 131.7KB |
| Pytuck high | 212.14ms | 416.48ms | 131.7KB |
| CSV none | 12.73ms | 15.15ms | 13.9KB |
| CSV password | 24.55ms | 25.08ms | 13.9KB |

### 5000 条记录

| 场景 | 保存 | 加载 | 文件大小 |
|------|------|------|----------|
| Pytuck none | 170.94ms | 121.90ms | 679.2KB |
| Pytuck low | 334.89ms | 204.17ms | 679.2KB |
| Pytuck medium | 845.87ms | 457.10ms | 679.2KB |
| Pytuck high | 3.25s | 2.10s | 679.2KB |
| CSV none | 73.99ms | 98.42ms | 78.4KB |
| CSV password | 165.96ms | 142.43ms | 78.4KB |

### 10000 条记录

| 场景 | 保存 | 加载 | 文件大小 |
|------|------|------|----------|
| Pytuck none | 402.87ms | 257.25ms | 1.33MB |
| Pytuck low | 1.07s | 400.37ms | 1.33MB |
| Pytuck medium | 2.96s | 938.03ms | 1.33MB |
| Pytuck high | 11.74s | 4.26s | 1.33MB |
| CSV none | 177.89ms | 233.68ms | 207.1KB |
| CSV password | 413.95ms | 400.64ms | 207.2KB |

## 复现命令

```bash
uv run python tests/benchmark/benchmark.py -n 100000 --extended --output-json /tmp/pytuck-benchmark.json
uv run python tests/benchmark/benchmark_encryption.py
```

## 相关文档

- [README 首页](../../README.md)
- [引擎对比与特性](../api/engines.md)
- [最佳实践](../api/best-practices.md)
- [开发与发布指南](./development.md)
