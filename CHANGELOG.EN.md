# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [中文版](./CHANGELOG.md)

> For historical versions, see: [docs/changelog/](./docs/changelog/)

---

## [0.8.0] - 2026-03-13

### Added

- **String Matching Query Operators**
  - `Column.contains(value)` — Substring match (case-insensitive)
  - `Column.startswith(value)` — Prefix match (case-insensitive)
  - `Column.endswith(value)` — Suffix match (case-insensitive)
  - Supported in both in-memory engines and SQLite native SQL mode
  - `query_table_data` `filters` parameter supports `LIKE`/`STARTSWITH`/`ENDSWITH` operators
  - Example:
    ```python
    # Find users whose name contains "ali" (case-insensitive)
    stmt = select(User).where(User.name.contains('ali'))

    # Prefix/suffix matching
    stmt = select(User).where(User.name.startswith('Al'))
    stmt = select(User).where(User.email.endswith('.com'))
    ```

- **Database Column Operations**
  - `alter_column()` — Modify column attributes (type, nullability, default value) with automatic data migration
  - `set_primary_key()` — Change table primary key
  - `reorder_columns()` — Reorder column positions
  - Available at both Session and Storage layers; accepts model classes or table name strings
  - Example:
    ```python
    # Change column type
    session.alter_column(User, 'age', col_type=str)

    # Change primary key
    session.set_primary_key(User, 'email')

    # Reorder columns
    session.reorder_columns(User, ['id', 'email', 'name', 'age'])
    ```

- **query_table_data Advanced Filtering**
  - `filters` parameter now supports both equality dicts and operator-based list format
  - Supports all operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `LIKE`, `STARTSWITH`, `ENDSWITH`
  - Backward compatible: original `dict` format (equality filtering) still works
  - Example:
    ```python
    # New format: operator-based filtering
    db.query_table_data('users', filters=[
        {'field': 'name', 'operator': 'LIKE', 'value': 'ali'},
        {'field': 'age', 'operator': '>=', 'value': 18},
    ])
    ```

- **CSV field_size_limit Configuration**
  - Added `field_size_limit` parameter to `CsvBackendOptions` for custom CSV field size limits
  - Resolves CSV parsing errors when data contains very large text fields (long articles, Base64 data, etc.)

- **Column Default Value Support**
  - Backend engines support setting column defaults via `alter_column`; new records are automatically populated

- **Complete API Reference Documentation**
  - Added `docs/api/` directory with 10 documentation files:
    - Models, Storage, Session, Query System, Engine Comparison
    - Configuration Options, Exception Hierarchy, Tools & Extensions, Best Practices, Index
  - Covers all public API signatures, parameter descriptions, usage examples, and caveats

- **Usage Scope Disclaimer**
  - README now includes prominent positioning and limitation notices (pure Python performance boundaries, data volume recommendations, alternative solutions, etc.)
  - Best Practices documentation includes detailed scope and limitation tables

### Tests

- Added string matching query tests (40 test cases covering expression creation, in-memory evaluation, Query/Select integration, query_table_data formats)
- Added `alter_column` / `set_primary_key` / `reorder_columns` API tests
- Added CSV `field_size_limit` option tests
- Added SQLite backend string matching pagination tests
