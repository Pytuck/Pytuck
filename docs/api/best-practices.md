# 最佳实践

> [!IMPORTANT]
> ## 适用场景与限制
>
> Pytuck 是纯 Python 实现的嵌入式文档数据库，在使用前请了解以下限制：
>
> | 限制 | 说明 |
> |------|------|
> | **数据规模** | 万级记录以内体验最佳。十万级以上请使用 SQLite 引擎（原生 SQL 模式），百万级以上不建议使用本库 |
> | **性能** | 纯 Python 实现，查询和写入性能无法与 C 扩展数据库相比。如果性能是关键需求，本库不是最佳选择 |
> | **并发** | 定位单进程嵌入式数据库，不支持多进程/多线程并发写入 |
> | **事务** | 基础事务支持（快照回滚），不支持嵌套事务，不支持 MVCC |
> | **查询能力** | 不支持 JOIN、聚合函数（COUNT/SUM/AVG）、子查询。复杂分析请在 Python 层面处理 |
>
> ### 何时应该选择其他方案
>
> | 你的需求 | 推荐方案 |
> |---------|---------|
> | 大数据量 + 复杂查询 | [SQLAlchemy](https://www.sqlalchemy.org/) + PostgreSQL/MySQL |
> | 轻量嵌入式 + SQL 支持 | [SQLAlchemy](https://www.sqlalchemy.org/) + SQLite |
> | 高性能键值存储 | Redis、LMDB |
> | 复杂分析型查询（超出 Pytuck ORM 范围） | DuckDB、Pandas |
> | 分布式/高并发 | PostgreSQL、MongoDB |
>
> ### Pytuck 的最佳使用场景
>
> - **受限 Python 环境**（Ren'Py、MicroPython 等无法使用 C 扩展的场景）
> - **桌面应用 / 小工具**的本地数据存储
> - **原型开发 / 快速验证**（零配置、零 SQL）
> - **配置管理 / 小规模数据持久化**
> - **需要多种存储格式**（同一数据可在 Binary/JSON/CSV/Excel 间自由切换）

---

## 引擎选型

### 按场景选择

| 场景 | 推荐 | 备选 |
|------|------|------|
| 通用生产环境 | Binary | SQLite |
| 大数据量（>10 万条） | DuckDB / SQLite | Binary（懒加载） |
| 分析型查询 / 多 schema | DuckDB | SQLite |
| 需要加密保护 | Binary（加密） | CSV（ZIP 密码） |
| 开发调试 | JSON | — |
| 与 Excel 互操作 | Excel | CSV |
| 嵌入式应用（如 Ren'Py） | Binary | JSON |
| 跨系统数据交换 | CSV / JSON | XML |

### 引擎切换

引擎之间可以通过迁移工具零成本切换：

```python
from pytuck.tools.migrate import migrate_engine

# 开发阶段用 JSON，上线切换为 Binary
migrate_engine('data.json', 'json', 'data.db', 'binary')
```

---

## 持久化策略

### 理解持久化层次

Pytuck 的数据修改经过两层：

```
Session 待处理队列 → Storage 内存 → 磁盘文件
        flush()          flush()/close()
        commit()         auto_flush=True 时自动
```

### 推荐策略

**生产环境**：使用 `auto_flush=True`

```python
db = Storage(file_path='data.db', auto_flush=True)

# commit() 自动写入磁盘
session.commit()

# Active Record 的 create/save/delete 也自动写入
User.create(name='Alice')
```

**批量操作**：先关闭 `auto_flush`，操作完成后统一刷新

```python
db = Storage(file_path='data.db', auto_flush=False)

# 批量操作
for i in range(10000):
    db.insert('users', {'name': f'User_{i}'})

# 一次性写入磁盘
db.flush()
```

### 常见陷阱

```python
# ❌ 忘记持久化
db = Storage(file_path='data.db')  # auto_flush 默认 False
User.create(name='Alice')
# 程序崩溃 → 数据丢失！

# ✅ 确保持久化
db = Storage(file_path='data.db', auto_flush=True)
User.create(name='Alice')  # 自动写入磁盘

# ✅ 或显式关闭
db = Storage(file_path='data.db')
User.create(name='Alice')
db.close()  # 关闭时自动 flush
```

---

## 索引使用

### 索引类型选择

| 索引类型 | 适用查询 | 用法 |
|---------|---------|------|
| 哈希索引（HashIndex） | 等值查询 `==` | `Column(str, index=True)` 或 `Column(str, index='hash')` |
| 有序索引（SortedIndex） | 范围查询 `>`, `<`, `>=`, `<=` 和排序 | `Column(int, index='sorted')` |
| 无索引 | 不常查询的字段 | `Column(str)` 默认 |

### 建议

```python
class User(Base):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)              # 主键自动优化
    email = Column(str, index=True)                  # 等值查询多 → hash
    age = Column(int, index='sorted')                # 范围查询多 → sorted
    bio = Column(str)                                # 不常查询 → 无索引
```

- 主键查询始终是 O(1)，无需额外索引
- 只对查询频率高的列加索引
- `order_by` 使用 SortedIndex 列时，排序操作可被加速

---

## 模型设计

### 主键选择

```python
# ✅ 自动分配整数主键（推荐）
class User(Base):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)

# ✅ 指定主键值
class Config(Base):
    __tablename__ = 'configs'
    key = Column(str, primary_key=True)

# ✅ 无主键模型（日志场景）
class Log(Base):
    __tablename__ = 'logs'
    message = Column(str)
    level = Column(str)
    # Pytuck 使用内部隐式 _pytuck_rowid
```

### 类型转换

默认情况下 Pytuck 会尝试自动类型转换（宽松模式）：

```python
class User(Base):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)
    age = Column(int)       # '20' → 20（自动转换）
    strict_age = Column(int, strict=True)  # '20' → 报错！

User.create(age='20')          # OK，自动转换为 20
User.create(strict_age='20')   # ValidationError！
```

### 自定义校验器

使用 `validator` 参数对字段值进行更细粒度的约束：

```python
class User(Base):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)
    name = Column(str, validator=lambda x: len(x) <= 100)  # 限制长度
    age = Column(int, validator=[                            # 多个约束
        lambda x: x >= 0,
        lambda x: x <= 150,
    ])
    email = Column(str, validator=lambda x: '@' in x)       # 格式校验
```

- validator 在类型转换**之后**执行，接收的值已经是正确类型
- `None` 值跳过 validator（由 `nullable` 控制是否允许 `None`）
- 返回 `False` 或抛出异常时触发 `ValidationError`

### 默认值

```python
from datetime import datetime

class Post(Base):
    __tablename__ = 'posts'
    id = Column(int, primary_key=True)
    status = Column(str, default='draft')                     # 静态默认值
    created_at = Column(datetime, default_factory=datetime.now)  # 动态默认值（每次创建时调用）
    tags = Column(list, default_factory=list)                   # 每个实例独立的空列表
```

- `default`：静态值，直接赋给每个实例
- `default_factory`：无参可调用对象，每次创建实例时调用
- 两者**互斥**，不可同时设置

### 模型继承（Mixin 复用）

使用 `__abstract__ = True` 标记抽象基类，将公共列抽取到 Mixin 中复用：

```python
from datetime import datetime

class CommonBase(Base):
    """公共基类：所有模型共享的字段"""
    __abstract__ = True
    id = Column(int, primary_key=True)
    created_at = Column(datetime, default_factory=datetime.now)
    updated_at = Column(datetime, default_factory=datetime.now)

class User(CommonBase):
    __tablename__ = 'users'
    name = Column(str, nullable=False)
    email = Column(str)

class Article(CommonBase):
    __tablename__ = 'articles'
    title = Column(str)
    content = Column(str)
```

**使用建议：**

- Mixin 必须标记 `__abstract__ = True`，否则会因缺少 `__tablename__` 而报错
- 子类可以覆盖父类的同名列（例如修改默认值或添加校验）
- 支持多层继承（A → B → C）和多重继承（同时继承多个 Mixin）
- Mixin 中的 `validator`、`default`、`default_factory` 等特性会被子类完整继承

```python
# ❌ 忘记标记 __abstract__
class MyMixin(Base):
    shared_field = Column(str)  # ValidationError: 缺少 __tablename__

# ✅ 正确标记
class MyMixin(Base):
    __abstract__ = True
    shared_field = Column(str, default='')
```

---

## NULL 和空字符串处理

### 跨引擎差异

不同引擎对 `None` 和 `''` 的处理不同：

| 引擎 | `None` 保留 | `''` 保留 | 备注 |
|------|------------|----------|------|
| Binary | ✅ | ✅ | 完整类型保留 |
| JSON | ✅ | ✅ | `null` vs `""` |
| SQLite | ✅ | ✅ | `NULL` vs `''` |
| CSV | ⚠️ | ⚠️ | **无法区分 `None` 和 `''`** |
| Excel | ⚠️ | ⚠️ | 空单元格可能丢失类型信息 |
| XML | ⚠️ | ⚠️ | 空元素和缺失元素的语义差异 |

### 建议

- 如果业务逻辑依赖 `None` 和 `''` 的区分，避免使用 CSV 引擎
- 使用 Binary 或 SQLite 引擎可保证完整的类型保留

---

## 事务使用

### Session 事务

```python
# 上下文管理器（推荐）
with session.begin():
    session.add(User(name='Alice'))
    session.add(User(name='Bob'))
    # 异常时自动回滚

# Session 也支持 with 语句
with Session(db) as session:
    session.add(User(name='Alice'))
    # 正常退出 → commit
    # 异常退出 → rollback
```

### Storage 事务

```python
with db.transaction():
    db.insert('users', {'name': 'Alice'})
    db.insert('users', {'name': 'Bob'})
    # 异常时自动回滚
```

> 注意：Pytuck 不支持嵌套事务。

---

## Schema 同步

当模型定义发生变更（如新增字段），可以使用 Schema 同步功能更新表结构：

### 自动同步

```python
# 每次启动时自动同步
Base = declarative_base(db, sync_schema=True)
```

### 手动同步

```python
from pytuck import SyncOptions

# 默认选项（只添加新列）
result = session.sync_schema(User)

# 自定义选项
opts = SyncOptions(
    add_new_columns=True,
    drop_missing_columns=True,  # ⚠️ 危险：删除模型中不存在的列
)
result = session.sync_schema(User, options=opts)

if result.has_changes:
    print(f"新增列: {result.columns_added}")
```

### 注意事项

- `drop_missing_columns=True` 会删除数据库中存在但模型中不存在的列，**谨慎使用**
- `update_column_types=True` 暂未实现
- Schema 同步不会修改已有数据，只调整表结构

---

## 数据序列化

### to_dict 与 to_json

```python
user = User.get(1)

# 基础序列化
data = user.to_dict()           # Python 字典
json_str = user.to_json()       # JSON 字符串

# 字段筛选（适合 API 响应，隐藏敏感字段）
user.to_dict(exclude={'password', 'secret'})
user.to_json(include={'id', 'name', 'email'})

# 展开关联数据（避免 N+1 查询时可配合 prefetch 使用）
user.to_dict(depth=1)           # 展开一层关联
user.to_json(depth=1, indent=2) # 格式化 JSON 输出
```

### Web API 场景

```python
# 返回 JSON 响应（如 Flask / FastAPI）
@app.get('/users/{user_id}')
def get_user(user_id: int):
    user = User.get(user_id)
    return user.to_dict(exclude={'password'})

# 列表响应
@app.get('/users')
def list_users():
    users = User.all()
    return [u.to_dict(include={'id', 'name', 'email'}) for u in users]
```

---

## 性能优化

### 批量操作

```python
# ❌ 逐条插入（慢）
for i in range(10000):
    session.add(User(name=f'User_{i}'))
session.commit()

# ✅ 批量插入（快）
users = [User(name=f'User_{i}') for i in range(10000)]
session.bulk_insert(users)
session.commit()
```

### 关系预取

```python
# ❌ N+1 问题
users = User.all()
for user in users:
    print(user.orders)  # 每次访问触发一次查询

# ✅ 预取解决 N+1
from pytuck import prefetch
users = User.all()
prefetch(users, 'orders')  # 一次查询加载所有 orders
for user in users:
    print(user.orders)  # 从缓存读取，无查询
```

### 懒加载（Binary）

```python
# 大数据量场景
db = Storage(
    file_path='large_data.db',
    engine='binary',
    backend_options=BinaryBackendOptions(lazy_load=True),
)
# 只加载 schema 和索引，按需读取数据
```

懒加载同样支持加密文件——加载时仅解密索引区，读取记录时按需解密对应偏移的数据片段：

```python
# 加密 + 懒加载
db = Storage(
    file_path='large_secure.db',
    engine='binary',
    backend_options=BinaryBackendOptions(
        lazy_load=True,
        encryption='medium',
        password='my_password',
    ),
)
# 索引区在加载时解密；数据记录在 get(pk) 时按需解密
```

### 增量保存（CSV）

CSV 引擎支持增量保存——`Storage.flush()` 时仅重写发生变更的表，未变更表直接从旧 ZIP 复制：

```python
db = Storage(file_path='data.zip', engine='csv')
# ...修改 users 表...
db.flush()  # 仅重写 users 表的 CSV，其他表从旧 ZIP 直接复制
```

> 启用 ZIP 密码保护时不使用增量策略，此时仍为全量写入。

### SQLite 原生 SQL

```python
# 大数据量场景
db = Storage(
    file_path='data.sqlite',
    engine='sqlite',
    backend_options=SqliteBackendOptions(use_native_sql=True),
)
# 查询直接在数据库执行，不加载全部数据到内存
```
