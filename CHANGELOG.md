# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [1.3.0] - 2026-04-19

### 变更

- **采用现代类型注解语法**
  - 使用更现代的类型注解写法：`list[str]`、`str|None`、`type[str]` 等
  - 替代旧的 `typing.List[str]`、`typing.Optional[str]`、`typing.Type[str]` 等写法
  - 提升代码可读性和简洁性

- **恢复 Pytuck 三档加密能力**
  - 恢复并统一三档加密能力（低/中/高）在 Pytuck 引擎中的可用性
  - 明确默认行为与配置入口，确保不同安全等级下的使用路径一致
  - 对外文档与版本说明同步到 `1.3.0`

### 破坏性变更

- **最低 Python 版本要求提升至 3.10**
  - 不再支持 Python 3.8 及以下版本
  - Python 3.9 兼容性未经验证
  - 从 Python 3.10 开始正式支持
