# 存储引擎 API

## Storage

存储引擎封装，管理表、数据和后端引擎。

```python
from pytuck import Storage
```

### 构造函数

```python
Storage(
    file_path: Optional[Union[str, Path]] = None,
    in_memory: bool = False,
    engine: str = 'pytuck',
    auto_flush: bool = False,
    backend_options: Optional[BackendOptions] = None,
)
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | `Optional[Union[str, Path]]` | `None` | 数据文件路径。`None` 表示纯内存模式 |
| `in_memory` | `bool` | `False` | 是否纯内存模式（不持久化） |
| `engine` | `str` | `'pytuck'` | 后端引擎名称：`'pytuck'`、`'json'`、`'jsonl'`、`'csv'`、`'sqlite'`、`'duckdb'`、`'excel'`、`'xml'` |
| `auto_flush` | `bool` | `False` | 是否在每次会修改数据或 schema 的 Storage 操作后自动写入磁盘；与 `Session` 配合时，`Session.commit()` 也会据此触发持久化 |
| `backend_options` | `Optional[BackendOptions]` | `None` | 强类型后端配置选项。`None` 时使用引擎默认值 |

### 使用示例

```python
from pytuck import Storage
from pytuck.common.options import JsonBackendOptions, JsonlBackendOptions, SqliteBackendOptions, DuckdbBackendOptions

# 默认 pytuck 引擎
db = Storage(file_path='data.pytuck')

# JSON 引擎（带配置）
db = Storage(
    file_path='data.json',
    engine='json',
    backend_options=JsonBackendOptions(indent=2)
)

# JSONL 引擎（ZIP 容器）
db = Storage(
    file_path='data.zip',
    engine='jsonl',
    backend_options=JsonlBackendOptions(ensure_ascii=False)
)

# SQLite 引擎（原生 SQL 模式）
db = Storage(
    file_path='data.sqlite',
    engine='sqlite',
    backend_options=SqliteBackendOptions(use_native_sql=True)
)

# DuckDB 引擎（原生 SQL + 多 schema）
db = Storage(
    file_path='data.duckdb',
    engine='duckdb',
    backend_options=DuckdbBackendOptions(use_native_sql=True, schema='main')
)

# 纯内存模式（不持久化）
db = Storage(in_memory=True)

# 自动持久化
db = Storage(file_path='data.pytuck', auto_flush=True)
```

---

## CRUD 方法

### insert()

插入一条记录。

```python
def insert(self, table_name: str, data: Dict[str, Any]) -> Any
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `data` | 记录字典 `{列名: 值}` |
| **返回** | 主键值（自动分配或用户指定） |

```python
pk = db.insert('users', {'name': 'Alice', 'age': 20})
```

### select()

按主键查询单条记录。

```python
def select(self, table_name: str, pk: Any) -> Dict[str, Any]
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `pk` | 主键值 |
| **返回** | 记录字典 |
| **异常** | `RecordNotFoundError` |

```python
record = db.select('users', 1)
```

### update()

按主键更新记录。

```python
def update(self, table_name: str, pk: Any, data: Dict[str, Any]) -> None
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `pk` | 主键值 |
| `data` | 要更新的字段 `{列名: 新值}` |
| **异常** | `RecordNotFoundError` |

```python
db.update('users', 1, {'name': 'Bob'})
```

### delete()

按主键删除记录。

```python
def delete(self, table_name: str, pk: Any) -> None
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `pk` | 主键值 |
| **异常** | `RecordNotFoundError` |

```python
db.delete('users', 1)
```

### bulk_insert()

批量插入记录。

```python
def bulk_insert(self, table_name: str, records: List[Dict[str, Any]]) -> List[Any]
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `records` | 记录字典列表 |
| **返回** | 主键列表 |

```python
pks = db.bulk_insert('users', [
    {'name': 'A', 'age': 20},
    {'name': 'B', 'age': 25},
])
```

### bulk_update()

批量更新记录。

```python
def bulk_update(self, table_name: str, updates: List[Tuple[Any, Dict[str, Any]]]) -> int
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `updates` | `(主键, 更新数据)` 元组列表 |
| **返回** | 更新的记录数 |

```python
count = db.bulk_update('users', [
    (1, {'age': 21}),
    (2, {'age': 26}),
])
```

---

## 查询方法

### query()

条件查询记录。

```python
def query(
    self,
    table_name: str,
    conditions: Sequence[ConditionType],
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: Optional[str] = None,
    order_desc: bool = False,
) -> List[Dict[str, Any]]
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `conditions` | 条件列表（`Condition` 或 `CompositeCondition`） |
| `limit` | 最多返回的记录数；`None` 表示不限制 |
| `offset` | 跳过的记录数，默认 `0` |
| `order_by` | 排序字段名（可选） |
| `order_desc` | 是否降序（默认升序） |
| **返回** | 匹配的记录字典列表 |

