# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [0.9.0] - 2026-03-15

### Added

- **to_dict() Enhancement & to_json()**
  - `to_dict()` supports `include` / `exclude` field filtering
  - `depth` parameter controls relationship serialization depth (`depth=1` expands one level of Relationships)
  - New `to_json()` method with `indent`, `include`, `exclude`, `depth` parameters
  - Example:
    ```python
    user.to_dict(exclude={'password'})         # Exclude sensitive fields
    user.to_json(include={'id', 'name'})       # Keep only specified fields
    user.to_dict(depth=1)                      # Expand one level of relationships
    ```

- **Column-level Validators**
  - `Column` now accepts a `validator` parameter: a single function or list of functions
  - Validators execute after type conversion; `None` values skip validation
  - Returning `False` or raising an exception triggers `ValidationError`
  - Example:
    ```python
    name = Column(str, validator=lambda x: len(x) <= 100)
    age = Column(int, validator=[lambda x: x >= 0, lambda x: x <= 150])
    ```

- **Model Inheritance (Mixin Support)**
  - Use `__abstract__ = True` to mark abstract base classes for column reuse via Mixins
  - Supports multi-level inheritance (A -> B -> C) and multiple inheritance (multiple Mixins)
  - Subclasses can override parent columns (change defaults, add validators, etc.)
  - Example:
    ```python
    class TimestampMixin(Base):
        __abstract__ = True
        created_at = Column(datetime, default_factory=datetime.now)

    class User(TimestampMixin):
        __tablename__ = 'users'
        name = Column(str)
    ```

- **Column default_factory Support**
  - `Column` now accepts a `default_factory` parameter: a zero-argument callable invoked on each instance creation
  - Mutually exclusive with `default` (static value); cannot set both
  - Similar to Python `dataclass` `field(default_factory=...)` design
  - Example:
    ```python
    created_at = Column(datetime, default_factory=datetime.now)
    tags = Column(list, default_factory=list)
    ```

- **Incremental Save for Non-Binary Backends**
  - Added Table-level dirty flags (`_data_dirty` / `_schema_dirty`)
  - `Storage.flush()` automatically tracks changed tables and passes only changed table names to the backend
  - CSV engine implements incremental ZIP writing: unchanged tables are copied directly from the old ZIP (binary copy), only changed tables are rewritten
  - Other backends (JSON/Excel/XML) have extended signatures but behavior is unchanged (full rewrite)
  - Incremental strategy is not used when ZIP password protection is enabled (falls back to full rewrite)

- **Binary Encryption + Lazy Loading Compatibility**
  - All three ciphers (XOR/LCG/ChaCha20) now have a `decrypt_at()` method for random-access decryption
  - Encrypted files now support lazy loading: only the index region is decrypted on load to obtain `pk_offsets`; individual records are decrypted on demand
  - File format and write path are completely unchanged; this is a read-path optimization
  - Random-access decryption principles:
    - XOR: 256-byte periodic keystream, offset modulo
    - LCG: O(log N) fast-forward algorithm to jump to any offset
    - ChaCha20: Native random access via block counter

### Improved

- **Temporary File Security**
  - All backend engines now use `tempfile.mkstemp` instead of manually constructed temp file paths
  - Temp files are created in the target file's directory, ensuring atomic `replace()` on the same filesystem
  - Removed unnecessary `unlink()` + `replace()` patterns; uses `replace()` for atomic replacement

### Fixed

- Fixed database connection not properly closed in string matching query tests

### Tests

- Added to_dict/to_json enhancement tests
- Added Column validator tests
- Added model inheritance and Mixin tests
- Added Column default_factory tests
- Added Table-level dirty flags and incremental save tests
- Added encrypted lazy loading tests (three encryption levels + decrypt_at consistency verification)
