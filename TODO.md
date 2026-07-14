# Pytuck 开发待办

> 这里只保留当前仍需推进的功能项；最近已经收口的工作放在最上面，避免把已完成事项继续挂在未完成列表里。

## 已收口

- [x] `1.2.1` 版本号、CHANGELOG、README / README.EN 对外口径统一
- [x] PTK7 确认为默认且长期支持的单文件格式
- [x] Session 写入路径性能收敛（`add_all()` / `flush()` / `bulk_insert()`）
- [x] 持久化语义文档化（`auto_flush`、`flush()`、`close()`）
- [x] 发布检查清单并入 `docs/guide/development.md` / `development.en.md`
- [x] 当前基线验证通过（`uv run pytest tests/ -v`、`uv build`、两个推荐示例）
- [x] 升级最低 Python 版本至 3.10+，统一 license 格式为 SPDX 字符串，消除 setuptools 警告
- [x] benchmark 原始结果归档约定文档化（结果目录、命名方式、对外引用口径）
- [x] `examples/` 运行基线收敛到推荐起步示例，并补充 smoke test
- [x] 固化“纯 Python、核心零依赖、面向 Ren'Py 等受限环境”的产品边界与架构决策
- [x] 增加零依赖 wheel、Ren'Py 集成、分层后端契约和 PTK7 损坏恢复测试
- [x] PTK7 多表增量写盘复用未变更数据块，避免无关表物化并降低峰值内存
- [x] 可选后端适配器改为按需导入，核心启动路径不加载扩展模块
- [x] 记录核心性能基线与 PTK7 增量写盘对照结果

## 近期

- 暂无（本轮已收口）

## 中期

- [ ] 梳理 `tools/migrate.py` 与当前默认 Pytuck 单文件路径的关系，补一份迁移/清理说明
- [ ] 统一 benchmark 文档与脚本的对齐口径，为后续跨仓库对比做准备

## 长期 / 生态

- [ ] 与 `pytucky` 对齐 benchmark 方法、数据集和输出格式
- [ ] 推进“Pytuck 单格式精简库”方向
- [ ] 评估长期未常用后端适配器的裁剪顺序
- [ ] 评估非核心功能拆分到独立仓库的可行性

## 备注

- 长期项只保留方向，不在这里展开成长段说明
- 破坏性清理（删除 legacy 代码、裁剪后端）必须先有影响范围与迁移方案
