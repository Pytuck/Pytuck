# 引擎对比与特性

Pytuck 支持 8 种存储引擎，每种引擎有不同的特性、限制和适用场景。

## 引擎总览

| 特性 | Pytuck | JSON | JSONL | CSV | SQLite | DuckDB | Excel | XML |
|------|--------|------|-------|-----|--------|--------|-------|-----|
| 文件扩展名 | `.pytuck` | `.json` | `.zip` | `.zip` | `.sqlite` / `.db` | `.duckdb` | `.xlsx` | `.xml` |
| 外部依赖 | 无 | 无 | 无 | 无 | 无 | `duckdb` | `openpyxl` | `lxml` |
| 按需读取 | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| 加密支持 | ✅（无加密 / `low` / `medium` / `high`） | ❌ | ✅（ZIP 密码） | ✅（ZIP 密码） | ❌ | ❌ | ❌ | ❌ |
| 原生 SQL | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| 服务端分页 | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| 类型精确保留 | ✅ | ⚠️ 部分 | ⚠️ 部分 | ⚠️ 有限 | ⚠️ 部分 | ⚠️ 部分 | ⚠️ 部分 | ⚠️ 部分 |
| 人类可读 | ❌ | ✅ | ✅（解压后） | ✅（解压后） | ❌ | ❌ | ✅ | ✅ |
| 大文件性能 | ✅ 优秀 | ⚠️ 一般 | ⚠️ 一般 | ⚠️ 一般 | ✅ 优秀 | ✅ 优秀 | ⚠️ 一般 | ⚠️ 一般 |
| 核心优势 | 默认单文件引擎、类型最完整、适合零依赖嵌入式场景 | 最易调试、可手改 | 逐行文本、多表归档 | 文件体积最小、便于交换 | 通用 SQL、事务稳定 | 分析查询、多 schema | 办公软件直开 | 标准化结构交换 |

---

## Pytuck 引擎（默认）

Pytuck 使用自定义的 `.pytuck` 单文件格式，适合零依赖、嵌入式和受限环境中的本地数据持久化。

> [!IMPORTANT]
> `PytuckBackendOptions` 当前只保留 `encryption` 与 `password` 两个字段；重新打开 `.pytuck` 文件时默认按需读取，无需额外开关。当前单文件新写入支持无加密与 `low` / `medium` / `high`。

### 特性
- **默认按需读取**：打开文件时优先恢复结构与索引目录，记录内容按需读取
- **单文件持久化**：使用单文件保存，写入采用重写 + 原子替换；多表数据库只修改部分表时，可直接复用未修改 lazy 表的 PTK7 编码块，避免完整解码进内存
- **加密支持**：当前新写入支持无加密与 `low` / `medium` / `high`；加密写入使用独立加密/认证子密钥和 HMAC-SHA256 标签检测文件篡改，旧版无认证标签的 PTK7 加密文件仍可读取
- **类型精确保留**：所有 Python 类型完整往返

> 说明：当前默认单文件主路径的重点是格式长期稳定、实现收敛，以及打开 / 重开 / 主键点查体验；不要把它理解成“在所有 benchmark 维度都全面领先”的通用最快实现。

### 配置

```python
from pytuck.common.options import PytuckBackendOptions

db = Storage(
    file_path='data.pytuck',
    engine='pytuck',
    backend_options=PytuckBackendOptions(
        encryption='low',
        password='my_password',
    )
)
```

### 当前行为

重新打开 `.pytuck` 文件时，Pytuck 会优先恢复 schema 与索引目录，记录内容按需读取；无需通过额外选项切换。

### 限制
- 文件格式不可人工阅读或编辑
- 当前单文件新写入支持无加密 / `low` / `medium` / `high`
- 第三方工具无法直接检查或修复内部数据，排障通常需要通过 Pytuck 自身 API 导出
- 如果更看重原生 SQL、服务端分页或超大数据集，优先考虑 SQLite / DuckDB

---

## JSON 引擎

