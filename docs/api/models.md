# 模型定义 API

## Column

列定义描述符，用于在模型类中声明字段。

```python
from pytuck import Column
```

### 构造函数

```python
Column(
    col_type: type,              # Python 类型
    *,
    name: Optional[str] = None,  # 存储列名（默认使用属性名）
    nullable: bool = True,       # 是否允许 None
    primary_key: bool = False,   # 是否为主键
    index: Union[bool, str] = False,  # 索引类型
    default: Any = None,         # 静态默认值
    default_factory: Optional[Callable[[], Any]] = None,  # 默认值工厂函数
    foreign_key: Optional[tuple] = None,  # 外键 ('table', 'column')
    comment: Optional[str] = None,  # 列备注
    strict: bool = False,        # 严格模式（禁止类型转换）
    validator: Optional[Union[Callable, List[Callable]]] = None,  # 自定义校验函数
)
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `col_type` | `type` | 必填 | Python 类型，支持 `int`, `str`, `float`, `bool`, `bytes`, `datetime`, `date`, `timedelta`, `list`, `dict` |
| `name` | `Optional[str]` | `None` | 数据库存储的列名。`None` 时使用 Python 属性名 |
| `nullable` | `bool` | `True` | 是否允许 `None` 值 |
| `primary_key` | `bool` | `False` | 是否为主键。每个模型最多一个主键 |
| `index` | `Union[bool, str]` | `False` | `False`=无索引, `True`或`'hash'`=哈希索引, `'sorted'`=有序索引 |
| `default` | `Any` | `None` | 静态默认值。与 `default_factory` 互斥 |
| `default_factory` | `Optional[Callable[[], Any]]` | `None` | 默认值工厂函数（无参可调用对象），每次创建实例时调用。与 `default` 互斥 |
| `foreign_key` | `Optional[tuple]` | `None` | 外键引用 `('表名', '列名')` |
| `comment` | `Optional[str]` | `None` | 列备注信息 |
| `strict` | `bool` | `False` | 严格模式：`True` 时类型不匹配直接报错，不自动转换 |
| `validator` | `Optional[Union[Callable, List[Callable]]]` | `None` | 自定义校验函数或校验函数列表（详见下方说明） |

### 自定义校验器（validator）

`validator` 参数支持传入自定义校验函数，在类型转换**之后**对值进行额外验证。

**校验规则：**
- 校验函数接收类型转换后的值，返回 `True` 表示通过
- 返回 `False` 或抛出异常则触发 `ValidationError`
- `None` 值跳过校验（`None` 的合法性由 `nullable` 参数控制）

**单个校验器：**

```python
# 限制字符串长度
name = Column(str, validator=lambda x: len(x) <= 100)

# 检查邮箱格式
email = Column(str, validator=lambda x: '@' in x)
```

**多个校验器（列表）：**

```python
# 值范围约束
age = Column(int, validator=[
    lambda x: x >= 0,    # 不小于 0
    lambda x: x <= 150,  # 不大于 150
])
```

**自定义校验函数（可抛出异常提供详细错误信息）：**

```python
def check_email(value):
    if '@' not in value:
        raise ValueError("Invalid email format")
    return True

email = Column(str, validator=check_email)
```

### 默认值工厂（default_factory）

`default_factory` 参数接受一个无参可调用对象，**每次创建模型实例时调用**生成默认值。适用于需要动态默认值的场景。

**与 `default` 的区别：**
- `default`：静态值，所有实例共享同一个默认值
- `default_factory`：工厂函数，每次实例化时调用，生成新的值
- 两者**互斥**，不可同时设置

> `default_factory` 仅在 ORM 层生效，不会写入后端引擎的表结构元数据中。

**自动创建时间：**

```python
from datetime import datetime

class Article(Base):
    __tablename__ = 'articles'
    id = Column(int, primary_key=True)
    title = Column(str)
    created_at = Column(datetime, default_factory=datetime.now)

article = Article(title='Hello')
print(article.created_at)  # 2024-01-15 10:30:00.123456
```

**自增序列号：**

```python
counter = {'value': 0}