> 通常不直接调用此方法，而是通过 `Session.execute(select(...))` 或 `Query.filter()` 使用。

### count_rows()

统计表的记录数。

```python
def count_rows(self, table_name: str) -> int
```

### query_table_data()

分页查询表数据（专为 Web UI 设计）。

```python
def query_table_data(
    self,
    table_name: str,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: Optional[str] = None,
    order_desc: bool = False,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]
```

| 参数 | 说明 |
|------|------|
| `table_name` | 表名 |
| `limit` | 每页记录数；`None` 表示不限制 |
| `offset` | 偏移量，默认 `0` |
| `order_by` | 排序字段 |
| `order_desc` | 是否降序 |
| `filters` | 过滤条件（见下文） |
| **返回** | `{'records': [...], 'total_count': N, 'has_more': bool, 'schema': [...]}` |

**filters 参数格式**：

```python
# 格式 1：等值过滤（向后兼容）
filters = {'name': 'Alice', 'active': True}

# 格式 2：带操作符的过滤
filters = [
    {'field': 'name', 'operator': 'LIKE', 'value': 'ali'},
    {'field': 'age', 'operator': '>=', 'value': 18},
]
```

支持的操作符：`=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `LIKE`, `STARTSWITH`, `ENDSWITH`

---

## 表管理方法

### create_table()

创建表。

```python
def create_table(
    self,
    name: str,
    columns: List[Column],
    comment: Optional[str] = None,
) -> None
```

| 参数 | 说明 |
|------|------|
| `name` | 表名 |
| `columns` | 列定义列表；主键会从 `Column(primary_key=True)` 自动推断 |
| `comment` | 表备注 |
| **返回** | `None` |

> 通常不直接调用。定义模型类并继承 Base 时会自动创建表。

### get_table()

获取表对象。

```python
def get_table(self, name: str) -> Table
```

| **异常** | `TableNotFoundError` |

### drop_table()

删除表。

```python
def drop_table(self, table_name: str) -> None
```

### rename_table()

重命名表。

```python
def rename_table(self, old_name: str, new_name: str) -> None
```

### update_table_comment()

更新表备注。

```python
def update_table_comment(self, table_name: str, comment: Optional[str]) -> None
```

---

## Schema 操作方法

### add_column()

添加列。

```python
def add_column(self, table_name: str, column: Column, default_value: Any = None) -> None
```

### drop_column()

删除列。

```python
def drop_column(self, table_name: str, column_name: str) -> None
```

### alter_column()

修改列属性（类型、可空性、默认值）。

```python
def alter_column(
    self,
    table_name: str,
    column_name: str,
    *,
    col_type: Any = ...,     # ... 表示不修改
    nullable: Any = ...,
    default: Any = ...,
) -> None
```

### set_primary_key()

修改表的主键。

```python
def set_primary_key(self, table_name: str, column_name: str) -> None
```

### reorder_columns()

重新排列列的顺序。

```python
def reorder_columns(self, table_name: str, new_order: List[str]) -> None
```

### update_column()

更新列的备注和索引属性。

```python
def update_column(
    self,
    table_name: str,
    column_name: str,
    comment: Any = ...,
    index: Any = ...,
) -> None
```

### sync_table_schema()

同步模型定义与数据库表结构。

```python
def sync_table_schema(
    self,
    table_name: str,
    columns: List[Column],
    comment: Optional[str] = None,
    options: Optional[SyncOptions] = None,
) -> SyncResult
```

---

## 事务管理

### transaction()

事务上下文管理器。

```python
with db.transaction():
    db.insert('users', {'name': 'Alice'})
    db.insert('users', {'name': 'Bob'})
    # 异常时自动回滚
```

---

## 持久化方法

### flush()

将内存数据写入磁盘。

```python
db.flush()
```

> 仅在 `_dirty=True` 时实际写入。
>
> 当前实现会为 `flush()` 加上同一 `Storage` 实例级别的多线程写锁保护，用于降低并发写盘时的竞态风险；这不意味着 Pytuck 变成了面向高并发场景的数据库，整体定位仍是单进程嵌入式使用。

### close()

关闭数据库，自动调用 `flush()`。

```python
db.close()
```

---

## 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `file_path` | `Optional[Path]` | 数据文件路径 |
| `in_memory` | `bool` | 是否为纯内存模式 |
| `engine_name` | `str` | 引擎名称 |
| `auto_flush` | `bool` | 是否自动持久化 |
| `tables` | `Dict[str, Table]` | 所有表对象 |
| `backend` | `Optional[StorageBackend]` | 后端实例 |
| `is_native_sql_mode` | `bool`（property） | 是否为原生 SQL 模式；在支持的后端（如 SQLite、DuckDB）启用 `use_native_sql=True` 时为 `True` |
