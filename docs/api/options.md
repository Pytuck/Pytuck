# 配置选项 API

所有配置选项均为 `dataclass`，提供完整的类型提示和默认值。

```python
from pytuck.common.options import (
    PytuckBackendOptions, JsonBackendOptions, JsonlBackendOptions, CsvBackendOptions,
    SqliteBackendOptions, DuckdbBackendOptions,
    ExcelBackendOptions, XmlBackendOptions,
    SqliteConnectorOptions, DuckdbConnectorOptions,
    SyncOptions, SyncResult,
)
```

---

## 后端配置选项

### PytuckBackendOptions

```python
@dataclass
class PytuckBackendOptions:
    encryption: Optional[Literal['low', 'medium', 'high']] = None
    password: Optional[str] = None
```

> [!IMPORTANT]
> 当前 `.pytuck` 单文件引擎重新打开文件时默认走按需读取路径，无需额外开关。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `encryption` | `Optional[str]` | `None` | 单文件加密等级；支持 `None` / `low` / `medium` / `high` |
| `password` | `Optional[str]` | `None` | 与加密配置配套使用的密码；设置 `encryption` 时必须提供 |

### JsonBackendOptions

```python
@dataclass
class JsonBackendOptions:
    indent: Optional[int] = None
    ensure_ascii: bool = False
    impl: Optional[str] = None
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `indent` | `Optional[int]` | `None` | 缩进空格数。`None` 为紧凑格式 |
| `ensure_ascii` | `bool` | `False` | 是否强制 ASCII 编码 |
| `impl` | `Optional[str]` | `None` | 指定 JSON 库：`'orjson'`、`'ujson'`、`'json'` 等 |

### JsonlBackendOptions

```python
@dataclass
class JsonlBackendOptions:
    ensure_ascii: bool = False
    impl: Optional[str] = None
    password: Optional[str] = None
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ensure_ascii` | `bool` | `False` | 是否强制 ASCII 编码 |
| `impl` | `Optional[str]` | `None` | 指定 JSON 库：`'orjson'`、`'ujson'`、`'json'` 等 |
| `password` | `Optional[str]` | `None` | ZIP 密码（仅 ASCII 可打印字符）；设置后 JSONL ZIP 将启用密码保护 |

### CsvBackendOptions

```python
@dataclass
class CsvBackendOptions:
    encoding: str = 'utf-8-sig'
    delimiter: str = ','
    indent: Optional[int] = None
    password: Optional[str] = None
    field_size_limit: Optional[int] = None
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `encoding` | `str` | `'utf-8-sig'` | 字符编码（默认带 BOM，兼容 Excel） |
| `delimiter` | `str` | `','` | 字段分隔符 |
| `indent` | `Optional[int]` | `None` | 元数据 JSON 缩进空格数 |
| `password` | `Optional[str]` | `None` | ZIP 密码（仅 ASCII 可打印字符） |
| `field_size_limit` | `Optional[int]` | `None` | CSV 字段大小上限（bytes）。`None` 使用默认 131072 |

### SqliteBackendOptions

继承自 `SqliteConnectorOptions`。

```python
@dataclass
class SqliteBackendOptions(SqliteConnectorOptions):
    use_native_sql: bool = True
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_native_sql` | `bool` | `True` | 使用原生 SQL 模式 |
| `check_same_thread` | `bool` | `True` | 检查同一线程（继承） |
| `timeout` | `Optional[float]` | `None` | 连接超时时间（继承） |
| `isolation_level` | `Optional[str]` | `None` | 事务隔离级别（继承） |

### DuckdbBackendOptions

继承自 `DuckdbConnectorOptions`。

```python
@dataclass
class DuckdbBackendOptions(DuckdbConnectorOptions):
    use_native_sql: bool = True
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_native_sql` | `bool` | `True` | 使用原生 SQL 模式 |
| `read_only` | `bool` | `False` | 只读模式（继承） |
| `threads` | `Optional[int]` | `None` | DuckDB 线程数，`None` 表示自动（继承） |
| `schema` | `str` | `'main'` | 默认 schema 名称（继承） |