def next_seq():
    counter['value'] += 1
    return counter['value']

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(int, primary_key=True)
    seq = Column(int, default_factory=next_seq)
```

**使用 lambda：**

```python
import time

class Event(Base):
    __tablename__ = 'events'
    id = Column(int, primary_key=True)
    timestamp = Column(float, default_factory=time.time)
    tags = Column(list, default_factory=list)  # 每个实例一个新列表
```

### 索引类型

| 值 | 索引类型 | 适用场景 |
|----|---------|---------|
| `False` | 无索引 | 不常查询的字段 |
| `True` 或 `'hash'` | 哈希索引（HashIndex） | 等值查询加速（`==`） |
| `'sorted'` | 有序索引（SortedIndex） | 范围查询（`>`, `<`, `>=`, `<=`）和排序加速 |

### 查询表达式方法

Column 支持 Python 运算符构建查询条件，返回 `BinaryExpression`：

```python
# 比较运算符
User.age == 20        # 等于
User.age != 20        # 不等于
User.age > 18         # 大于
User.age >= 18        # 大于等于
User.age < 30         # 小于
User.age <= 30        # 小于等于

# IN 查询
User.age.in_([18, 19, 20])

# 字符串匹配（大小写不敏感）
User.name.contains('ali')      # 包含 → LIKE '%ali%'
User.name.startswith('Al')     # 前缀 → LIKE 'Al%'
User.email.endswith('.com')    # 后缀 → LIKE '%.com'
```

### 实例方法

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `to_dict()` | `dict` | 将列元数据转为字典 |
| `validate(value)` | `Any` | 验证并转换值为列类型 |
| `has_default()` | `bool` | 判断列是否设置了默认值（`default` 或 `default_factory`） |
| `resolve_default()` | `Any` | 获取解析后的默认值。`default_factory` 时调用工厂函数生成新值 |

### 类型转换规则（宽松模式）

| Python 类型 | 转换规则 | 示例 |
|------------|---------|------|
| `int` | `int(value)` | `'123'` → `123` |
| `float` | `float(value)` | `'3.14'` → `3.14` |
| `str` | `str(value)` | `123` → `'123'` |
| `bool` | 特殊规则 | `'true'`, `1` → `True`; `'false'`, `0` → `False` |
| `bytes` | `str.encode()` | `'hello'` → `b'hello'` |
| `datetime` | ISO 8601 解析 | `'2024-01-15T10:30:00'` → `datetime` |
| `date` | ISO 8601 解析 | `'2024-01-15'` → `date` |
| `timedelta` | 秒数转换 | `3600.0` → `timedelta(hours=1)` |
| `list` | JSON 解析 | `'[1,2,3]'` → `[1, 2, 3]` |
| `dict` | JSON 解析 | `'{"a":1}'` → `{'a': 1}` |

---

## declarative_base()

创建模型基类的工厂函数，将 Storage 实例绑定到基类。

```python
from pytuck import Storage, declarative_base
```

### 签名

```python
def declarative_base(
    storage: Storage,
    *,
    crud: bool = False,
    sync_schema: bool = False,
    sync_options: Optional[SyncOptions] = None,
) -> Union[Type[PureBaseModel], Type[CRUDBaseModel]]
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `storage` | `Storage` | 必填 | 数据库存储实例 |
| `crud` | `bool` | `False` | `False`=返回 `PureBaseModel` 基类；`True`=返回 `CRUDBaseModel` 基类 |
| `sync_schema` | `bool` | `False` | 是否在模型定义时自动同步表结构（适用于表已存在的场景） |
| `sync_options` | `Optional[SyncOptions]` | `None` | Schema 同步选项（仅 `sync_schema=True` 时生效） |

### 使用示例

```python
from typing import Type
from pytuck import Storage, declarative_base, PureBaseModel, CRUDBaseModel

db = Storage(file_path='mydb.pytuck')

# 纯模型模式（默认）
Base: Type[PureBaseModel] = declarative_base(db)

# Active Record 模式
Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

# 启用 Schema 同步（重启时自动添加新列）
Base = declarative_base(db, sync_schema=True)
```

