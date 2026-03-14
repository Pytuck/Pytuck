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
    default: Any = None,         # 默认值（值或可调用对象）
    foreign_key: Optional[tuple] = None,  # 外键 ('table', 'column')
    comment: Optional[str] = None,  # 列备注
    strict: bool = False,        # 严格模式（禁止类型转换）
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
| `default` | `Any` | `None` | 默认值。可以是值或可调用对象（如 `datetime.now`） |
| `foreign_key` | `Optional[tuple]` | `None` | 外键引用 `('表名', '列名')` |
| `comment` | `Optional[str]` | `None` | 列备注信息 |
| `strict` | `bool` | `False` | 严格模式：`True` 时类型不匹配直接报错，不自动转换 |

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

db = Storage(file_path='mydb.db')

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
| `to_dict()` | `to_dict(use_column_names: bool = False) -> Dict[str, Any]` | 转为字典。`use_column_names=True` 时键使用存储列名 |
| `__repr__()` | `-> str` | 字符串表示，显示主键值 |

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

关联关系描述符，支持一对多和多对一关联，延迟加载 + 自动缓存。

```python
from pytuck.core.orm import Relationship
```

### 构造函数

```python
Relationship(
    target_model: Union[str, Type[PureBaseModel]],  # 目标模型类或表名
    foreign_key: str,           # 外键字段名
    lazy: bool = True,          # 延迟加载
    back_populates: Optional[str] = None,  # 反向属性名
    uselist: Optional[bool] = None,  # 返回类型
)
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `target_model` | `Union[str, Type]` | 必填 | 目标模型类或表名字符串（推荐使用表名，支持前向引用） |
| `foreign_key` | `str` | 必填 | 外键字段名 |
| `lazy` | `bool` | `True` | 是否延迟加载（首次访问时才查询） |
| `back_populates` | `Optional[str]` | `None` | 反向关联的属性名 |
| `uselist` | `Optional[bool]` | `None` | `None`=自动判断, `True`=返回列表, `False`=返回单个对象 |

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
```

### 行为说明

- **延迟加载**：首次访问关联属性时才执行查询
- **自动缓存**：查询结果缓存到实例，后续访问不再查询
- **自动判断方向**：
  - 如果 `foreign_key` 在当前模型中 → 多对一（返回单个对象）
  - 如果 `foreign_key` 在目标模型中 → 一对多（返回列表）
  - 自引用场景需用 `uselist` 显式指定
