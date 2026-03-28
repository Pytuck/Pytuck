# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [1.0.0] - 2026-03-29

### 新增

- **DuckDB 原生后端**
  - 新增 `duckdb` 可选依赖与原生后端实现
  - 支持多 schema、原生 SQL、表备注/列备注与服务端分页
  - 保持与现有 `Storage` / `Session` / ORM API 一致，只需切换引擎与选项即可使用

- **JSONL ZIP 后端**
  - 新增 `jsonl` 引擎，外层使用 ZIP 容器
  - 每张表单独存储为 `.jsonl` 文件，统一 `_metadata.json`
  - 已接入迁移工具、benchmark 与引擎文档矩阵

### 变更

- **Pytuck 单文件引擎正式定版**
  - 公开引擎名 `binary` 正式更名为 `pytuck`
  - 默认单文件扩展名从 `.db` 改为 `.pytuck`
  - 单文件格式仅保留 PTK5，停止维护 v4/PTK4 兼容
  - sidecar WAL 文件名改为隐藏形式 `.<name>.wal`

- **公开入口同步到 1.0.0 语义**
  - `Storage` 默认引擎、迁移工具默认目标引擎、README、docs/api、TODO 与 benchmark 统一改为 `pytuck`
  - 单文件引擎的对外说明统一改为 Pytuck / `.pytuck` / PTK5

### 改进

- **依赖与工作流整理**
  - 保持默认安装零外部依赖，DuckDB / Excel / XML / JSON 加速能力均通过 extras 提供
  - GitHub Actions 与 benchmark 工作流切换为 uv 驱动

- **文档与基准同步**
  - README 与 API 文档补充 DuckDB、JSONL、CSV 体积优势、PyPy 复测与引擎选型说明
  - 明确“十万级”主要指单张热点表，并补充 DuckDB 对 `None` / `''` 的处理说明

### 测试

- 补齐 DuckDB / JSONL / Pytuck 改名后的测试覆盖
- benchmark 脚本纳入 DuckDB、JSONL 与 PyPy 复测结果
- 同步更新现有引擎矩阵、迁移工具与文档示例
