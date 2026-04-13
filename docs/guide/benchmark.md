# Pytuck 性能基准报告

本文档汇总当前仓库最新一次多引擎 benchmark 结果，作为 README 首页之外的详细性能参考。

> 测试时间：2026-04-13 23:26:40
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

主表统计的指标包括：

- 插入
- 主键查询（100 次）
- 索引查询（100 次）
- 非索引查询（100 次）
- 索引加速比
- 范围查询
- 保存
- 加载
- 重开
- 重开后首次查询
- 文件大小

> [!IMPORTANT]
> README 与本页主表都以 `tests/benchmark/benchmark.py` 的多引擎结果为准。`benchmark_encryption.py` 仅用于补充观察加密路径，不参与这张多引擎主表。

## 100000 条记录扩展 benchmark

| 引擎 | 插入 | 主键查询 | 索引查询 | 非索引查询 | 索引加速 | 范围查询 | 保存 | 加载 | 重开 | 首次查询 | 文件大小 |
|------|------|----------|----------|------------|----------|----------|------|------|------|----------|----------|
| Pytuck | 864.88ms | 1.67ms | 1.86ms | 7.99s | 4295x | 431.08ms | 617.42ms | 126.97ms | 131.55ms | 51.7μs | 9.51MB |
| JSON | 839.62ms | 137.8μs | 1.91ms | 8.15s | 4263x | 418.37ms | 287.07ms | 326.25ms | 388.65ms | 9.5μs | 10.70MB |
| JSONL | 837.14ms | 140.4μs | 1.80ms | 8.10s | 4504x | 426.50ms | 579.55ms | 488.79ms | 545.59ms | 8.5μs | 827.5KB |
| CSV | 858.79ms | 126.0μs | 1.85ms | 8.29s | 4490x | 425.67ms | 445.29ms | 467.82ms | 532.19ms | 7.1μs | 731.9KB |
| SQLite | 1.39s | 997.6μs | 4.20ms | 489.44ms | 116x | 511.72ms | 3.01ms | 286.4μs | 279.4μs | 41.5μs | 6.97MB |
| DuckDB | 1.45s | 52.88ms | 55.34ms | 93.91ms | 2x | 482.28ms | 85.50ms | 26.04ms | 15.69ms | 864.8μs | 6.76MB |
| Excel | 784.91ms | 152.1μs | 1.85ms | 8.41s | 4543x | 450.76ms | 5.47s | 7.48s | 7.27s | 9.2μs | 2.84MB |
| XML | 769.28ms | 154.4μs | 1.83ms | 8.13s | 4447x | 430.64ms | 2.34s | 1.94s | 1.97s | 10.9μs | 34.54MB |

## 结果解读

### Pytuck

- 作为默认单文件引擎，`insert` 为 `864.88ms`，`load` 为 `126.97ms`，`reopen` 为 `131.55ms`，在纯 Python 文件引擎里保持了比较均衡的表现。
- `主键查询` 与 `索引查询` 都维持在毫秒级，适合需要完整类型保留和零依赖单文件存储的场景。
- 代价是文件体积达到 `9.51MB`，明显大于 `CSV` / `JSONL` 这类交换型格式。

### JSON / JSONL / CSV

- 这三类文本引擎在 `insert`、`索引查询`、`范围查询` 上表现接近，适合可读性、交换和归档场景。
- `JSON` 的 `save` 最快，但文件体积也最大（`10.70MB`）。
- `JSONL` 与 `CSV` 的体积最小，尤其适合交换与归档；代价是 `load` / `reopen` 明显慢于 Pytuck、SQLite 和 DuckDB。

### SQLite

- `save`、`load`、`reopen` 都明显领先：分别为 `3.01ms`、`286.4μs`、`279.4μs`。
- `非索引查询` 仅 `489.44ms`，显著快于纯扫描型文件引擎，适合需要原生 SQL、事务和快速 reopen 的场景。
- `insert` 为 `1.39s`，比 Pytuck / JSON / CSV 略慢，但整体读写体验非常稳定。

### DuckDB

- `非索引查询` 为 `93.91ms`，`load` 为 `26.04ms`，`reopen` 为 `15.69ms`，很适合分析型查询和已有 DuckDB 工作流。
- 在这组 benchmark 中，`索引查询` 与 `主键查询` 并不是它的强项，因此更适合作为分析与 SQL 引擎，而不是小对象高频点查引擎。

### Excel / XML

- `Excel` 与 `XML` 更偏向办公互操作和结构化交换，而不是高频持久化。
- `Excel` 的 `save` / `load` / `reopen` 分别达到 `5.47s` / `7.48s` / `7.27s`；`XML` 也有 `2.34s` / `1.94s` / `1.97s`，更适合导出、交付和集成场景。

## 如何阅读这张表

- 如果你更看重**默认单文件体验、类型保留、零依赖**，优先看 `Pytuck`。
- 如果你更看重**可读性与调试便利**，优先看 `JSON`。
- 如果你更看重**小体积归档或交换**，优先看 `JSONL` / `CSV`。
- 如果你更看重**原生 SQL、事务与快速重开**，优先看 `SQLite`。
- 如果你更看重**分析查询和 DuckDB 生态**，优先看 `DuckDB`。
- 如果你需要**办公软件交付或标准化结构交换**，再考虑 `Excel` / `XML`。

## 复现命令

```bash
# 跑完整多引擎扩展 benchmark
uv run python tests/benchmark/benchmark.py -n 100000 -e pytuck json jsonl csv sqlite duckdb excel xml --extended --output-json /tmp/pytuck-benchmark.json

# 只看单个引擎
uv run python tests/benchmark/benchmark.py -e pytuck -n 100000 --extended --output-json /tmp/pytuck.json
```

## 相关文档

- [README 首页](../../README.md)
- [引擎对比与特性](../api/engines.md)
- [最佳实践](../api/best-practices.md)
- [工具与扩展 API](../api/tools.md)
