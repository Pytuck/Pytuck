# Pytuck Benchmark Report

This document summarizes the latest multi-engine benchmark run in the repository and serves as the detailed performance reference outside the README home page.

> Test time: 2026-04-13 23:26:40
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

The main comparison table includes:

- insert
- primary-key query (100 runs)
- indexed query (100 runs)
- non-indexed query (100 runs)
- index speedup
- range query
- save
- load
- reopen
- first query after reopen
- file size

> [!IMPORTANT]
> The README and the main table on this page both use the multi-engine results from `tests/benchmark/benchmark.py`. `benchmark_encryption.py` is only a supplemental script for observing encryption-path costs and is not used as the main multi-engine benchmark table.

## 100000-record extended benchmark

| Engine | Insert | PK Query | Indexed | Non-Indexed | Speedup | Range | Save | Load | Reopen | First Query | Size |
|--------|--------|----------|---------|-------------|---------|-------|------|------|--------|-------------|------|
| Pytuck | 864.88ms | 1.67ms | 1.86ms | 7.99s | 4295x | 431.08ms | 617.42ms | 126.97ms | 131.55ms | 51.7μs | 9.51MB |
| JSON | 839.62ms | 137.8μs | 1.91ms | 8.15s | 4263x | 418.37ms | 287.07ms | 326.25ms | 388.65ms | 9.5μs | 10.70MB |
| JSONL | 837.14ms | 140.4μs | 1.80ms | 8.10s | 4504x | 426.50ms | 579.55ms | 488.79ms | 545.59ms | 8.5μs | 827.5KB |
| CSV | 858.79ms | 126.0μs | 1.85ms | 8.29s | 4490x | 425.67ms | 445.29ms | 467.82ms | 532.19ms | 7.1μs | 731.9KB |
| SQLite | 1.39s | 997.6μs | 4.20ms | 489.44ms | 116x | 511.72ms | 3.01ms | 286.4μs | 279.4μs | 41.5μs | 6.97MB |
| DuckDB | 1.45s | 52.88ms | 55.34ms | 93.91ms | 2x | 482.28ms | 85.50ms | 26.04ms | 15.69ms | 864.8μs | 6.76MB |
| Excel | 784.91ms | 152.1μs | 1.85ms | 8.41s | 4543x | 450.76ms | 5.47s | 7.48s | 7.27s | 9.2μs | 2.84MB |
| XML | 769.28ms | 154.4μs | 1.83ms | 8.13s | 4447x | 430.64ms | 2.34s | 1.94s | 1.97s | 10.9μs | 34.54MB |

## Supplementary Session write-path benchmark

> Same machine / Python 3.12.3 / in-memory mode / 100000 records

| Path | Time | Notes |
|------|------|-------|
| `session.add_all() + session.commit()` | 0.72s | Keeps per-row `before_insert` / `after_insert` semantics, suitable when you need model hooks, identity-map registration, and per-instance state refresh |
| `session.bulk_insert()` | 0.41s | Highest throughput, does not trigger per-row insert events, suitable for pure write-throughput workloads |

- Before the optimization, the same `session.add_all() + commit()` path took about `47.59s`; it is now about `0.72s`
- The gain mainly comes from two fixes: removing the O(N²) duplicate-check bottleneck in `Session.add()`, and batching new objects in `Session.flush()` via `storage.bulk_insert()` grouped by model class

## JSON / orjson focused benchmark

> Test time: 2026-04-24 22:57:26 CST
>
> Environment: macOS-26.4.1-arm64-arm-64bit-Mach-O / Python 3.13.11
>
> Dataset: 100000 records
>
> Scope: this run compares only the `json` and `jsonl` engines under two serializer implementations: the standard-library `json` and `orjson`. It focuses on serialization-sensitive paths: `save`, `load`, `reopen`, `reopen_first_query`, and file size.

| Engine | Impl | Save | Load | Reopen | First Query After Reopen | Size |
|--------|------|------|------|--------|--------------------------|------|
| JSON | json | 154.51ms | 219.81ms | 226.54ms | 10.5μs | 20.99MB |
| JSON | orjson | 117.12ms | 184.05ms | 178.87ms | 14.2μs | 19.65MB |
| JSONL | json | 315.49ms | 326.85ms | 286.08ms | 5.2μs | 1.14MB |
| JSONL | orjson | 177.94ms | 236.22ms | 198.88ms | 5.9μs | 1.15MB |

- On the `json` engine, `orjson` is about `1.32x` faster on `save`, `1.19x` on `load`, and `1.27x` on `reopen`
- On the `jsonl` engine, the gain is larger: `orjson` is about `1.77x` faster on `save`, `1.38x` on `load`, and `1.44x` on `reopen`
- File size changes are small: `JSON + orjson` is slightly smaller than `JSON + json`, while `JSONL` stays nearly identical across implementations
- `reopen_first_query` remains in the microsecond range for all four combinations, which suggests the main difference is still in serialization/deserialization rather than primary-key lookup itself

