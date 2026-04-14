# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [1.2.0] - 2026-04-14

### 变更

- **PTK7 确认为默认且长期支持的单文件格式**
  - Pytuck 默认单文件引擎现在以 PTK7 作为当前主格式
  - 后续默认方向是在 PTK7 内持续做兼容优化和性能收敛，除非出现硬阻塞，否则不再轻易推进下一代格式

- **公开层不再以 PTK5 迁移为主线**
  - README、API 文档和根包说明回到“当前产品能力”的叙事
  - PTK5 专用的公开迁移入口已移除，保留通用迁移工具路径

### 文档

- **文档结构回归当前用户视角**
  - README、API 与 benchmark 文档重新聚焦安装、用法、引擎对比、最佳实践和当前 benchmark 结果
  - 多引擎 benchmark 总表已恢复，并集中放在 `docs/guide/benchmark.md`

### 测试

- **公开契约同步到 PTK7**
  - 单文件引擎相关测试与用户可见错误口径已调整到当前 PTK7 行为
  - 保持懒加载、持久化完整性与多引擎兼容路径的测试覆盖
