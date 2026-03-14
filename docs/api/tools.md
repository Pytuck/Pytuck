# 工具与扩展 API

## 数据迁移工具

迁移工具不从根包导出，需单独导入：

```python
from pytuck.tools.migrate import migrate_engine, import_from_database, get_available_engines
```

### migrate_engine()

在不同存储引擎之间迁移数据。

```python
def migrate_engine(
    source_path: Union[str, Path],
    source_engine: str,
    target_path: Union[str, Path],
    target_engine: str,
    *,
    overwrite: bool = False,
    source_options: Optional[BackendOptions] = None,
    target_options: Optional[BackendOptions] = None,
) -> Dict[str, Any]
```

| 参数 | 说明 |
|------|------|
| `source_path` | 源数据文件路径 |
| `source_engine` | 源引擎名称 |
| `target_path` | 目标数据文件路径 |
| `target_engine` | 目标引擎名称 |
| `overwrite` | 是否覆盖已存在的目标文件 |
| `source_options` | 源引擎配置选项 |
| `target_options` | 目标引擎配置选项 |
| **返回** | `{'tables': N, 'records': N, 'source_engine': str, 'target_engine': str, ...}` |
| **异常** | `MigrationError`、`FileNotFoundError`、`FileExistsError` |

```python
from pytuck.tools.migrate import migrate_engine

# 从 Binary 迁移到 JSON
result = migrate_engine(
    source_path='data.db',
    source_engine='binary',
    target_path='data.json',
    target_engine='json',
)
print(f"迁移完成: {result['tables']} 个表, {result['records']} 条记录")

# 覆盖已存在的目标文件
migrate_engine(
    source_path='data.json',
    source_engine='json',
    target_path='data.sqlite',
    target_engine='sqlite',
    overwrite=True,
)
```

### import_from_database()

从外部关系型数据库导入数据到 Pytuck 格式。

```python
def import_from_database(
    source_path: Union[str, Path],
    target_path: Union[str, Path],
    target_engine: str = 'binary',
    *,
    source_type: str = 'sqlite',
    tables: Optional[List[str]] = None,
    primary_key_map: Optional[Dict[str, str]] = None,
    exclude_tables: Optional[List[str]] = None,
    schema_only: bool = False,
    overwrite: bool = False,
    source_options: Optional[ConnectorOptions] = None,
    target_options: Optional[BackendOptions] = None,
) -> Dict[str, Any]
```

| 参数 | 说明 |
|------|------|
| `source_path` | 源数据库文件路径 |
| `target_path` | 目标 Pytuck 文件路径 |
| `target_engine` | 目标引擎名称（默认 `'binary'`） |
| `source_type` | 源数据库类型（目前仅 `'sqlite'`） |
| `tables` | 要导入的表名列表（`None` = 全部） |
| `primary_key_map` | 表名到主键列名的映射 |
| `exclude_tables` | 要排除的表名列表 |
| `schema_only` | 仅导入表结构，不导入数据 |
| `overwrite` | 是否覆盖已存在的目标文件 |
| **返回** | `{'tables': N, 'records': N, 'table_details': {...}, ...}` |

```python
from pytuck.tools.migrate import import_from_database

# 从普通 SQLite 导入
result = import_from_database(
    source_path='external.db',
    target_path='data.json',
    target_engine='json',
)

# 指定主键和排除表
result = import_from_database(
    source_path='external.db',
    target_path='data.db',
    primary_key_map={'users': 'user_id'},
    exclude_tables=['sqlite_sequence'],
    overwrite=True,
)

# 仅导入结构
result = import_from_database(
    source_path='external.db',
    target_path='schema.json',
    target_engine='json',
    schema_only=True,
)
```

### get_available_engines()

获取所有可用的存储引擎及其状态。

```python
def get_available_engines() -> Dict[str, bool]
```

```python
from pytuck.tools.migrate import get_available_engines

engines = get_available_engines()
# {'binary': True, 'json': True, 'csv': True, 'sqlite': True, 'excel': False, 'xml': False}
```

