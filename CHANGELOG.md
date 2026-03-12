# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [0.8.0] - 2026-03-13

### 新增

- **字符串匹配查询操作符**
  - `Column.contains(value)` — 包含匹配（大小写不敏感）
  - `Column.startswith(value)` — 前缀匹配（大小写不敏感）
  - `Column.endswith(value)` — 后缀匹配（大小写不敏感）
  - 内存引擎和 SQLite 原生 SQL 模式均支持
  - `query_table_data` 的 `filters` 参数支持 `LIKE`/`STARTSWITH`/`ENDSWITH` 操作符
  - 示例：
    ```python
    # 查询名字包含 "ali" 的用户（大小写不敏感）
    stmt = select(User).where(User.name.contains('ali'))

    # 前缀/后缀匹配
    stmt = select(User).where(User.name.startswith('Al'))
    stmt = select(User).where(User.email.endswith('.com'))
    ```

- **数据库列操作功能**
  - `alter_column()` — 修改列属性（类型、可空性、默认值），支持数据自动迁移
  - `set_primary_key()` — 修改表的主键
  - `reorder_columns()` — 重新排列列顺序
  - Session 和 Storage 两层均可调用，参数同时支持模型类和表名字符串
  - 示例：
    ```python
    # 修改列类型
    session.alter_column(User, 'age', col_type=str)

    # 修改主键
    session.set_primary_key(User, 'email')

    # 重排列顺序
    session.reorder_columns(User, ['id', 'email', 'name', 'age'])
    ```

- **query_table_data 高级过滤**
  - `filters` 参数扩展为同时支持等值字典和带操作符的列表格式
  - 支持所有操作符：`=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `LIKE`, `STARTSWITH`, `ENDSWITH`
  - 向后兼容：原有 `dict` 格式（等值过滤）不受影响
  - 示例：
    ```python
    # 新格式：带操作符的过滤
    db.query_table_data('users', filters=[
        {'field': 'name', 'operator': 'LIKE', 'value': 'ali'},
        {'field': 'age', 'operator': '>=', 'value': 18},
    ])
    ```

- **CSV field_size_limit 配置**
  - `CsvBackendOptions` 新增 `field_size_limit` 参数，支持自定义 CSV 字段大小上限
  - 解决含超大文本字段（长文章、Base64 数据等）时 CSV 解析报错的问题

- **列默认值支持**
  - 各后端引擎支持 `alter_column` 设置列默认值，新增记录时自动填充

- **完整 API 参考文档**
  - 新增 `docs/api/` 目录，包含 10 个文档文件：
    - 模型定义、存储引擎、会话管理、查询系统、引擎对比与特性
    - 配置选项、异常体系、工具与扩展、最佳实践、文档索引
  - 文档涵盖全部公开 API 签名、参数说明、使用示例和注意事项

- **适用场景说明**
  - README 添加醒目的库定位和限制提示（纯 Python 性能边界、数据规模建议、替代方案推荐等）
  - 最佳实践文档添加详细的适用场景与限制表格

### 测试

- 添加字符串匹配查询测试（40 个测试用例，覆盖表达式创建、内存评估、Query/Select 集成、query_table_data 格式）
- 添加 `alter_column` / `set_primary_key` / `reorder_columns` API 测试
- 添加 CSV `field_size_limit` 选项测试
- 添加 SQLite 后端字符串匹配分页测试
