# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [0.9.0] - 2026-03-15

### 新增

- **to_dict() 增强与 to_json()**
  - `to_dict()` 支持 `include` / `exclude` 字段筛选
  - `depth` 参数控制关联数据的序列化深度（`depth=1` 只展开一层 Relationship）
  - 新增 `to_json()` 方法，支持 `indent`、`include`、`exclude`、`depth` 参数
  - 示例：
    ```python
    user.to_dict(exclude={'password'})         # 排除敏感字段
    user.to_json(include={'id', 'name'})       # 仅保留指定字段
    user.to_dict(depth=1)                      # 展开一层关联数据
    ```

- **Column 级数据校验器（validator）**
  - `Column` 新增 `validator` 参数，支持自定义校验函数或函数列表
  - 校验在类型转换之后执行，`None` 值跳过校验
  - 返回 `False` 或抛出异常时触发 `ValidationError`
  - 示例：
    ```python
    name = Column(str, validator=lambda x: len(x) <= 100)
    age = Column(int, validator=[lambda x: x >= 0, lambda x: x <= 150])
    ```

- **模型继承支持（Mixin）**
  - 支持使用 `__abstract__ = True` 标记抽象基类，将公共列抽取到 Mixin 中复用
  - 支持多层继承（A → B → C）和多重继承（同时继承多个 Mixin）
  - 子类可覆盖父类同名列（修改默认值、添加校验等）
  - 示例：
    ```python
    class TimestampMixin(Base):
        __abstract__ = True
        created_at = Column(datetime, default_factory=datetime.now)

    class User(TimestampMixin):
        __tablename__ = 'users'
        name = Column(str)
    ```

- **Column default_factory 支持**
  - `Column` 新增 `default_factory` 参数，接受无参可调用对象，每次创建实例时调用
  - 与 `default`（静态值）互斥，不可同时设置
  - 类似 Python `dataclass` 的 `field(default_factory=...)` 设计
  - 示例：
    ```python
    created_at = Column(datetime, default_factory=datetime.now)
    tags = Column(list, default_factory=list)
    ```

- **非二进制后端增量保存**
  - 新增 Table 级别脏标记（`_data_dirty` / `_schema_dirty`）
  - `Storage.flush()` 自动跟踪变更表，仅传递变更表名给后端
  - CSV 引擎实现增量 ZIP 写入：未变更表直接从旧 ZIP 复制（二进制拷贝），仅重写变更表
  - 其他后端（JSON/Excel/XML）签名已扩展但行为不变（全量写入）
  - 启用 ZIP 密码保护时不使用增量策略，此时仍为全量写入

- **Binary 加密懒加载兼容**
  - 三种加密算法（XOR/LCG/ChaCha20）均新增 `decrypt_at()` 方法，支持随机位置解密
  - 加密文件现在支持懒加载：加载时仅解密索引区获取 `pk_offsets`，读取记录时按需解密
  - 文件格式和写入流程完全不变，纯读路径优化
  - 随机访问解密原理：
    - XOR：256 字节周期循环密钥流，偏移取模
    - LCG：O(log N) 快进算法跳到任意偏移
    - ChaCha20：天然支持随机访问（基于块计数器）

### 改进

- **临时文件安全改进**
  - 所有后端引擎使用 `tempfile.mkstemp` 替代手动构造临时文件路径
  - 临时文件创建在目标文件同目录下，确保原子 `replace()` 在同一文件系统
  - 移除不必要的 `unlink()` + `replace()` 模式，直接用 `replace()` 原子替换

### 修复

- 修复字符串匹配查询测试中数据库连接未正确关闭的问题

### 测试

- 添加 to_dict/to_json 增强功能测试
- 添加 Column validator 校验器测试
- 添加模型继承和 Mixin 测试
- 添加 Column default_factory 测试
- 添加 Table 级别脏标记和增量保存测试
- 添加加密懒加载测试（三种加密等级 + decrypt_at 一致性验证）
