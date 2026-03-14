# 引擎对比与特性

Pytuck 支持 6 种存储引擎，每种引擎有不同的特性、限制和适用场景。

## 引擎总览

| 特性 | Binary | JSON | CSV | SQLite | Excel | XML |
|------|--------|------|-----|--------|-------|-----|
| 文件扩展名 | `.db` | `.json` | `.zip` | `.sqlite` / `.db` | `.xlsx` | `.xml` |
| 外部依赖 | 无 | 无 | 无 | 无 | `openpyxl` | `lxml` |
| 懒加载 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 加密支持 | ✅ | ❌ | ✅（ZIP 密码） | ❌ | ❌ | ❌ |
| 原生 SQL | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 服务端分页 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 类型精确保留 | ✅ | ⚠️ 部分 | ⚠️ 有限 | ⚠️ 部分 | ⚠️ 部分 | ⚠️ 部分 |
| 人类可读 | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| 大文件性能 | ✅ 优秀 | ⚠️ 一般 | ⚠️ 一般 | ✅ 优秀 | ⚠️ 一般 | ⚠️ 一般 |

---

## Binary 引擎（默认）

Pytuck 自定义的二进制格式，性能最优。

### 特性
- **懒加载**：只加载 schema 和索引，按需读取数据记录
- **WAL（Write-Ahead Log）**：v4 格式支持追加写入，减少全量重写
- **加密**：支持三级加密（low / medium / high）
- **类型精确保留**：所有 Python 类型完整往返

### 配置

```python
from pytuck.common.options import BinaryBackendOptions

db = Storage(
    file_path='data.db',
    engine='binary',
    backend_options=BinaryBackendOptions(
        lazy_load=True,             # 启用懒加载
        encryption='medium',        # 加密等级
        password='my_password',     # 加密密码
    )
)
```

### 限制
- 文件格式不可人工阅读或编辑
- 加密启用后懒加载被禁用（数据区整体加密）

---

## JSON 引擎

标准 JSON 格式存储，可读性最好。

### 特性
- 人类可读，可手动编辑
- 支持多种 JSON 库加速（`orjson`、`ujson`）
- 无外部依赖

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

---

## CSV 引擎

CSV 文件打包为 ZIP 存储（每张表一个 `.csv` 文件 + 元数据 `_metadata.json`）。

### 特性
- 人类可读（解压后）
- 支持 ZIP 密码保护
- 兼容 Excel 打开（默认 `utf-8-sig` 编码带 BOM）

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

### 限制
- `bool` 类型存储为 `0` / `1`（SQLite 无原生布尔类型）
- `list` / `dict` 类型序列化为 JSON 字符串存储
- `datetime` / `date` / `timedelta` 序列化为文本存储

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

---

## 引擎选型建议

| 场景 | 推荐引擎 | 理由 |
|------|----------|------|
| 生产环境（通用） | Binary | 性能最优，支持懒加载和加密 |
| 需要 SQL 查询能力 | SQLite | 原生 SQL，大数据量友好 |
| 需要人类可读 | JSON | 直接查看和编辑 |
| 需要 Excel 打开 | Excel / CSV | 兼容办公软件 |
| 数据交换格式 | CSV / JSON | 通用数据交换 |
| 数据需要加密 | Binary | 三级加密支持 |
| 数据需要密码保护 | CSV | ZIP 密码保护 |
| 嵌入式场景（如 Ren'Py） | Binary | 无外部依赖，文件格式紧凑 |
| 开发调试 | JSON | 可直接查看数据 |
| 结构化数据交换 | XML | 标准 XML 格式 |
