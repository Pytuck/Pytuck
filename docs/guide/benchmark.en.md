# Pytuck Benchmark Report

This document keeps the latest benchmark results outside the README home page, so the README can stay focused on positioning and quick start guidance.

> Test time: 2026-03-29 17:09:41
>
> Environment: Linux 6.18.7-76061807-generic / Python 3.12.3
>
> Dataset: 100000 records (extended benchmark)

## Coverage

This extended run covers the following engines:

- `pytuck`
- `json`
- `jsonl`
- `csv`
- `sqlite`
- `duckdb`
- `excel`
- `xml`

The extended mode includes:

- insert
- full table query
- indexed query (100 runs)
- non-indexed query (100 runs)
- range query
- batch read (1000 rows)
- update / delete
- save / load
- `pytuck` lazy reopen and first lazy query
- file size

## 100000-record extended benchmark

| Engine | Insert | Indexed | Non-Indexed | Speedup | Range | Save | Load | Lazy | Size |
|--------|--------|---------|-------------|---------|-------|------|------|------|------|
| Pytuck | 786.38ms | 1.83ms | 8.34s | 4568x | 430.40ms | 543.59ms | 321.59ms | 316.76ms | 6.09MB |
| JSON | 878.75ms | 1.68ms | 8.49s | 5046x | 438.08ms | 290.43ms | 380.68ms | - | 10.70MB |
| JSONL | 864.12ms | 1.81ms | 8.28s | 4583x | 422.87ms | 591.97ms | 531.75ms | - | 827.5KB |
| CSV | 859.28ms | 1.76ms | 8.26s | 4702x | 435.74ms | 453.77ms | 571.33ms | - | 731.9KB |
| SQLite | 2.10s | 4.27ms | 489.70ms | 115x | 525.26ms | 13.95ms | 348.5μs | - | 6.97MB |
| DuckDB | 277.18s | 59.88ms | 190.30ms | 3x | 482.98ms | 18.39ms | 26.66ms | - | 4.76MB |
| Excel | 789.34ms | 1.88ms | 8.49s | 4528x | 427.10ms | 5.56s | 7.49s | - | 2.84MB |
| XML | 775.03ms | 1.78ms | 8.20s | 4617x | 432.99ms | 2.30s | 1.95s | - | 34.54MB |

## Notes

### Pytuck

- At 100000 records, insert is about `786.38ms`, which keeps `pytuck` in the top tier among the pure Python file engines in this repository.
- Lazy reopen is about `316.76ms`, and the first lazy query is only `121.6μs`, which is a good sign that the new default lazy reopen path is working as intended.
- Non-indexed queries still scan, so `8.34s` is expected; once the query hits an index, 100 lookups take only `1.83ms`.

### JSON / JSONL / CSV

- These three engines behave similarly during in-memory query phases because the main differences are in serialization format and persistence path.
- `CSV` and `JSONL` keep disk usage much smaller, which makes them attractive for interchange and archival workflows.
- `JSON` saves faster, but is the largest on disk; its main strength remains readability and easy debugging.

### SQLite

- `SQLite` is clearly ahead for save and reopen latency, which matches its role as the best fit for stable SQL write paths and fast reopen behavior.
- Non-indexed queries are much faster than the scan-based pure in-memory paths because native SQL can filter more efficiently.
- Insert is still slower than `pytuck`, `json`, and `csv`, which benefit from in-memory writes followed by a coordinated flush.

### DuckDB

- `DuckDB` still reopens and queries quickly, but the current ORM / Session row-by-row write path performs very poorly for insert benchmark: `277.18s`.
- That is why `TODO.md` still keeps the `duckdb` optimization task open.
- In the current implementation, `duckdb` is better suited to analytical queries, existing DuckDB files, and native SQL workflows than high-frequency ORM bulk writes.

### Excel / XML

- `Excel` and `XML` remain useful for interchange, office workflows, and human-readable exports, but their persistence cost is much higher at this dataset size.
- `Excel` is slow to save and reload; `XML` produces the largest files.

## Encryption benchmark

The following tables preserve the encryption benchmark that was rerun in this session, so the detailed numbers do not need to live in the README.

### 1000 records

| Scenario | Save | Load | Size |
|----------|------|------|------|
| Pytuck none | 22.64ms | 24.76ms | 131.7KB |
| Pytuck low | 21.18ms | 38.92ms | 131.7KB |
| Pytuck medium | 55.12ms | 89.72ms | 131.7KB |
| Pytuck high | 212.14ms | 416.48ms | 131.7KB |
| CSV none | 12.73ms | 15.15ms | 13.9KB |
| CSV password | 24.55ms | 25.08ms | 13.9KB |

### 5000 records

| Scenario | Save | Load | Size |
|----------|------|------|------|
| Pytuck none | 170.94ms | 121.90ms | 679.2KB |
| Pytuck low | 334.89ms | 204.17ms | 679.2KB |
| Pytuck medium | 845.87ms | 457.10ms | 679.2KB |
| Pytuck high | 3.25s | 2.10s | 679.2KB |
| CSV none | 73.99ms | 98.42ms | 78.4KB |
| CSV password | 165.96ms | 142.43ms | 78.4KB |

### 10000 records

| Scenario | Save | Load | Size |
|----------|------|------|------|
| Pytuck none | 402.87ms | 257.25ms | 1.33MB |
| Pytuck low | 1.07s | 400.37ms | 1.33MB |
| Pytuck medium | 2.96s | 938.03ms | 1.33MB |
| Pytuck high | 11.74s | 4.26s | 1.33MB |
| CSV none | 177.89ms | 233.68ms | 207.1KB |
| CSV password | 413.95ms | 400.64ms | 207.2KB |

## Reproduction

```bash
uv run python tests/benchmark/benchmark.py -n 100000 --extended --output-json /tmp/pytuck-benchmark.json
uv run python tests/benchmark/benchmark_encryption.py
```

## Related docs

- [README home page](../../README.EN.md)
- [Engine comparison](../api/engines.md)
- [Best practices](../api/best-practices.md)
- [Development and release guide](./development.en.md)