---

## 事件钩子

全局事件管理器，支持 Model 级和 Storage 级事件。

```python
from pytuck import event
```

### Model 级事件

| 事件名 | 回调签名 | 触发时机 |
|--------|---------|---------|
| `before_insert` | `fn(instance)` | 插入前 |
| `after_insert` | `fn(instance)` | 插入后（已有主键） |
| `before_update` | `fn(instance)` | 更新前 |
| `after_update` | `fn(instance)` | 更新后（已刷新） |
| `before_delete` | `fn(instance)` | 删除前 |
| `after_delete` | `fn(instance)` | 删除后 |
| `before_bulk_insert` | `fn(instances)` | 批量插入前 |
| `after_bulk_insert` | `fn(instances)` | 批量插入后 |
| `before_bulk_update` | `fn(instances)` | 批量更新前 |
| `after_bulk_update` | `fn(instances)` | 批量更新后 |

### Storage 级事件

| 事件名 | 回调签名 | 触发时机 |
|--------|---------|---------|
| `before_flush` | `fn(storage)` | 写入磁盘前 |
| `after_flush` | `fn(storage)` | 写入磁盘后 |

### 注册方式

```python
from pytuck import event

# 装饰器注册
@event.listens_for(User, 'before_insert')
def set_timestamp(instance):
    instance.created_at = datetime.now()

# 函数式注册
def audit_changes(instance):
    print(f"Updated: {instance}")

event.listen(User, 'after_update', audit_changes)

# Storage 级事件
event.listen(db, 'before_flush', lambda storage: print("flushing..."))
```

### 管理方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `listen()` | `listen(target, event_name, fn)` | 注册监听器 |
| `listens_for()` | `listens_for(target, event_name)` | 装饰器方式注册 |
| `remove()` | `remove(target, event_name, fn)` | 移除监听器 |
| `clear()` | `clear(target=None)` | 清除监听器（`None` 清除全部） |

---

## 关系预取 API

批量预取关联数据，解决 Relationship 的 N+1 查询问题。

```python
from pytuck import prefetch
```

### 两种使用方式

**1. 独立函数**（对已获取的实例列表批量预取）：

```python
users = session.execute(select(User)).all()
prefetch(users, 'orders')              # 批量加载所有用户的 orders
prefetch(users, 'orders', 'profile')   # 支持多个关系名
```

**2. 查询选项**（集成到 Select 链式调用）：

```python
stmt = select(User).options(prefetch('orders'))
result = session.execute(stmt)
users = result.all()  # all() 返回后，orders 已批量加载
```

### 函数签名

```python
def prefetch(*args) -> Union[None, PrefetchOption]
```

- 第一个参数是序列（实例列表）→ 直接执行预取，返回 `None`
- 第一个参数是字符串（关系名）→ 返回 `PrefetchOption`，用于 `Select.options()`

### 工作原理

- **一对多**：收集所有 owner 主键 → 一次 IN 查询 → 按外键分组到各实例
- **多对一**：收集所有外键值（去重）→ 一次 IN 查询 → 按主键映射到各实例
- 结果自动缓存到实例，后续访问不再查询

---

## 类型系统

Pytuck 内置类型编解码器，支持以下 Python 类型的自动序列化和反序列化：

| Python 类型 | 支持 | 序列化方式 |
|------------|------|-----------|
| `int` | ✅ | 原值 |
| `float` | ✅ | 原值 |
| `str` | ✅ | 原值 |
| `bool` | ✅ | 原值（SQLite 中为 0/1） |
| `bytes` | ✅ | Base64（文本引擎）/ 原值（Binary） |
| `datetime` | ✅ | ISO 8601 字符串 |
| `date` | ✅ | ISO 8601 字符串 |
| `timedelta` | ✅ | 秒数（浮点数） |
| `list` | ✅ | JSON 字符串 |
| `dict` | ✅ | JSON 字符串 |
