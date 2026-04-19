# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [1.3.0] - 2026-04-19

### Changed

- **Adopted modern type annotation syntax**
  - Using more modern type annotation syntax: `list[str]`, `str|None`, `type[str]`, etc.
  - Replaced old `typing.List[str]`, `typing.Optional[str]`, `typing.Type[str]`, etc.
  - Improved code readability and conciseness

- **Restored Pytuck three-tier encryption**
  - Restored and unified the three encryption levels (low/medium/high) for the Pytuck engine
  - Clarified default behavior and configuration entry points so usage stays consistent across security levels
  - Updated public-facing docs and release references to `1.3.0`

### Breaking Changes

- **Minimum Python version requirement raised to 3.10**
  - No longer supports Python 3.8 and below
  - Python 3.9 compatibility has not been verified
  - Officially supports Python 3.10 and above
