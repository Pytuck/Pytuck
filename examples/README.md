# Pytuck 示例代码

本目录包含 Pytuck 的各种使用示例，每个文件都是可独立运行的完整脚本。

## 示例列表

| 文件 | 主题 | 说明 |
|------|------|------|
| `session_api_demo.py` | Session + Statement API | **推荐起步示例**。展示 `declarative_base` + `Session` + `execute()` 的完整 CRUD、事务和查询用法 |
| `active_record_demo.py` | Active Record 模式 | 展示 `CRUDBaseModel` 的 create/save/delete/filter 等模型级方法，无需 Session |
| `data_model_demo.py` | 数据模型特性 | 展示模型实例在 Session/Storage 关闭后仍可访问、可序列化等独立数据容器特性 |
| `transaction_demo.py` | 事务管理 | 展示成功提交、自动回滚、批量操作事务保护和上下文管理器 |
| `relationship_demo.py` | 关联关系 | 展示一对多、一对一、多对多（中间表）、自引用和类型提示的 Relationship 用法 |
| `type_validation_demo.py` | 类型验证与转换 | 展示宽松/严格模式、None 处理、布尔转换规则等 Column 类型行为 |
| `typing_demo.py` | 泛型类型提示 | 展示 `Select[User]`、`Result[User]` 等泛型如何提升 IDE 补全和类型推断 |
| `backend_options_demo.py` | 后端配置选项 | 展示各引擎的强类型 dataclass 选项（JSON/CSV/SQLite/Excel/XML/Pytuck） |
| `json_impl_demo.py` | JSON 实现选择 | 展示 orjson/ujson 等多种 JSON 库切换、性能对比和自定义实现 |
| `migration_tools_demo.py` | 数据迁移工具 | 展示 `migrate_engine()` 跨引擎迁移和 `import_from_database()` 外部导入 |
| `_common.py` | 内部工具 | 提供临时目录等示例共用的辅助函数（不直接运行） |

## 运行方式

```bash
# 推荐起步
uv run python examples/session_api_demo.py

# Active Record 模式
uv run python examples/active_record_demo.py

# 运行任意示例
uv run python examples/<文件名>.py
```

## API 选择指南

### Session + Statement API（推荐）

适合新项目、团队开发、需要清晰架构的场景：

```python
from pytuck import Storage, declarative_base, Session, Column, PureBaseModel
from pytuck import select, insert, update, delete
from typing import Type

db = Storage('mydb.pytuck')
Base: Type[PureBaseModel] = declarative_base(db)

class User(Base):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)
    name = Column(str)

session = Session(db)
session.execute(insert(User).values(name='Alice'))
session.commit()
```

### Active Record 模式

适合小型项目、快速原型、简单 CRUD：

```python
from pytuck import Storage, declarative_base, Column, CRUDBaseModel
from typing import Type

db = Storage('mydb.pytuck')
Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(int, primary_key=True)
    name = Column(str)

user = User.create(name='Alice')
```

## 更多资源

- [API 文档](../docs/api/index.md)
- [引擎对比与配置](../docs/api/engines.md)
- [最佳实践](../docs/api/best-practices.md)
- [开发与发布指南](../docs/guide/development.md)
