# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [1.2.1] - 2026-04-14

### Changed

- **PTK7 is now the default long-term single-file format**
  - The default Pytuck single-file engine now treats PTK7 as the current primary format
  - Future work is expected to focus on compatibility and performance improvements within PTK7 unless a hard blocker requires another format change

- **The public surface no longer centers PTK5 migration**
  - README, API docs, and root package messaging are now focused on the current product surface
  - PTK5-specific public migration shortcuts have been removed while the generic migration path remains available

### Performance

- **Session write paths are now much tighter**
  - Fixed the O(N²) duplicate-check bottleneck in `Session.add()`, reducing 100k `session.add_all() + commit()` from `47.59s` to `0.72s`
  - `Session.flush()` now groups new objects by model class and reuses `storage.bulk_insert()`; the in-memory path removes redundant readback while preserving per-row `before_insert` / `after_insert` semantics
  - `Session.bulk_insert()` stays at `0.41s` in the same benchmark, with no throughput regression

### Documentation

- **Docs are refocused on current usage**
  - README, API, and benchmark docs now center on installation, usage, engine comparison, best practices, and current benchmark results
  - README, benchmark, and best-practices docs now explain the `session.add_all() + commit()` vs `session.bulk_insert()` write-path trade-off
  - User-facing version references are unified on `1.2.1`, and the release notes are kept only in the root changelog without adding a new archived changelog file

### Tests

- **The public contract is aligned to PTK7**
  - Single-file engine tests and user-visible error messaging now reflect PTK7 behavior
  - Coverage keeps lazy-load, persistence integrity, and multi-engine compatibility paths in place

- **Added write-path regression coverage**
  - Covers `add_all()` duplicate-check complexity, the grouped bulk-insert path in `flush()`, mixed-model grouping, and the per-row event semantics of `add_all() + commit()`
  - The full test suite passes with `1114` tests