标准 JSON 格式存储，可读性最好。

### 特性
- 人类可读，可手动编辑
- 支持 `orjson` 可选加速
- 无外部依赖

> 说明：`ujson` 已从当前文档与官方内置支持路径中移除；如需加速，优先使用 `orjson`，否则默认走标准库 `json`。
>
> 参考当前仓库内的专项 benchmark，在 `100000` 条记录口径下，`orjson` 相比标准库 `json` 在 JSON 引擎上的 `save` / `load` / `reopen` 大致有 `1.19x` 到 `1.32x` 的提升。详见 [`docs/guide/benchmark.md`](../guide/benchmark.md)。

### 配置

```python
from pytuck.common.options import JsonBackendOptions

db = Storage(
    file_path='data.json',
    engine='json',
    backend_options=JsonBackendOptions(
        indent=2,               # 缩进（None 为紧凑格式）
        ensure_ascii=False,     # 允许非 ASCII 字符
        impl='orjson',          # 指定 JSON 库（可选）
    )
)
```

### 限制
- 每次保存完整重写文件
- 大文件场景 I/O 开销较高
- `datetime`、`date`、`timedelta` 序列化为字符串，`bytes` 序列化为 Base64
- 虽然可手动编辑，但若直接修改 schema、类型名或编码后的值，重新加载时可能出现类型恢复失败

---

## JSONL 引擎

JSONL 文件打包为 ZIP 存储（每张表一个 `.jsonl` 文件 + 元数据 `_metadata.json`）。

### 特性
- 人类可读（解压后）
- 每行一条记录，便于逐行处理和外部工具消费
- 支持 `orjson` 可选加速
- 支持 ZIP 密码保护
- 无外部依赖

> 说明：`ujson` 已从当前文档与官方内置支持路径中移除；如需加速，优先使用 `orjson`，否则默认走标准库 `json`。
>
> 参考当前仓库内的专项 benchmark，在 `100000` 条记录口径下，`orjson` 相比标准库 `json` 在 JSONL 引擎上的 `save` / `load` / `reopen` 大致有 `1.38x` 到 `1.77x` 的提升。详见 [`docs/guide/benchmark.md`](../guide/benchmark.md)。

### 配置

```python
from pytuck.common.options import JsonlBackendOptions

db = Storage(
    file_path='data.zip',
    engine='jsonl',
    backend_options=JsonlBackendOptions(
        ensure_ascii=False,
        impl='orjson',
        password='my_password',  # 可选：ZIP 密码（仅 ASCII 字符）
    )
)
```

### 注意事项

- 外层文件是 ZIP 容器，不是单个裸 `.jsonl`
- 每张表对应一个 `.jsonl` 文件，schema 保存在 `_metadata.json`
- 设置 `JsonlBackendOptions(password='...')` 后会启用 ZIP 密码保护；重新打开同一归档时也需要提供相同密码
- `probe()` 和 `get_metadata()` 在未提供密码时仍能识别“这是加密的 JSONL ZIP”，但只能返回有限信息
- ZIP 密码仅允许 ASCII 可打印字符（不支持中文、日文、空格等）
- 当前保存策略为全量重写，适合交换、归档、调试，不适合超大文件高频更新
- `datetime`、`date`、`timedelta` 序列化为字符串，`bytes` 序列化为 Base64
- 解压后手工修改 `.jsonl` 或重新打包 ZIP 时，如果破坏 `_metadata.json` 与表数据的一致性，类型恢复可能失败

---

## CSV 引擎

CSV 文件打包为 ZIP 存储（每张表一个 `.csv` 文件 + 元数据 `_metadata.json`）。

### 特性
- 人类可读（解压后）
- 支持 ZIP 密码保护
- 兼容 Excel 打开（默认 `utf-8-sig` 编码带 BOM）
- 当前 benchmark 中磁盘占用最小，适合体积敏感的数据交换场景

### 配置

