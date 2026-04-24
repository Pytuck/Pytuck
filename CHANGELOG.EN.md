# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [1.4.0] - 2026-04-24

### Added

- **Enabled cross-storage relationship loading**
  - `Relationship` and `prefetch` can now resolve target models and target storages across different storage instances
  - Related records can be loaded across heterogeneous engines without joins
  - Added documentation and regression coverage for cross-storage relationships

- **Added JSON vs orjson benchmark script**
  - Covers save, load, reopen, and first-query-after-reopen paths
  - Supports configurable record counts plus Markdown summaries and raw JSON output
  - Reports output file sizes and cleans up temporary data automatically

### Fixed

- **Improved Excel backend compatibility for external workbooks**
  - Normalizes external Excel headers to strings to avoid inconsistent internal key types
  - Filters empty or invalid schema / metadata keys to reduce load-time errors
  - Improves stability when reading external Excel files and partially named sheets

- **Added multi-threaded write locking around `Storage.flush()` and `close()`**
  - Critical write paths are serialized within the same `Storage` instance
  - Prevents duplicate backend saves during concurrent flushes
  - Adds thread-serialization regression coverage

- **Corrected DuckDB `datetime` type mapping**
  - `datetime` now maps to `TIMESTAMPTZ`
  - Preserves timezone information for more accurate persistence

### Docs & Benchmarks

- **Updated multi-engine, relationship, and benchmark docs**
  - Expanded multi-engine format notes, configuration options, and relationship loading docs
  - README and benchmark guides now include JSON / orjson comparison results and recommendations
  - Public-facing version references are updated to `1.4.0`

### Tests

- **Expanded regression coverage for engines and relationship scenarios**
  - Added round-trip fidelity tests for supported data types across engines
  - Added cross-storage relationship and exception-path tests
  - Improved benchmark type annotations and threading validation

### Breaking Changes

- **Dropped `ujson` support from JSON backends**
  - The `impl` option no longer accepts `ujson`
  - JSON / JSONL backends and examples are now simplified to `json`, `orjson`, or custom implementations

- **Removed the `lazy` parameter from the `Relationship` constructor**
  - Relationship configuration now uses the streamlined keyword-only signature
  - Call sites relying on the old parameter must be updated
