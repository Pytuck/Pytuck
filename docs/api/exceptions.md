# 异常体系

所有 Pytuck 异常都继承自 `PytuckException` 基类。

```python
from pytuck import (
    PytuckException, TableNotFoundError, RecordNotFoundError,
    DuplicateKeyError, ColumnNotFoundError, ValidationError,
    TypeConversionError, ConfigurationError, SchemaError,
    QueryError, TransactionError, DatabaseConnectionError,
    SerializationError, EncryptionError, MigrationError,
    PytuckIndexError, UnsupportedOperationError,
)
```

---

## 异常层次结构

```
PytuckException                     # 基础异常
├── TableNotFoundError              # 表不存在
├── RecordNotFoundError             # 记录不存在
├── DuplicateKeyError               # 主键重复
├── ColumnNotFoundError             # 列不存在
├── ValidationError                 # 数据验证
│   └── TypeConversionError         # 类型转换失败
├── ConfigurationError              # 配置错误
│   └── SchemaError                 # Schema 定义错误
├── QueryError                      # 查询错误
├── TransactionError                # 事务错误
├── DatabaseConnectionError         # 数据库连接错误
├── SerializationError              # 序列化/反序列化错误
├── EncryptionError                 # 加密/解密错误
├── MigrationError                  # 数据迁移错误
├── PytuckIndexError                # 索引操作错误
└── UnsupportedOperationError       # 不支持的操作
```

---

## 基础异常

### PytuckException

所有 Pytuck 异常的基类。

**属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `message` | `str` | 错误消息 |
| `table_name` | `Optional[str]` | 相关的表名 |
| `column_name` | `Optional[str]` | 相关的列名 |
| `pk` | `Any` | 相关的主键值 |
| `details` | `Dict[str, Any]` | 额外详细信息 |

**方法**：

| 方法 | 说明 |
|------|------|
| `to_dict()` | 将异常转为字典，便于日志记录和序列化 |

```python
try:
    db.select('users', 999)
except PytuckException as e:
    print(e.message)
    print(e.to_dict())
```

---

## 各异常详解

### TableNotFoundError

**触发场景**：访问不存在的表。

```python
TableNotFoundError(table_name: str)
```

```python
try:
    db.get_table('nonexistent')
except TableNotFoundError as e:
    print(e.table_name)  # 'nonexistent'
```

### RecordNotFoundError

**触发场景**：按主键查询/更新/删除不存在的记录。

```python
RecordNotFoundError(table_name: str, pk: Any)
```

```python
try:
    db.select('users', 999)
except RecordNotFoundError as e:
    print(e.table_name, e.pk)  # 'users', 999
```

### DuplicateKeyError

**触发场景**：插入的主键已存在。

```python
DuplicateKeyError(table_name: str, pk: Any)
```

### ColumnNotFoundError

**触发场景**：访问不存在的列。

```python
ColumnNotFoundError(table_name: str, column_name: str)
```

### ValidationError

**触发场景**：数据不符合预期格式或约束。

```python
ValidationError(
    message: str,
    *,
    table_name: Optional[str] = None,
    column_name: Optional[str] = None,
    pk: Any = None,
    details: Optional[Dict[str, Any]] = None,
)
```

常见情况：
- Column `strict=True` 时类型不匹配
- `bulk_insert` / `bulk_update` 包含不同模型类
- 密码格式校验失败

### TypeConversionError

继承自 `ValidationError`。

**触发场景**：值无法转换为目标类型（如 `'abc'` → `int`）。

额外属性：
- `value`：无法转换的原始值
- `target_type`：目标类型名称

### ConfigurationError

**触发场景**：引擎配置或后端选项不正确。

### SchemaError

继承自 `ConfigurationError`。

**触发场景**：表结构定义不正确（如多个主键）。

### QueryError

**触发场景**：查询构建或执行失败。

常见情况：
- 无主键模型调用 `session.get()`
- 不支持的操作符
- 不存在的列名

### TransactionError

**触发场景**：事务操作失败（如嵌套事务不支持）。

### DatabaseConnectionError

**触发场景**：数据库连接未建立或已断开。

### SerializationError

**触发场景**：数据序列化或反序列化失败。

### EncryptionError

**触发场景**：加密或解密操作失败（如密码错误）。

### MigrationError

**触发场景**：数据迁移操作失败。

### PytuckIndexError

**触发场景**：索引操作失败。

### UnsupportedOperationError

**触发场景**：请求的操作在当前上下文中不支持。

常见情况：
- 在 `CursorResult` 上调用 `all()` / `first()` 等方法
- 后端不支持的功能

---

## 异常捕获建议

```python
from pytuck import (
    PytuckException, RecordNotFoundError,
    DuplicateKeyError, ValidationError,
)

# 精确捕获
try:
    user = User.get(1)
except RecordNotFoundError:
    print("用户不存在")

# 捕获所有验证错误
try:
    User.create(name=123)
except ValidationError as e:
    print(f"验证失败: {e.message}")

# 捕获所有 Pytuck 异常
try:
    do_something()
except PytuckException as e:
    log.error(e.to_dict())
```
