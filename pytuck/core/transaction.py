"""Storage 事务快照与回滚状态。"""

import copy
from typing import Any, TYPE_CHECKING


if TYPE_CHECKING:
    from .storage import Table


class TransactionSnapshot:
    """保存事务开始时的完整表状态，以便异常时原地恢复。"""

    def __init__(self, tables: dict[str, "Table"]) -> None:
        self.table_snapshots: dict[str, dict[str, Any]] = {}
        self.table_refs = dict(tables)

        for table_name, table in tables.items():
            self.table_snapshots[table_name] = {
                "name": table.name,
                "columns": copy.deepcopy(table.columns),
                "primary_key": table.primary_key,
                "comment": table.comment,
                "data": copy.deepcopy(table.data),
                "indexes": copy.deepcopy(table.indexes),
                "next_id": table.next_id,
                "pk_offsets": copy.deepcopy(table._pk_offsets),
                "_lazy_loaded": table._lazy_loaded,
                "_data_file": copy.deepcopy(table._data_file),
                "_backend": table._backend,
                "_data_dirty": table._data_dirty,
                "_schema_dirty": table._schema_dirty,
            }

    def restore(self, tables: dict[str, "Table"]) -> None:
        """恢复表映射、schema、数据、索引和按需加载状态。"""
        tables.clear()
        tables.update(self.table_refs)

        for table_name, snapshot in self.table_snapshots.items():
            table = self.table_refs[table_name]
            table.name = snapshot["name"]
            table.columns = snapshot["columns"]
            table.primary_key = snapshot["primary_key"]
            table.comment = snapshot["comment"]
            table.data = snapshot["data"]
            table.indexes = snapshot["indexes"]
            table.next_id = snapshot["next_id"]
            table._pk_offsets = copy.deepcopy(snapshot.get("pk_offsets"))
            table._lazy_loaded = bool(snapshot.get("_lazy_loaded", False))
            table._data_file = copy.deepcopy(snapshot.get("_data_file"))
            table._backend = snapshot.get("_backend")
            table._data_dirty = bool(snapshot.get("_data_dirty", False))
            table._schema_dirty = bool(snapshot.get("_schema_dirty", False))
