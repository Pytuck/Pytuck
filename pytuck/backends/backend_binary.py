"""
Pytuck 二进制存储引擎 façade。

当前单文件后端默认使用 Pytuck 主格式运行。
"""

from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, TYPE_CHECKING, Union, cast

from ..common.crypto import ENCRYPTION_LEVELS
from ..common.exceptions import ConfigurationError, MigrationError
from ..common.options import BackendOptions, BinaryBackendOptions
from .legacy_ptk5 import (
    BinaryBackend,
    HeaderV5,
    WALEntry,
    WALOpType,
    load_ptk5_tables,
    probe_ptk5,
)
from .ptk7_store import StorePTK7, probe_ptk7

if TYPE_CHECKING:
    from ..core.storage import Table


_legacy_binary_backend_init = BinaryBackend.__init__


def _binary_backend_init(
    self: Any,
    file_path: Union[str, Path],
    options: BackendOptions,
) -> None:
    assert isinstance(options, BinaryBackendOptions), "options must be an instance of BinaryBackendOptions"
    _legacy_binary_backend_init(self, file_path, options)
    self.options = cast(BinaryBackendOptions, options)
    encryption = getattr(self.options, 'encryption', None)
    if encryption is not None:
        if encryption not in ENCRYPTION_LEVELS:
            raise ConfigurationError(f"无效的加密等级: {encryption}")
        if not getattr(self.options, 'password', None):
            raise ConfigurationError("加密需要提供密码")
    self.store = StorePTK7(self.file_path, self.options)

    # PTK7 主路径不启用 WAL；保留这些属性仅用于兼容 Storage 的旧检查逻辑。
    self._active_header = None
    self._active_slot = 0
    self._current_lsn = 0
    self._file_handle = None
    self._wal_buffer = []
    self._wal_buffer_size = 0
    self._wal_flush_threshold = 32 * 1024
    self._lazy_cipher = None
    self._lazy_data_offset = 0


def _binary_backend_load(self: Any) -> Dict[str, "Table"]:
    if not self.exists():
        raise FileNotFoundError(f"Pytuck file not found: {self.file_path}")

    matched, _ = probe_ptk5(self.file_path)
    if matched:
        raise MigrationError(
            f"检测到不受支持的旧版 Pytuck 单文件格式：{self.file_path}。当前版本无法直接打开该文件。"
        )
    return self.store.load_tables()


def _binary_backend_save(
    self: Any,
    tables: Dict[str, "Table"],
    *,
    changed_tables: Optional[Set[str]] = None,
) -> None:
    self.store.replace_tables(tables)
    self.store.flush(changed_tables=changed_tables)


def _binary_backend_probe(
    cls: type,
    file_path: Union[str, Path],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    matched, info = probe_ptk7(file_path)
    if matched:
        return matched, info
    return probe_ptk5(file_path)


from typing import Any, cast

# 使用 cast(Any, ...) 以消除 mypy 对方法赋值的警告
cast(Any, BinaryBackend).__init__ = _binary_backend_init
cast(Any, BinaryBackend).load = _binary_backend_load
cast(Any, BinaryBackend).save = _binary_backend_save
cast(Any, BinaryBackend).probe = classmethod(_binary_backend_probe)
BinaryBackend.FORMAT_VERSION = 7

__all__ = [
    "BinaryBackend",
    "HeaderV5",
    "WALEntry",
    "WALOpType",
    "probe_ptk5",
    "load_ptk5_tables",
]
