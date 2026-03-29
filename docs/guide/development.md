# Pytuck 开发与发布指南

本页汇总 README 首页之外、更偏向安装细节、贡献开发和发布维护的说明。

## 安装方式

### 从 PyPI 安装

```bash
# 基础安装（已包含 pytuck / json / jsonl / csv / sqlite）
pip install pytuck

# 安装特定功能
pip install pytuck[all]      # 所有可选依赖
pip install pytuck[duckdb]   # 仅 DuckDB 支持
pip install pytuck[excel]    # 仅 Excel 支持
pip install pytuck[xml]      # 仅 XML 支持
pip install pytuck[orjson]   # JSON / JSONL 可选加速
pip install pytuck[ujson]    # JSON / JSONL 可选加速
pip install pytuck[dev]      # 开发工具
```

### 在 uv 项目中添加依赖（推荐）

[uv](https://github.com/astral-sh/uv) 是一个极快的 Python 项目与包管理器。如果你的应用本身使用 uv 管理，推荐直接把 pytuck 添加到当前项目依赖中：

```bash
# 基础安装（已包含 pytuck / json / jsonl / csv / sqlite）
uv add pytuck

# 安装特定功能
uv add "pytuck[all]"       # 所有可选依赖
uv add "pytuck[duckdb]"    # 仅 DuckDB 支持
uv add "pytuck[excel]"     # 仅 Excel 支持
uv add "pytuck[xml]"       # 仅 XML 支持
uv add "pytuck[orjson]"    # JSON / JSONL 可选加速
uv add "pytuck[ujson]"     # JSON / JSONL 可选加速
```

## 贡献者：同步源码开发环境

如果你是克隆仓库后准备参与开发，不要使用 editable install 方式手动把项目装进当前环境，而是直接同步项目开发环境：

```bash
# 克隆仓库
git clone https://github.com/Pytuck/Pytuck.git
cd pytuck

# 同步开发环境（包含测试与可选引擎依赖）
uv sync --extra dev

# 运行测试或示例
uv run pytest tests/ -v
uv run python examples/sqlalchemy20_api_demo.py
```

## 打包与发布

```bash
# 构建 wheel 和源码分发包
uv build

# 上传到 PyPI（使用已配置凭证，或显式传入 token）
uv publish
# uv publish --token $PYPI_TOKEN

# 上传到 TestPyPI（需先在 pyproject.toml 中配置对应 index）
uv publish --index testpypi
# uv publish --index testpypi --token $TEST_PYPI_TOKEN
```

> `uv publish --index testpypi` 依赖已配置的 `[[tool.uv.index]]` 条目，其中应包含 `url` 和 `publish-url`。

## 相关文档

- [README 首页](../../README.md)
- [API 文档索引](../api/index.md)
- [性能基准报告](benchmark.md)
- [开发待办 TODO](../../TODO.md)
