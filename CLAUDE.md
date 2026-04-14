# Pytuck — 精简项目协作要点（CLAUDE.md）

本文件为项目必须遵守的精简约定，便于快速查阅。所有规范以中文描述，代码保持英文。

核心约定（一屏速览）
- 语言：项目内交流、注释与文档必须使用中文。
- 环境：使用 uv 管理依赖与运行，项目虚拟环境位于 .venv；不要依赖系统 python/pip/pytest。
- 模型模式：支持两种基类：
  - PureBaseModel（纯模型）：数据定义 + Session/Statement 操作。
  - CRUDBaseModel（Active Record）：在 PureBaseModel 基础上提供 create/save/delete 等方法。使用 declarative_base(db) 或 declarative_base(db, crud=True)。
- 持久化语义（必须注意）：默认不自动写盘 —— commit()/save() 只修改内存，必须调用 storage.flush() 或 storage.close() 才写入磁盘。生产环境建议使用 auto_flush=True。
- 路径处理：所有文件路径必须使用 pathlib.Path；公共 API 接受路径时应立即转换并调用 expanduser()。
- 类型提示（强制）：函数与方法必须有完整的参数和返回值类型注解，使用 typing 模块与 TYPE_CHECKING 以避免循环引用。
- 目录边界：pytuck/ 根目录只允许 __init__.py 和 py.typed；tests/ 专用于测试，examples/ 放示例。
- 文档双语同步：中文 README 或 CHANGELOG 更新时，必须同时更新对应英文文件（README.EN.md / CHANGELOG.EN.md）。
- CHANGELOG 发布规则：更新/发布前先运行系统日期命令获取实际日期；发布新版本时将旧版本归档到 docs/changelog/{version}.md（包含中英文内容）。
- 测试（强制）：修改后必须运行全部测试并确保通过，使用 pytest（通过 uv 运行）；测试文件和用例遵循命名规范（test_ 前缀等）。

常用命令（在项目根目录，通过 uv）
- 安装开发依赖：uv sync --extra dev
- 运行全部测试：uv run pytest tests/ -v
- 运行单个测试：uv run pytest tests/test_orm.py -v
- 运行示例：uv run python examples/new_api_demo.py

说明与延伸
- 本文件保留核心约束；更详细的开发指南、设计记录与长任务放在 docs/ 与 TODO.md 中。
- 如需迁移或向后兼容，优先使用 tools/migrate.py 等现有工具，不在核心库中引入大量历史分支。