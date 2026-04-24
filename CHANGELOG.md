# 更新日志

本文件记录项目的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

> [English Version](./CHANGELOG.EN.md)

> 历史版本请查看：[docs/changelog/](./docs/changelog/)

---

## [1.4.0] - 2026-04-24

### 新增

- **支持跨 storage 关联加载**
  - `Relationship` 与 `prefetch` 现在可以在不同 storage 之间解析目标模型与目标数据源
  - 异构引擎之间也可直接完成关联读取，无需 join
  - 补充了跨 storage 关联文档与回归测试

- **新增 JSON 与 orjson 性能基准脚本**
  - 覆盖 save、load、reopen 与 reopen 后首次查询等关键路径
  - 支持自定义记录规模、输出 Markdown 汇总和原始 JSON 结果
  - 自动统计输出文件体积并在临时目录完成清理

### 修复

- **增强 Excel 引擎对外部工作簿的兼容处理**
  - 将外部 Excel 表头规范化为字符串，避免内部键类型不一致
  - 过滤空值或无效的 schema / metadata 键，减少加载异常
  - 改善外部 Excel 文件与部分列名场景下的读取稳定性

- **为 `Storage.flush()` 和 `close()` 增加多线程写锁保护**
  - 关键写入路径在同一 `Storage` 实例内串行执行
  - 避免并发 flush 导致后端重复保存
  - 增加并发串行化测试覆盖

- **修正 DuckDB 的 `datetime` 类型映射**
  - `datetime` 现在映射为 `TIMESTAMPTZ`
  - 保留时区信息，提升时间字段写入与读取的准确性

### 文档与基准

- **同步更新多引擎、关联关系与 benchmark 文档**
  - 补充多引擎格式说明、配置选项与关联加载说明
  - README 与 benchmark 文档收录 JSON / orjson 对比结果及选型建议
  - 对外版本说明更新为 `1.4.0`

### 测试

- **补强引擎兼容与关系场景的回归覆盖**
  - 新增所有引擎支持类型的 round-trip 保真测试
  - 新增跨 storage 关联加载与异常处理测试
  - 补充 benchmark 类型标注与线程场景验证

### 破坏性变更

- **JSON 后端移除 `ujson` 支持**
  - `impl` 选项不再支持 `ujson`
  - JSON / JSONL 后端实现与示例已同步简化为 `json`、`orjson` 或自定义实现

- **`Relationship` 构造函数移除 `lazy` 参数**
  - 关联配置入口收敛为新的关键字参数形式
  - 需要依赖旧参数签名的调用方应同步更新
