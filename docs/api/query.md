# 查询系统 API

## 语句构建器

### select()

创建 SELECT 语句。

```python
from pytuck import select

stmt = select(User)
stmt = select(User).where(User.age >= 18)
stmt = select(User).where(User.age >= 18).order_by('name').limit(10)
```

### insert()

创建 INSERT 语句。

```python
from pytuck import insert

stmt = insert(User).values(name='Alice', age=20)
```

### update()

创建 UPDATE 语句。

```python
from pytuck import update

stmt = update(User).where(User.id == 1).values(age=21)
```

### delete()

创建 DELETE 语句。

```python
from pytuck import delete

stmt = delete(User).where(User.id == 1)
```

---

## Select

SELECT 语句构建器，支持链式调用。

### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `where()` | `where(*expressions) -> Select[T]` | 添加 WHERE 条件 |
| `filter_by()` | `filter_by(**kwargs) -> Select[T]` | 等值查询 |
| `order_by()` | `order_by(field, desc=False) -> Select[T]` | 排序 |
| `limit()` | `limit(n) -> Select[T]` | 限制返回数量 |
| `offset()` | `offset(n) -> Select[T]` | 偏移 |
| `options()` | `options(*opts) -> Select[T]` | 添加查询选项（如 prefetch） |

### 使用示例

```python
from pytuck import select, or_, and_, not_, prefetch

# 基本查询
stmt = select(User).where(User.age >= 18)

# 等值查询
stmt = select(User).filter_by(name='Alice', active=True)

# 多条件（AND 语义）
stmt = select(User).where(User.age >= 18, User.active == True)

# OR 条件
stmt = select(User).where(or_(User.role == 'admin', User.role == 'moderator'))

# 复杂组合
stmt = select(User).where(
    User.active == True,
    or_(User.role == 'admin', and_(User.age >= 21, User.verified == True))
)

# 排序 + 分页
stmt = select(User).order_by('age', desc=True).order_by('name').limit(20).offset(40)

# 关系预取
stmt = select(User).options(prefetch('orders'))

# 字符串匹配
stmt = select(User).where(User.name.contains('ali'))
stmt = select(User).where(User.name.startswith('Al'))
stmt = select(User).where(User.email.endswith('.com'))
```

---

## Insert / Update / Delete

### Insert

```python
stmt = insert(User).values(name='Alice', age=20)
result = session.execute(stmt)
new_id = result.inserted_primary_key
```

### Update

```python
stmt = update(User).where(User.id == 1).values(age=21)
result = session.execute(stmt)
affected = result.rowcount()
```

### Delete

```python
stmt = delete(User).where(User.id == 1)
result = session.execute(stmt)
affected = result.rowcount()
```

---

## Query 构建器

旧风格查询构建器，通过 `Session.query()` 或 `CRUDBaseModel.filter()` 创建。

```python
from pytuck import Query
```

### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `filter()` | `filter(*expressions) -> Query[T]` | 添加表达式条件 |
| `filter_by()` | `filter_by(**kwargs) -> Query[T]` | 等值查询 |
| `order_by()` | `order_by(field, desc=False) -> Query[T]` | 排序 |
| `limit()` | `limit(n) -> Query[T]` | 限制数量 |
| `offset()` | `offset(n) -> Query[T]` | 偏移 |
| `all()` | `all() -> List[T]` | 返回所有结果 |
| `first()` | `first() -> Optional[T]` | 返回第一条 |
| `count()` | `count() -> int` | 返回记录数 |

```python
# 通过 Session
users = session.query(User).filter(User.age >= 18).order_by('name').all()

# 通过 CRUDBaseModel
users = User.filter(User.age >= 18).order_by('name').all()
users = User.filter_by(name='Alice').all()
```

---

## BinaryExpression

由 Column 运算符生成的二元表达式。

### Column 支持的运算符

```python
User.age == 20        # 等于
User.age != 20        # 不等于
User.age > 18         # 大于
User.age >= 18        # 大于等于
User.age < 30         # 小于
User.age <= 30        # 小于等于
```

### Column 方法

```python
User.age.in_([18, 19, 20])         # IN 查询
User.name.contains('ali')          # 包含（大小写不敏感）
User.name.startswith('Al')         # 前缀匹配（大小写不敏感）
User.email.endswith('.com')        # 后缀匹配（大小写不敏感）
```

---

## 逻辑操作符

### or_()

OR 组合（至少 2 个表达式）。

```python
from pytuck import or_

stmt = select(User).where(or_(User.age >= 18, User.vip == True))
```

### and_()

AND 组合（至少 2 个表达式）。主要用于与 `or_()` 嵌套。

```python
from pytuck import and_

stmt = select(User).where(or_(
    User.role == 'admin',
    and_(User.age >= 21, User.verified == True)
))
```

> 注意：`where()` 的多参数默认就是 AND 语义，`and_()` 主要用于嵌套组合。

### not_()

NOT 取反。

```python
from pytuck import not_

stmt = select(User).where(not_(User.banned == True))
```

---

## Result

SELECT 查询结果包装器。

```python
from pytuck import Result
```

### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `all()` | `all() -> List[T]` | 返回所有结果为模型实例列表 |
| `first()` | `first() -> Optional[T]` | 返回第一个结果 |
| `one()` | `one() -> T` | 返回唯一结果（必须恰好一条，否则抛异常） |
| `one_or_none()` | `one_or_none() -> Optional[T]` | 返回唯一结果或 None（最多一条） |
| `rowcount()` | `rowcount() -> int` | 返回结果数量 |

```python
result = session.execute(select(User).where(User.age >= 18))

users = result.all()          # List[User]
user = result.first()         # Optional[User]
user = result.one()           # User（必须恰好一条）
user = result.one_or_none()   # Optional[User]（最多一条）
count = result.rowcount()     # int
```

---

## CursorResult

CUD（Create/Update/Delete）操作结果包装器。

```python
from pytuck import CursorResult
```

### 方法和属性

| 成员 | 类型 | 说明 |
|------|------|------|
| `rowcount()` | `int` | 受影响的行数 |
| `inserted_primary_key` | `Any` | 插入记录的主键（仅 INSERT） |

```python
# INSERT
result = session.execute(insert(User).values(name='Alice'))
pk = result.inserted_primary_key
count = result.rowcount()  # 1

# UPDATE / DELETE
result = session.execute(update(User).where(User.age < 18).values(active=False))
affected = result.rowcount()
```

> 注意：`all()`、`first()`、`one()`、`one_or_none()` 在 CursorResult 上调用会抛出 `UnsupportedOperationError`。

---

## Condition（内部类）

查询条件，通常不直接创建，由 `BinaryExpression.to_condition()` 生成。

```python
from pytuck.query.builder import Condition

cond = Condition('age', '>=', 18)
cond.evaluate({'age': 20})  # True
```

支持的操作符：`=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `LIKE`, `STARTSWITH`, `ENDSWITH`

## CompositeCondition（内部类）

组合条件，支持 `AND` / `OR` / `NOT` 逻辑。

```python
from pytuck.query.builder import CompositeCondition, Condition

cond = CompositeCondition('AND', [
    Condition('age', '>=', 18),
    Condition('active', '=', True),
])
cond.evaluate({'age': 20, 'active': True})  # True
```