### 行为说明

当子类继承返回的 Base 时，会自动：
1. 收集所有 `Column` 和 `Relationship` 定义
2. 验证 `__tablename__` 存在且主键数量 ≤ 1
3. 在 Storage 中创建表（若不存在）或同步表结构（若 `sync_schema=True`）
4. 在 Storage 中注册模型类

---

## PureBaseModel

纯模型基类，仅定义数据结构，通过 `Session` 操作数据。

### 类属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `__tablename__` | `str` | 表名（必须定义） |
| `__table_comment__` | `Optional[str]` | 表备注（可选） |
| `__columns__` | `Dict[str, Column]` | 列定义映射（自动收集） |
| `__primary_key__` | `Optional[str]` | 主键列名（`None` 表示无主键） |
| `__relationships__` | `Dict[str, Relationship]` | 关联关系映射（自动收集） |
| `__storage__` | `Optional[Storage]` | 绑定的 Storage 实例 |

### 实例方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `to_dict()` | `to_dict(use_column_names=False, include=None, exclude=None, depth=0) -> Dict[str, Any]` | 转为字典（详见下方说明） |
| `to_json()` | `to_json(use_column_names=False, include=None, exclude=None, depth=0, ensure_ascii=False, indent=None) -> str` | 转为 JSON 字符串 |
| `__repr__()` | `-> str` | 字符串表示，显示主键值 |

#### to_dict() 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_column_names` | `bool` | `False` | `True` 时键使用存储列名（`Column.name`），否则使用属性名 |
| `include` | `Optional[Set[str]]` | `None` | 只包含指定的字段名集合。与 `exclude` 同时传入时 `include` 优先 |
| `exclude` | `Optional[Set[str]]` | `None` | 排除指定的字段名集合 |
| `depth` | `int` | `0` | 关联数据展开深度。`0`=不展开 Relationship，`1`=展开一层 |

```python
user = User(name='Alice', age=25)

# 基本用法
user.to_dict()                           # {'id': 1, 'name': 'Alice', 'age': 25}
user.to_dict(include={'name', 'age'})    # {'name': 'Alice', 'age': 25}
user.to_dict(exclude={'age'})            # {'id': 1, 'name': 'Alice'}

# 展开关联数据
user.to_dict(depth=1)                    # {'id': 1, 'name': 'Alice', 'age': 25, 'orders': [...]}
```

#### to_json() 参数

继承 `to_dict()` 的所有参数，额外支持：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ensure_ascii` | `bool` | `False` | 是否强制 ASCII 编码（`False` 支持中文直接输出） |
| `indent` | `Optional[int]` | `None` | 缩进空格数（`None` 为紧凑输出） |

自动处理 `datetime`→ISO 字符串、`date`→ISO 字符串、`timedelta`→秒数、`bytes`→Base64 编码。

```python
user.to_json()                           # '{"name": "Alice", "age": 25}'
user.to_json(indent=2)                   # 格式化输出
user.to_json(include={'name'})           # '{"name": "Alice"}'
user.to_json(depth=1)                    # 包含展开的关联数据
```

### 无主键模型

模型可以不定义主键，适用于日志表、事件表等场景：

```python
class Log(Base):
    __tablename__ = 'logs'
    message = Column(str)
    level = Column(str)
    # 无 primary_key=True 的列
    # Pytuck 会使用内部隐式 _pytuck_rowid