## Notes

### Pytuck

- As the default single-file engine, `insert` is `864.88ms`, `load` is `126.97ms`, and `reopen` is `131.55ms`, which makes it one of the more balanced pure-Python file engines in this repository.
- Both primary-key lookup and indexed lookup stay in the millisecond range, which makes it a strong fit when you want full Python type fidelity, zero-dependency single-file storage, and a faster open / reopen experience.
- The current default single-file path mainly targets long-term format stability, a simpler implementation path, and read-path experience; this table should not be read as `Pytuck` leading every benchmark dimension.
- The trade-off is file size: `9.51MB`, clearly larger than exchange-oriented formats such as `CSV` and `JSONL`.

### JSON / JSONL / CSV

- These text-oriented engines are close to each other on `insert`, `indexed`, and `range` workloads, making them good fits for readability, interchange, and archival workflows.
- `JSON` has the fastest `save`, but also the largest file among the text engines (`10.70MB`).
- `JSONL` and `CSV` are by far the smallest on disk, but `load` / `reopen` are noticeably slower than Pytuck, SQLite, and DuckDB.

### SQLite

- `save`, `load`, and `reopen` are all clearly ahead at `3.01ms`, `286.4μs`, and `279.4μs`.
- `Non-Indexed` is only `489.44ms`, far faster than scan-heavy file engines, which makes SQLite a strong choice for native SQL, transactions, and fast reopen behavior.
- `insert` is `1.39s`, a bit slower than Pytuck / JSON / CSV, but the overall read/write profile is very stable.

### DuckDB

- `Non-Indexed` is `93.91ms`, `load` is `26.04ms`, and `reopen` is `15.69ms`, which makes DuckDB a very good fit for analytical queries and DuckDB-centered workflows.
- In this benchmark, `Indexed` and `PK Query` are not its strongest paths, so it is better viewed as an analytics/SQL engine than a tiny-object point-lookup engine.

### Excel / XML

- `Excel` and `XML` are better treated as office-interchange and structured-export formats rather than high-frequency persistence backends.
- `Excel` reaches `5.47s` / `7.48s` / `7.27s` for `save` / `load` / `reopen`; `XML` is also relatively heavy at `2.34s` / `1.94s` / `1.97s`.

## How to read this table

- If you care most about a **default single-file experience, type fidelity, and zero dependencies**, start with `Pytuck`.
- If you care most about **readability and debugging convenience**, start with `JSON`.
- If you care most about **small archives or interchange**, start with `JSONL` / `CSV`.
- If you care most about **native SQL, transactions, and fast reopen**, start with `SQLite`.
- If you care most about **analytics and DuckDB ecosystem workflows**, start with `DuckDB`.
- If you need **office handoff or standardized structured exchange**, consider `Excel` / `XML`.

## Raw result archival rules

- Long-lived repository archive directory: `docs/benchmark-results/`
- Multi-engine main-table raw result filename: `YYYY-MM-DD-py312-100000-extended-multi-engine.json`
- Encryption supplemental benchmark filename: `YYYY-MM-DD-py312-100000-encryption.json`
- The README and this page contain curated public conclusions; the JSON files in the repository are the raw inputs behind those tables
- The GitHub Actions artifact is named `benchmark-results-py312-5000-${GITHUB_SHA}` and is only for temporary download, not a replacement for the repository archive. Note: the workflow actually uses the `${{ github.sha }}` syntax; the CI workflow runs with `-n 5000` to produce this temporary artifact, while long-term archival runs use `-n 100000` and output results into `docs/benchmark-results/`.

### Repository archival example

```bash
uv run python tests/benchmark/benchmark.py \
  -n 100000 \
  -e pytuck json jsonl csv sqlite duckdb excel xml \
  --extended \
  --output-json docs/benchmark-results/2026-04-16-py312-100000-extended-multi-engine.json
```

## Reproduction

```bash
# Full multi-engine extended benchmark (temporary local output)
uv run python tests/benchmark/benchmark.py -n 100000 -e pytuck json jsonl csv sqlite duckdb excel xml --extended --output-json /tmp/pytuck-benchmark.json

# Single-engine run
uv run python tests/benchmark/benchmark.py -e pytuck -n 100000 --extended --output-json /tmp/pytuck.json

# Focused json vs orjson comparison for JSON / JSONL only
uv run python tests/benchmark/benchmark_json_impl.py -n 100000 --output-json /tmp/pytuck-json-impl.json
```

## Related docs

- [README home page](../../README.EN.md)
- [Engine comparison](../api/engines.md)
- [Best practices](../api/best-practices.md)
- [Tools and extensions API](../api/tools.md)