```python
from pytuck.common.options import CsvBackendOptions

db = Storage(
    file_path='data.zip',
    engine='csv',
    backend_options=CsvBackendOptions(
        encoding='utf-8-sig',       # 字符编码
        delimiter=',',              # 分隔符
        indent=2,                   # 元数据 JSON 缩进
        password='my_password',     # ZIP 密码（仅 ASCII 字符）
        field_size_limit=1048576,   # CSV 字段大小上限（bytes）
    )
)
```

### 注意事项

- **NULL vs 空字符串**：CSV 格式无法区分 `None` 和空字符串 `''`。从 CSV 加载后，原来的 `None` 值可能变为空字符串
- **类型信息**：类型信息保存在 `_metadata.json` 中，加载时根据元数据恢复类型。但直接编辑 CSV 可能导致类型不匹配
- **field_size_limit**：Python 的 `csv` 模块默认字段大小限制为 131072 bytes。如果数据中包含超大文本字段（如长文章、Base64 编码的二进制数据），需要设置更大的 `field_size_limit`
- **ZIP 密码**：仅允许 ASCII 可打印字符（`!` 到 `~`），不支持中文、日文、空格等

### 增量保存

CSV 引擎支持 Table 级别的增量保存优化。当使用 `Storage.flush()` 写入磁盘时，Pytuck 会自动跟踪哪些表的数据发生了变更：

- **未变更的表**：直接从旧 ZIP 文件复制（二进制拷贝，无需重新编码）
- **变更的表**：仅重写这些表的 CSV 数据和元数据

这对于包含多张表的大型数据库特别有效——只修改一张表时，其他表的 I/O 开销降为零。

> **注意**：启用 ZIP 密码保护时不使用增量策略（因为 Python `zipfile` 模块不支持读取加密 ZIP 条目的原始字节），此时仍为全量写入。

---

## SQLite 引擎

使用 SQLite 数据库作为后端。

### 特性
- **原生 SQL 模式**：直接执行 SQL 语句（默认开启），性能最优
- **服务端分页**：`query_table_data` 直接在数据库端分页，适合大数据量
- 无外部依赖（Python 内置 `sqlite3`）
- 数据文件可被其他 SQLite 工具读取

### 配置

```python
from pytuck.common.options import SqliteBackendOptions

db = Storage(
    file_path='data.sqlite',
    engine='sqlite',
    backend_options=SqliteBackendOptions(
        use_native_sql=True,        # 原生 SQL 模式（默认 True）
        check_same_thread=True,     # 检查同一线程
        timeout=5.0,                # 连接超时
    )
)
```

### 原生 SQL 模式说明

`use_native_sql=True`（默认）时：
- `SELECT` / `INSERT` / `UPDATE` / `DELETE` 直接编译为 SQL 执行
- 不加载全部数据到内存
- 适合大数据量场景

`use_native_sql=False` 时：
- 全量加载数据到内存
- 查询在内存中执行
- 行为与其他引擎一致
- 当 `Column.name` 使用中文或其他特殊标识符时，兼容模式更稳妥

### 限制
- `bool` 类型存储为 `0` / `1`（SQLite 无原生布尔类型）
- `list` / `dict` 类型序列化为 JSON 字符串存储
- `datetime` / `date` / `timedelta` 序列化为文本存储
- 直接使用外部 SQL 工具修改 schema 或表名后，若与 Pytuck 模型定义不一致，重开时可能出现映射偏差

---

## DuckDB 引擎

使用 DuckDB 数据库作为后端，适合分析型查询、已有 DuckDB 文件接入和多 schema 工作流。

### 特性
- **原生 SQL 模式**：默认开启，直接执行 SQL 语句
- **多 schema 支持**：可通过 `schema` 选项切换默认 schema
- **服务端分页**：`query_table_data` 可直接在数据库端分页
- **原生注释支持**：表备注与列备注直接写入 DuckDB catalog

### 配置