```

---

## CRUDBaseModel

Active Record 基类，继承 `PureBaseModel`，包含 CRUD 方法。

```python
Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)
```

### 类方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `create()` | `create(**kwargs) -> CRUDBaseModel` | 创建并保存实例 |
| `get()` | `get(pk: Any) -> Optional[CRUDBaseModel]` | 按主键查询 |
| `filter()` | `filter(*expressions) -> Query` | 条件查询（表达式语法） |
| `filter_by()` | `filter_by(**kwargs) -> Query` | 等值查询 |
| `all()` | `all() -> List[CRUDBaseModel]` | 获取全部记录 |
| `bulk_insert()` | `bulk_insert(instances: List) -> List[Any]` | 批量插入，返回主键列表 |
| `bulk_update()` | `bulk_update(instances: List) -> int` | 批量更新，返回更新数 |

### 实例方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `save()` | `save() -> None` | 保存（新建或更新） |
| `delete()` | `delete() -> None` | 删除当前记录 |
| `refresh()` | `refresh() -> None` | 从数据库重新加载最新数据 |

### 使用示例

```python
# 创建
user = User.create(name='Alice', age=20)

# 查询
user = User.get(1)
users = User.filter(User.age >= 18).order_by('name').all()
users = User.filter_by(name='Alice').all()
all_users = User.all()

# 更新
user.name = 'Bob'
user.save()

# 删除
user.delete()

# 批量操作
users = [User(name='A'), User(name='B'), User(name='C')]
pks = User.bulk_insert(users)
```

---

## Relationship

关联关系描述符，支持一对多和多对一关联；当前真实行为是首次访问时加载并自动缓存结果。

```python
from pytuck.core.orm import Relationship
```

### 构造函数

```python
Relationship(
    target_model: Union[str, Type[PureBaseModel]],  # 目标模型类或表名
    foreign_key: str,           # 外键字段名
    lazy: bool = True,          # 保留兼容参数，当前实现仍为首次访问时加载
    back_populates: Optional[str] = None,  # 反向属性名
    uselist: Optional[bool] = None,  # 返回类型
    storage: Optional[Storage] = None,  # 显式指定目标模型所在的 Storage
)
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `target_model` | `Union[str, Type]` | 必填 | 目标模型类或表名字符串（推荐使用表名，支持前向引用） |
| `foreign_key` | `str` | 必填 | 外键字段名 |
| `lazy` | `bool` | `True` | 保留兼容参数；当前实现无论取值如何，都是首次访问时查询并缓存结果 |
| `back_populates` | `Optional[str]` | `None` | 反向关联的属性名 |
| `uselist` | `Optional[bool]` | `None` | `None`=自动判断, `True`=返回列表, `False`=返回单个对象 |
| `storage` | `Optional[Storage]` | `None` | 可选。目标模型不在当前模型绑定的 storage 中时，可显式指定目标模型所在的 `Storage`，用于按表名解析目标模型 |

### 使用示例

```python
class User(Base):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)
    name = Column(str)
    orders: List['Order'] = Relationship('orders', foreign_key='user_id')  # type: ignore

class Order(Base):
    __tablename__ = 'orders'
    id = Column(int, primary_key=True)
    user_id = Column(int)
    amount = Column(float)
    user: Optional[User] = Relationship('users', foreign_key='user_id')  # type: ignore

# 自引用（树形结构）
class Category(Base):
    __tablename__ = 'categories'
    id = Column(int, primary_key=True)
    parent_id = Column(int, nullable=True)
    parent: Optional['Category'] = Relationship(
        'categories', foreign_key='parent_id', uselist=False
    )  # type: ignore
    children: List['Category'] = Relationship(
        'categories', foreign_key='parent_id', uselist=True
    )  # type: ignore

# 跨 storage 场景：按表名引用目标模型时，显式指定目标 storage
product_db = Storage(file_path='products.sqlite', engine='sqlite')
favorite_db = Storage(file_path='favorites.json', engine='json')

ProductBase = declarative_base(product_db, crud=True)
FavoriteBase = declarative_base(favorite_db, crud=True)

class Product(ProductBase):
    __tablename__ = 'products'
    id = Column(int, primary_key=True)
    name = Column(str)

class UserFavorite(FavoriteBase):
    __tablename__ = 'favorites'
    id = Column(int, primary_key=True)
    product_id = Column(int)
    product: Optional[Product] = Relationship(
        'products',
        foreign_key='product_id',
        storage=product_db,
    )  # type: ignore
```