### ExcelBackendOptions

```python
@dataclass
class ExcelBackendOptions:
    read_only: bool = False
    hide_metadata_sheets: bool = True
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `read_only` | `bool` | `False` | 只读模式（显著提升读取性能，不可修改） |
| `hide_metadata_sheets` | `bool` | `True` | 是否隐藏元数据工作表 |

### XmlBackendOptions

```python
@dataclass
class XmlBackendOptions:
    encoding: str = 'utf-8'
    pretty_print: bool = True
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `encoding` | `str` | `'utf-8'` | 字符编码 |
| `pretty_print` | `bool` | `True` | 是否格式化输出 |

---

## 连接器配置选项

### DuckdbConnectorOptions

```python
@dataclass
class DuckdbConnectorOptions:
    read_only: bool = False
    threads: Optional[int] = None
    schema: str = 'main'
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `read_only` | `bool` | `False` | 只读模式 |
| `threads` | `Optional[int]` | `None` | DuckDB 线程数，`None` 表示自动 |
| `schema` | `str` | `'main'` | 默认 schema 名称 |

---

## 联合类型

```python
# 后端配置选项联合类型
BackendOptions = Union[
    JsonBackendOptions, JsonlBackendOptions, CsvBackendOptions, SqliteBackendOptions,
    DuckdbBackendOptions, ExcelBackendOptions,
    XmlBackendOptions, PytuckBackendOptions
]

# 连接器配置选项联合类型
ConnectorOptions = Union[SqliteConnectorOptions, DuckdbConnectorOptions]
```

### 默认选项工具函数

```python
from pytuck.common.options import get_default_backend_options, get_default_connector_options

# 根据引擎类型返回默认配置
options = get_default_backend_options('pytuck')  # PytuckBackendOptions()
options = get_default_backend_options('json')    # JsonBackendOptions()
options = get_default_backend_options('jsonl')   # JsonlBackendOptions()
options = get_default_backend_options('sqlite')  # SqliteBackendOptions()
options = get_default_backend_options('duckdb')  # DuckdbBackendOptions()

# 根据连接器类型返回默认配置
options = get_default_connector_options('sqlite')  # SqliteConnectorOptions()
options = get_default_connector_options('duckdb')  # DuckdbConnectorOptions()
```

---

## Schema 同步选项

### SyncOptions

控制 `sync_table_schema` 和 `declarative_base(sync_schema=True)` 的行为。

```python
@dataclass
class SyncOptions:
    sync_table_comment: bool = True
    sync_column_comments: bool = True
    add_new_columns: bool = True
    drop_missing_columns: bool = False
    update_column_types: bool = False
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sync_table_comment` | `bool` | `True` | 是否同步表备注 |
| `sync_column_comments` | `bool` | `True` | 是否同步列备注 |
| `add_new_columns` | `bool` | `True` | 是否添加模型中新增的列 |
| `drop_missing_columns` | `bool` | `False` | 是否删除模型中不存在的列（**危险**） |
| `update_column_types` | `bool` | `False` | 是否更新列类型（**危险**，暂未实现） |

### SyncResult

`sync_table_schema` 的返回结果。

```python
@dataclass
class SyncResult:
    table_name: str
    table_comment_updated: bool = False
    columns_added: List[str] = field(default_factory=list)
    columns_dropped: List[str] = field(default_factory=list)
    column_comments_updated: List[str] = field(default_factory=list)
```

| 字段 | 说明 |
|------|------|
| `table_name` | 表名 |
| `table_comment_updated` | 表备注是否更新 |
| `columns_added` | 新增的列名列表 |
| `columns_dropped` | 删除的列名列表 |
| `column_comments_updated` | 更新备注的列名列表 |
| `has_changes`（property） | 是否有任何变更 |

```python
from pytuck import SyncOptions

result = session.sync_schema(User)
if result.has_changes:
    print(f"新增列: {result.columns_added}")
    print(f"删除列: {result.columns_dropped}")
```
