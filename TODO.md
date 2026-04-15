# Pytuck 开发待办

> 这里只保留当前仍需推进的功能项；最近已经收口的工作放在最上面，避免把已完成事项继续挂在未完成列表里。

## 已收口

- [x] `1.2.1` 版本号、CHANGELOG、README / README.EN 对外口径统一
- [x] PTK7 确认为默认且长期支持的单文件格式
- [x] Session 写入路径性能收敛（`add_all()` / `flush()` / `bulk_insert()`）
- [x] 持久化语义文档化（`auto_flush`、`flush()`、`close()`）
- [x] 发布检查清单并入 `docs/guide/development.md` / `development.en.md`
- [x] 当前基线验证通过（`uv run pytest tests/ -v`、`uv build`、两个推荐示例）

## 近期

- [ ] 将 `pyproject.toml` 的 `project.license` 改为 SPDX 字符串，消除 `uv build` 的 setuptools deprecation warning
- [ ] 补充 benchmark 原始结果的归档约定（结果文件位置、命名方式、对外引用口径）
- [ ] 梳理 `examples/` 目录的运行基线，决定是否需要补充自动化示例验证

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