### 行为说明

- **当前真实行为**：首次访问关联属性时才执行查询，并把结果缓存到实例上；`lazy=False` 目前不会改为 eager load
- **自动判断方向**：
  - 如果 `foreign_key` 在当前模型中 → 多对一（返回单个对象）
  - 如果 `foreign_key` 在目标模型中 → 一对多（返回列表）
  - 自引用场景需用 `uselist` 显式指定
- **批量预取**：如需避免 N+1 查询，请使用 `prefetch(users, 'orders')` 或 `select(User).options(prefetch('orders'))`

---

## 模型继承

Pytuck 支持通过抽象基类（Mixin）复用列定义，语义与 SQLAlchemy 的 `__abstract__` 一致。

### __abstract__ 属性

| 属性值 | 含义 |
|--------|------|
| `__abstract__ = True` | 抽象类 / Mixin，不创建数据库表，列定义供子类继承 |
| 未设置 / `False` | 具体模型，必须定义 `__tablename__`，会创建表 |

**规则：**
- 设置 `__abstract__ = True` 的类不会在 Storage 中创建表
- 未设置 `__abstract__` 且未定义 `__tablename__` 的类会抛出 `ValidationError`
- 具体子类的 `__abstract__` 会被自动设为 `False`

### 基本用法

```python
from datetime import datetime

class TimestampMixin(Base):
    __abstract__ = True
    created_at = Column(datetime, default_factory=datetime.now)
    updated_at = Column(datetime, default_factory=datetime.now)

class User(TimestampMixin):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)
    name = Column(str)

# User 自动拥有 id, name, created_at, updated_at 四个列
user = User(name='Alice')
print(user.created_at)  # datetime 对象
```

### 多层继承

```python
class BaseMixin(Base):
    __abstract__ = True
    id = Column(int, primary_key=True)

class AuditMixin(BaseMixin):
    __abstract__ = True
    created_by = Column(str, default='system')

class Article(AuditMixin):
    __tablename__ = 'articles'
    title = Column(str)

# Article 拥有 id, created_by, title 三个列
```

### 多重继承（多个 Mixin）

```python
class SoftDeleteMixin(Base):
    __abstract__ = True
    is_deleted = Column(bool, default=False)

class TagMixin(Base):
    __abstract__ = True
    tag = Column(str, default='')

class Post(SoftDeleteMixin, TagMixin):
    __tablename__ = 'posts'
    id = Column(int, primary_key=True)
    content = Column(str)

# Post 拥有 id, content, is_deleted, tag 四个列
```

### 子类覆盖父类列

子类可以重新定义同名列，覆盖父类的列定义：

```python
class DefaultMixin(Base):
    __abstract__ = True
    status = Column(str, default='inactive')

class ActiveModel(DefaultMixin):
    __tablename__ = 'active_models'
    id = Column(int, primary_key=True)
    status = Column(str, default='active')  # 覆盖父类默认值

model = ActiveModel()
print(model.status)  # 'active'
```

### 同一 Mixin 复用

一个 Mixin 可以被多个具体模型继承，各模型独立建表：

```python
class CommonMixin(Base):
    __abstract__ = True
    id = Column(int, primary_key=True)
    status = Column(str, default='active')

class User(CommonMixin):
    __tablename__ = 'users'
    name = Column(str)

class Order(CommonMixin):
    __tablename__ = 'orders'
    amount = Column(float)

# users 表和 orders 表各自独立，都拥有 id 和 status 列
```

### Mixin 中的 validator 和 default_factory

Mixin 中定义的 `validator`、`default_factory` 等列特性会被子类完整继承：

```python
class ValidatedMixin(Base):
    __abstract__ = True
    score = Column(int, validator=lambda x: 0 <= x <= 100)

class Student(ValidatedMixin):
    __tablename__ = 'students'
    id = Column(int, primary_key=True)
    name = Column(str)

Student(name='Alice', score=85)   # OK
Student(name='Bob', score=150)    # ValidationError
```
