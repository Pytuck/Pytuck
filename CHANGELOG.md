# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [1.2.1] - 2026-04-14

### 变更

- **PTK7 确认为默认且长期支持的单文件格式**
  - Pytuck 默认单文件引擎现在以 PTK7 作为当前主格式
  - 后续默认方向是在 PTK7 内持续做兼容优化和性能收敛，除非出现硬阻塞，否则不再轻易推进下一代格式

- **公开层不再以 PTK5 迁移为主线**
  - README、API 文档和根包说明回到“当前产品能力”的叙事
  - PTK5 专用的公开迁移入口已移除，保留通用迁移工具路径

### 性能

- **Session 批量写入路径收敛**
  - 修复 `Session.add()` 对 `_new_objects` 的 O(N²) 去重瓶颈，100k `session.add_all() + commit()` 从 `47.59s` 降到 `0.72s`
  - `Session.flush()` 现在按模型类分组复用 `storage.bulk_insert()`；内存模式移除冗余 readback，仍保留逐条 `before_insert` / `after_insert` 语义
  - `Session.bulk_insert()` 在同口径下保持 `0.41s`，未出现性能回退

### 文档

- **文档结构回归当前用户视角**
  - README、API 与 benchmark 文档重新聚焦安装、用法、引擎对比、最佳实践和当前 benchmark 结果
  - README、benchmark 与最佳实践新增 `session.add_all() + commit()` / `session.bulk_insert()` 的写入路径对比和选型建议
  - 对外版本统一更新为 `1.2.1`，本次直接在根级 changelog 收口，不新增历史归档文件

### 测试

- **公开契约同步到 PTK7**
  - 单文件引擎相关测试与用户可见错误口径已调整到当前 PTK7 行为
  - 保持懒加载、持久化完整性与多引擎兼容路径的测试覆盖

- **新增写入路径保护测试**
  - 覆盖 `add_all()` 去重复杂度、`flush()` 批量插入路径、mixed model classes 分组处理，以及 `add_all() + commit()` 的逐条事件语义
  - 全量测试 `1114` 项通过
