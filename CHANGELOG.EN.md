# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [1.1.0] - 2026-03-29

### Added

- **DuckDB Bulk Insert Optimization**
  - Session insert buffer: individual `INSERT` statements are automatically buffered and batch-committed on `commit()`
  - DuckDB engine now uses `COPY FROM CSV` fast bulk insert path, reducing 100k inserts from `277s` to `1.5s`
  - Native SQL mode transaction wrapping + `bulk_insert` batching, now on par with SQLite insert performance

- **JSONL Engine Incremental Save**
  - Following the CSV engine's incremental pattern, `save()` is split into `_save_full()` + `_save_incremental()`
  - In multi-table scenarios, unchanged tables are copied as compressed bytes from the old ZIP, avoiding full serialization
  - Encrypted ZIPs automatically fall back to full save; API is fully backward-compatible

- **Lazy-Loaded Table Full Record Access**
  - Lazy-load mode now supports `len(table)`, `iter(table)` and other full record access operations
  - First access automatically loads all records from disk; subsequent operations behave identically to in-memory mode

### Fixed

- **DuckDB WAL Not Written to Main File**
  - In DuckDB native SQL mode, data remained in the WAL file after `commit()`, leaving the main database file with only schema (~12KB)
  - Added `DuckDBConnector.checkpoint()` method; `flush()` and `close()` now automatically execute `CHECKPOINT`
  - After fix, 100k record file size restored from `12KB` to `6.76MB`

- **SQLite `insert_records` Special Type Handling**
  - `executemany` bulk inserts failed for `datetime` / `timedelta` / `list` / `dict` types that were not serialized
  - All field values now go through `_serialize_value()` uniformly

- **DuckDB `rollback_transaction` Error on No Active Transaction**
  - After `CHECKPOINT` ended the transaction, `session.close()` rollback threw `TransactionException`
  - `rollback_transaction()` now safely ignores "no active transaction" exceptions

### Improved

- **README Documentation Split**
  - README home page streamlined to project positioning, installation, and minimal examples
  - Detailed documentation moved to `docs/api/` (API reference) and `docs/guide/` (guides & benchmarks)

- **Example Code Cleanup**
  - Renamed `new_api_demo.py` → `session_api_demo.py` for clearer naming
  - All examples now have `if __name__ == '__main__'` entry guards
  - Fixed `_common.py` path joining and `json_impl_demo.py` exception handling issues

### Tests

- Added all-engine persistence integrity tests (500 records: flush → file size sanity → reopen → record count + data verification)
- Added all-engine flush-then-reopen tests (verify data is written to file after flush without close)
- SQLite Chinese column name tests changed from permanent skip to SQLite compatibility mode execution
- Optimized Pytuck engine tests to support lazy-load logic

### Benchmark (100k records)

| Engine | Insert | Save | Load | File Size |
|--------|--------|------|------|-----------|
| DuckDB | 1.52s | 86.23ms | 29.24ms | 6.76MB |
| SQLite | 1.53s | 2.91ms | 389.5μs | 6.97MB |
| Pytuck | 834.38ms | 562.03ms | 337.28ms | 6.09MB |

> Full benchmark at [docs/guide/benchmark.md](./docs/guide/benchmark.md)
