# Pytuck 项目上下文

Pytuck 面向无法可靠安装第三方包或原生扩展的 Python 环境，提供零依赖的关系型数据存储能力和 SQLAlchemy 风格的 Pythonic 操作体验。

## Language

**受限 Python 环境**：
无法可靠安装或使用第三方依赖、原生扩展或完整数据库服务的 Python 运行环境，例如 Ren'Py。
_Avoid_：阉割版 Python、异常环境

**零依赖核心**：
仅依赖 Python 自身即可使用的 Pytuck 基础安装与核心能力，是所有设计和优化必须保留的产品边界。
_Avoid_：最小安装、基础版

**扩展能力**：
通过可选依赖提供的额外引擎、加速或集成功能；未安装时不得影响零依赖核心的可用性。
_Avoid_：核心依赖、必选插件

**SQLAlchemy 风格 API**：
借鉴 SQLAlchemy 使用习惯的 Pythonic 数据操作接口，不表示 Pytuck 要成为完整 SQLAlchemy 或成熟数据库的替代品。
_Avoid_：SQLAlchemy 兼容层、SQLAlchemy 替代品
