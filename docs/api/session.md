# 会话管理 API

## Session

会话管理器，统一管理数据库操作，提供对象状态追踪和事务管理。

```python
from pytuck import Session
```

### 构造函数

```python
Session(storage: Storage, autocommit: bool = False)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `storage` | `Storage` | 必填 | Storage 实例 |
| `autocommit` | `bool` | `False` | 是否在 `add()` / `delete()` 后自动提交 |

---

## 对象管理

### add()

添加对象到会话（标记为待插入）。

```python
def add(self, instance: PureBaseModel) -> None
```

### add_all()

批量添加对象到会话。

```python
def add_all(self, instances: List[PureBaseModel]) -> None
```

### delete()

标记对象为待删除。

```python
def delete(self, instance: PureBaseModel) -> None
```

### merge()

合并一个 detached 实例到会话中。

```python
def merge(self, instance: PureBaseModel) -> PureBaseModel
```

行为：
- 如果 identity map 中存在相同主键的实例 → 更新其属性，返回现有实例
- 如果不存在 → 尝试从数据库加载，加载成功则更新属性
- 如果数据库中也不存在 → 作为新对象 `add()`

```python
external_user = User(id=1, name='Updated')
managed_user = session.merge(external_user)
session.commit()
```

---

## 提交与回滚

### flush()

将待处理的修改刷新到 Storage 内存（不写入磁盘）。

```python
def flush(self) -> None
```

### commit()

提交事务：调用 `flush()`，若 `auto_flush=True` 则同时写入磁盘。

```python
def commit(self) -> None
```

### rollback()

回滚：清空所有待处理修改和 identity map。

```python
def rollback(self) -> None
```

---

## 批量操作

### bulk_insert()

批量插入模型实例（立即写入 Storage 内存）。

```python
def bulk_insert(self, instances: List[PureBaseModel]) -> List[Any]
```

与 `add_all()` 的区别：
- `add_all()` 将实例标记为待插入，`commit()` 时逐条写入
- `bulk_insert()` 立即批量写入 Storage，性能更优

触发 `before_bulk_insert` / `after_bulk_insert` 事件，不触发逐条事件。

```python
users = [User(name='A'), User(name='B'), User(name='C')]
pks = session.bulk_insert(users)
session.commit()  # 仅负责 auto_flush 磁盘持久化
```

### bulk_update()

批量更新模型实例（立即写入 Storage 内存）。

```python
def bulk_update(self, instances: List[PureBaseModel]) -> int
```

触发 `before_bulk_update` / `after_bulk_update` 事件。

---

## 查询方法

### get()

通过主键获取对象（支持 identity map 缓存）。

```python
def get(self, model_class: Type[T], pk: Any) -> Optional[T]
```

| 参数 | 说明 |
|------|------|
| `model_class` | 模型类 |
| `pk` | 主键值 |
| **返回** | 模型实例或 `None` |
| **异常** | `QueryError`（无主键模型调用时） |

```python
user = session.get(User, 1)
```

### refresh()

从数据库重新加载实例的所有属性。

```python
def refresh(self, instance: PureBaseModel) -> None
```

```python
session.refresh(user)  # 重新加载最新数据
```

### query()

创建查询构建器（旧风格，推荐使用 `execute(select(...))`）。

```python
def query(self, model_class: Type[T]) -> Query[T]
```

```python
# 旧风格（仍然支持）
users = session.query(User).filter(User.age >= 18).all()

# 推荐风格
result = session.execute(select(User).where(User.age >= 18))
users = result.all()
```

---

## 语句执行

### execute()

执行 Statement（SQLAlchemy 2.0 风格）。

```python
def execute(self, statement: Statement) -> Union[Result, CursorResult]
```

根据 Statement 类型返回不同结果：

| Statement 类型 | 返回类型 | 说明 |
|----------------|----------|------|
| `Select[T]` | `Result[T]` | 查询结果 |
| `Insert[T]` | `CursorResult[T]` | 插入结果 |
| `Update[T]` | `CursorResult[T]` | 更新结果 |
| `Delete[T]` | `CursorResult[T]` | 删除结果 |

```python
from pytuck import select, insert, update, delete

# SELECT
result = session.execute(select(User).where(User.age >= 18))
users = result.all()

# INSERT
result = session.execute(insert(User).values(name='Alice', age=20))
new_id = result.inserted_primary_key
session.commit()

# UPDATE
result = session.execute(update(User).where(User.id == 1).values(age=21))
affected = result.rowcount()
session.commit()

# DELETE
result = session.execute(delete(User).where(User.id == 1))
session.commit()
```

---

## 事务管理

### begin()

事务上下文管理器。

```python
with session.begin():
    session.add(User(name='Alice'))
    session.add(User(name='Bob'))
    # 异常时自动回滚
```

### 上下文管理器协议

Session 支持 `with` 语句，正常退出时自动 `commit()`，异常时自动 `rollback()`。

```python
with Session(db) as session:
    session.add(User(name='Alice'))
    # 退出时自动 commit
```

### close()

关闭会话，清理所有状态。

```python
def close(self) -> None
```

---

## Schema 操作

Session 提供面向模型的 Schema 操作方法，参数接受模型类或表名字符串。

### sync_schema()

```python
def sync_schema(self, model_class: Type[PureBaseModel], options: Optional[SyncOptions] = None) -> SyncResult
```

### add_column()

```python
def add_column(self, model_or_table, column: Column, default_value: Any = None) -> None
```

### drop_column()

```python
def drop_column(self, model_or_table, column_name: str) -> None
```

### alter_column()

```python
def alter_column(self, model_or_table, column_name: str, *, col_type=..., nullable=..., default=...) -> None
```

### set_primary_key()

```python
def set_primary_key(self, model_or_table, column_name: str) -> None
```

### reorder_columns()

```python
def reorder_columns(self, model_or_table, new_order: List[str]) -> None
```

### update_table_comment()

```python
def update_table_comment(self, model_or_table, comment: Optional[str]) -> None
```

### update_column()

```python
def update_column(self, model_or_table, column_name: str, comment=None, index=None) -> None
```

### drop_table()

```python
def drop_table(self, model_or_table) -> None
```

### rename_table()

```python
def rename_table(self, old_model_or_table, new_name: str) -> None
```

---

## Identity Map

Session 内部维护一个 Identity Map（标识映射），确保同一主键的对象在会话中只有一个实例：

- `get()` 优先从 Identity Map 查找
- `execute(select(...))` 返回的实例自动注册
- 修改已注册实例的属性会自动标记为 dirty

### 脏跟踪（Dirty Tracking）

Session 管理的实例修改属性时，会自动标记为"脏"状态，`commit()` 时自动更新到数据库：

```python
user = session.get(User, 1)
user.name = 'New Name'  # 自动标记为 dirty
session.commit()         # 自动更新到数据库
```
