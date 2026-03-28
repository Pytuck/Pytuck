# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [1.0.0] - 2026-03-29

### Added

- **Native DuckDB Backend**
  - Added the optional `duckdb` dependency and a native DuckDB backend implementation
  - Supports multi-schema workflows, native SQL, table/column comments, and server-side pagination
  - Keeps the existing `Storage` / `Session` / ORM API shape; switching engine and options is enough to use it

- **JSONL ZIP Backend**
  - Added the `jsonl` engine with a ZIP container layout
  - Stores each table as its own `.jsonl` file with a unified `_metadata.json`
  - Integrated into migration tools, benchmark scripts, and engine documentation

### Changed

- **Pytuck Single-File Engine Finalized**
  - The public engine name `binary` has been renamed to `pytuck`
  - The default single-file extension has changed from `.db` to `.pytuck`
  - PTK5 is now the only supported single-file format; v4/PTK4 compatibility has been dropped
  - The sidecar WAL filename now uses the hidden form `.<name>.wal`

- **Public Entry Points Synchronized for 1.0.0**
  - `Storage` default engine, migration-tool defaults, README, docs/api, TODO, and benchmark docs now consistently use `pytuck`
  - Public documentation for the single-file engine is now aligned on Pytuck / `.pytuck` / PTK5 terminology

### Improved

- **Dependencies and Tooling**
  - Default installation remains zero external dependencies; DuckDB / Excel / XML / JSON acceleration are all exposed through extras
  - GitHub Actions and benchmark workflows have been updated to use uv-based commands

- **Documentation and Benchmarks**
  - README and API docs now include DuckDB, JSONL, CSV footprint guidance, PyPy rerun results, and engine-selection notes
  - Clarified that the "~10K / 100K+" guidance mainly refers to a single hot table, and documented DuckDB handling of `None` vs `''`

### Tests

- Expanded test coverage for DuckDB, JSONL, and the Pytuck engine rename
- Updated benchmark scripts to include DuckDB, JSONL, and PyPy rerun results
- Synchronized the engine matrix, migration examples, and documentation samples
