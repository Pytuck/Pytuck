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

> [!IMPORTANT]
> `pyproject.toml` 当前仍保留 `license = {text = "MIT"}`。`uv build` 下 setuptools 会提示 `project.license` TOML table 的 deprecation warning，但不要为了消除这条 warning 直接改成 SPDX 字符串，因为该路径依赖 `setuptools>=77`，会破坏当前 Python `3.7` / `3.8` 构建兼容。只有在项目提高最低支持 Python 版本或统一升级构建链后，才切到 `license = "MIT"` / `license-files`。

## 发布检查清单

在正式发布前，建议按下面顺序执行：

1. 获取当天实际日期，避免手写错误：

   ```bash
   date '+%Y-%m-%d'
   ```

2. 确认版本号与 changelog 组织方式：
   - 更新 `pyproject.toml` 中的版本号
   - 更新 `CHANGELOG.md` 与 `CHANGELOG.EN.md`
   - 如果要把上一版从根级 changelog 归档，放到 `docs/changelog/{version}.md`

3. 同步所有用户可见文档：
   - `README.md` / `README.EN.md`
   - `CHANGELOG.md` / `CHANGELOG.EN.md`
   - 如果开发指南、benchmark 或其他公开文档有变动，也要同步对应英文文件

4. 运行发布前验证（默认依赖示例基线与 `examples/README.md` 的“推荐起步示例”保持一致）：

   ```bash
   uv run pytest tests/ -v
   uv run python examples/session_api_demo.py
   uv run python examples/active_record_demo.py
   uv build
   ```

5. 验证通过后再发布：

   ```bash
   uv publish
   # 或发布到 TestPyPI
   uv publish --index testpypi
   ```

> 如果这次变更涉及新文档、新示例或新的用户可见行为，先补齐中英文内容，再执行构建与发布。

## 相关文档

- [README 首页](../../README.md)
- [API 文档索引](../api/index.md)
- [性能基准报告](benchmark.md)
- [开发待办 TODO](../../TODO.md)
