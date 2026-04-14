# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [1.2.0] - 2026-04-14

### Changed

- **PTK7 is now the default long-term single-file format**
  - The default Pytuck single-file engine now treats PTK7 as the current primary format
  - Future work is expected to focus on compatibility and performance improvements within PTK7 unless a hard blocker requires another format change

- **The public surface no longer centers PTK5 migration**
  - README, API docs, and root package messaging are now focused on the current product surface
  - PTK5-specific public migration shortcuts have been removed while the generic migration path remains available

### Documentation

- **Docs are refocused on current usage**
  - README, API, and benchmark docs now center on installation, usage, engine comparison, best practices, and current benchmark results
  - The multi-engine benchmark table is restored in `docs/guide/benchmark.md`

### Tests

- **The public contract is aligned to PTK7**
  - Single-file engine tests and user-visible error messaging now reflect PTK7 behavior
  - Coverage keeps lazy-load, persistence integrity, and multi-engine compatibility paths in place