```python
from pytuck.common.options import DuckdbBackendOptions

db = Storage(
    file_path='data.duckdb',
    engine='duckdb',
    backend_options=DuckdbBackendOptions(
        use_native_sql=True,
        schema='main',
        read_only=False,
        threads=None,
    )
)
```

### 依赖
```bash
pip install duckdb
```

### 限制
- 需要安装 `duckdb`
- 当前 ORM / Session 的逐条写入路径不适合大批量写入 benchmark；DuckDB 更适合分析查询和原生 SQL 场景
- `list` / `dict` 类型以 JSON 形式存储
- 直接在外部工具中修改表结构、schema 或注释后，需要确保与 Pytuck 模型定义保持一致

---

## Excel 引擎

使用 `.xlsx` 格式存储。

### 特性
- 可直接用 Excel / WPS 打开查看
- 每张表对应一个工作表
- 元数据存储在隐藏的 `_pytuck_tables` 工作表中

### 配置

```python
from pytuck.common.options import ExcelBackendOptions

db = Storage(
    file_path='data.xlsx',
    engine='excel',
    backend_options=ExcelBackendOptions(
        read_only=False,                # 只读模式（提升读取性能）
        hide_metadata_sheets=True,      # 隐藏元数据工作表
    )
)
```

### 依赖
```bash
pip install openpyxl
```

### 限制
- 需要安装 `openpyxl`
- 每次保存完整重写文件
- 大文件写入较慢
- Excel 空单元格无法区分 `None`、空字符串 `''` 和空 bytes `b''`；重新加载时会按空单元格语义合并处理
- 直接在 Excel / WPS 中手工改表头、隐藏元数据工作表或单元格文本，可能破坏列类型恢复与表结构识别
- 行号映射功能（`row_number_mapping`）可追踪原始 Excel 行号

---

## XML 引擎

使用 XML 格式存储。

### 特性
- 人类可读的结构化格式
- 支持格式化输出

### 配置

```python
from pytuck.common.options import XmlBackendOptions

db = Storage(
    file_path='data.xml',
    engine='xml',
    backend_options=XmlBackendOptions(
        encoding='utf-8',          # 字符编码
        pretty_print=True,         # 格式化输出
    )
)
```

### 依赖
```bash
pip install lxml
```

### 限制
- 需要安装 `lxml`
- 每次保存完整重写文件
- XML 解析性能一般
- `bytes` 以 Base64 文本保存，`list` / `dict` 以 JSON 文本保存；手工编辑时需要保留对应编码语义
- 若手工修改 `null`、`encoding`、`type` 等属性，重新加载时可能出现类型恢复错误

---

## 引擎选型建议

| 场景 | 推荐引擎 | 理由 |
|------|----------|------|
| 生产环境（通用） | Pytuck | 默认单文件引擎，类型保留最完整，适合零依赖与受限环境 |
| 需要 SQL 查询能力 | SQLite / DuckDB | 都支持原生 SQL；SQLite 更偏通用事务写入，DuckDB 更偏分析查询 |
| 分析型查询 / 多 schema | DuckDB | 原生 DuckDB 后端，支持多 schema 与服务端分页 |
| 需要人类可读 | JSON / JSONL | JSON 适合单文件直读；JSONL 适合多表归档后解压查看 |
| 需要逐行文本交换 | JSONL | 每表一份 `.jsonl`，便于逐行处理 |
| 需要 Excel 打开 | Excel / CSV | 兼容办公软件 |
| 数据交换格式 | CSV / JSONL / JSON | 按体积、逐行文本、单文件可读性分别取舍 |
| 数据需要加密 | Pytuck | 当前单文件新写入支持无加密 / `low` / `medium` / `high` |
| 数据需要密码保护 | CSV / JSONL | 都支持 ZIP 密码保护；CSV 更偏体积优先，JSONL 更偏逐行文本交换 |
| 嵌入式场景（如 Ren'Py） | Pytuck | 无外部依赖，单文件使用简单 |
| 开发调试 | JSON | 直接查看和编辑最方便 |
| 结构化数据交换 | XML | 标准 XML 格式 |
