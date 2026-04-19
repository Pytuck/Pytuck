from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING, Union

from ..common.crypto import ENCRYPTION_LEVELS
from ..common.exceptions import ConfigurationError
from ..common.options import BackendOptions, PytuckBackendOptions
from .base import StorageBackend
from .pytuck_store import PytuckStore, probe_pytuck

if TYPE_CHECKING:
    from ..core.storage import Table

class PytuckBackend(StorageBackend):
    ENGINE_NAME = 'pytuck'
    FORMAT_VERSION = 7

    def __init__(self, file_path: Union[str, Path], options: BackendOptions) -> None:
        super().__init__(file_path, options)
        assert isinstance(options, PytuckBackendOptions), 'options must be an instance of PytuckBackendOptions'
        self.options = options
        encryption = self.options.encryption
        if encryption is not None and encryption not in ENCRYPTION_LEVELS:
            raise ConfigurationError(f'无效的加密等级: {encryption}')
        if encryption is not None and not self.options.password:
            raise ConfigurationError('加密需要提供密码')
        self.store = PytuckStore(self.file_path, self.options)

    def load(self) -> dict[str, 'Table']:
        if not self.exists():
            raise FileNotFoundError(f'Pytuck file not found: {self.file_path}')
        return self.store.load_tables()

    def supports_lazy_loading(self) -> bool:
        """Pytuck 重新打开文件时默认按需 materialize 数据。"""
        return True

    def supports_server_side_pagination(self) -> bool:
        """Pytuck 在干净状态下支持通过后端路径执行分页查询。"""
        return True

    def populate_tables_with_data(self, tables: dict[str, 'Table']) -> None:
        """将已打开的 pytuck 表全部 materialize 到内存。"""
        for table in tables.values():
            table._ensure_all_loaded()

    def query_with_pagination(
        self,
        table_name: str,
        conditions: list[dict[str, Any]],
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> dict[str, Any]:
        """通过后端路径执行过滤、排序和分页。"""
        if not self.exists():
            return {'records': [], 'total_count': 0, 'has_more': False}

        from ..core.storage import Condition, Storage

        temp_db = Storage(
            file_path=str(self.file_path),
            engine='pytuck',
            backend_options=self.options,
        )
        try:
            condition_objs = [
                Condition(cond['field'], cond.get('operator', '='), cond['value'])
                for cond in conditions
            ]
            all_records = temp_db.query(
                table_name,
                condition_objs,
                order_by=order_by,
                order_desc=order_desc,
            )
            total_count = len(all_records)
            paged_records = all_records[offset:]
            if limit is not None:
                paged_records = paged_records[:limit]
            has_more = (offset + len(paged_records)) < total_count if limit is not None else False
            return {
                'records': paged_records,
                'total_count': total_count,
                'has_more': has_more,
            }
        finally:
            temp_db.close()

    def save(
        self,
        tables: dict[str, 'Table'],
        *,
        changed_tables: Optional[set[str]] = None,
    ) -> None:
        self.store.replace_tables(tables)
        self.store.flush(changed_tables=changed_tables)

    def exists(self) -> bool:
        return self.store.exists()

    def delete(self) -> None:
        self.store.delete()

    @classmethod
    def probe(cls, file_path: Union[str, Path]) -> tuple[bool, Optional[dict[str, Any]]]:
        return probe_pytuck(file_path)

__all__ = ['PytuckBackend']
