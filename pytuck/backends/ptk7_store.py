from __future__ import annotations

"""
PTK7 主存储路径实现。
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import struct
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..common.exceptions import MigrationError, RecordNotFoundError, SerializationError, TableNotFoundError
from ..common.options import BinaryBackendOptions
from ..core.orm import Column
from ..core.storage import Table
from ..core.types import TypeRegistry
from .legacy_ptk5 import probe_ptk5
from .ptk7_format import (
    FileHeaderV7,
    HEADER_STRUCT,
    MAGIC_V7,
    PK_DIR_INT_STRUCT,
    PkDirEntry,
    TABLE_REF_BODY_STRUCT,
    TABLE_REF_PREFIX_STRUCT,
    TableBlockRef,
    decode_row,
    encode_row,
)
from .ptk7_index import encode_sorted_pairs, decode_sorted_pairs
from ..core.index import BaseIndex, HashIndex, SortedIndex


class _LazySortedIndex(SortedIndex):
    """延迟解码的有序索引子类，保持 isinstance 为 SortedIndex。"""

    def __init__(self, column_name: str, blob: bytes, column: Column, table_ref: Table) -> None:
        SortedIndex.__init__(self, column_name)
        self._blob = blob
        self._column = column
        self._table = table_ref
        self._materialized = False

    def _materialize(self) -> None:
        if self._materialized:
            return
        pairs = decode_sorted_pairs(self._blob, self._column)
        for value, pk in pairs:
            SortedIndex.insert(self, value, pk)
        self._blob = b""
        self._materialized = True
        column_name = self._column.name
        if column_name is not None:
            self._table.indexes[column_name] = self

    def lookup(self, value: Any) -> Set[Any]:
        self._materialize()
        return SortedIndex.lookup(self, value)

    def range_query(
        self,
        min_val: Optional[Any] = None,
        max_val: Optional[Any] = None,
        include_min: bool = True,
        include_max: bool = True,
    ) -> Set[Any]:
        self._materialize()
        return SortedIndex.range_query(self, min_val, max_val, include_min, include_max)

    def get_sorted_pks(self, reverse: bool = False) -> List[Any]:
        self._materialize()
        return SortedIndex.get_sorted_pks(self, reverse)

    def insert(self, value: Any, pk: Any) -> None:
        self._materialize()
        SortedIndex.insert(self, value, pk)

    def remove(self, value: Any, pk: Any) -> None:
        self._materialize()
        SortedIndex.remove(self, value, pk)

    def clear(self) -> None:
        self._materialize()
        SortedIndex.clear(self)

    def __len__(self) -> int:
        self._materialize()
        return SortedIndex.__len__(self)


class _LazyHashIndex(HashIndex):
    """延迟解码的哈希索引子类，保持 isinstance 为 HashIndex。"""

    def __init__(self, column_name: str, blob: bytes, column: Column, table_ref: Table) -> None:
        HashIndex.__init__(self, column_name)
        self._blob = blob
        self._column = column
        self._table = table_ref
        self._materialized = False

    def _materialize(self) -> None:
        if self._materialized:
            return
        pairs = decode_sorted_pairs(self._blob, self._column)
        for value, pk in pairs:
            HashIndex.insert(self, value, pk)
        self._blob = b""
        self._materialized = True
        column_name = self._column.name
        if column_name is not None:
            self._table.indexes[column_name] = self

    def lookup(self, value: Any) -> Set[Any]:
        self._materialize()
        return HashIndex.lookup(self, value)

    def insert(self, value: Any, pk: Any) -> None:
        self._materialize()
        HashIndex.insert(self, value, pk)

    def remove(self, value: Any, pk: Any) -> None:
        self._materialize()
        HashIndex.remove(self, value, pk)

    def clear(self) -> None:
        self._materialize()
        HashIndex.clear(self)

    def __len__(self) -> int:
        self._materialize()
        return HashIndex.__len__(self)



RECORD_LENGTH_STRUCT = struct.Struct("<I")


@dataclass
class TableOverlay:
    inserted: Dict[Any, Dict[str, Any]] = field(default_factory=dict)
    updated: Dict[Any, Dict[str, Any]] = field(default_factory=dict)
    deleted: Set[Any] = field(default_factory=set)
    row_cache: Dict[Any, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TableState:
    table: Table
    pk_index: Dict[Any, Tuple[int, int]] = field(default_factory=dict)
    overlay: TableOverlay = field(default_factory=TableOverlay)


class StorePTK7:
    def __init__(
        self,
        file_path: Union[str, Path],
        options: Optional[BinaryBackendOptions] = None,
    ) -> None:
        self.file_path: Path = Path(file_path).expanduser()
        self.options: BinaryBackendOptions = options or BinaryBackendOptions()
        self._tables: Dict[str, TableState] = {}
        if self.file_path.exists():
            self.open()

    def exists(self) -> bool:
        return self.file_path.exists()

    def delete(self) -> None:
        try:
            self.file_path.unlink()
        except FileNotFoundError:
            pass
        self._tables = {}

    def create_table(
        self,
        table_name: str,
        columns: List[Column],
        primary_key: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> None:
        resolved_primary_key = primary_key or _find_primary_key(columns)
        table = Table(table_name, columns, primary_key=resolved_primary_key, comment=comment)
        self._tables[table_name] = TableState(table=table)

    def insert(self, table_name: str, record: Dict[str, Any]) -> Any:
        state = self.table_state(table_name)
        pk = state.table.insert(record.copy())
        state.overlay.inserted[pk] = state.table.data[pk].copy()
        state.overlay.deleted.discard(pk)
        state.overlay.updated.pop(pk, None)
        return pk

    def table_state(self, table_name: str) -> TableState:
        if table_name not in self._tables:
            raise TableNotFoundError(table_name)
        return self._tables[table_name]

    def replace_tables(self, tables: Dict[str, Table]) -> None:
        self._tables = {
            table_name: TableState(table=table)
            for table_name, table in tables.items()
        }

    def load_tables(self) -> Dict[str, Table]:
        if not self._tables and self.exists():
            self.open()
        return {
            table_name: state.table
            for table_name, state in self._tables.items()
        }

    def open(self) -> None:
        matched_ptk5, _ = probe_ptk5(self.file_path)
        if matched_ptk5:
            raise MigrationError(
                f"检测到不受支持的旧版 Pytuck 单文件格式：{self.file_path}。当前版本无法直接打开该文件。"
            )

        header = self._read_header()
        schema_blob = self._read_region(header.schema_offset, header.schema_size)
        schema_doc = _decode_schema_document(schema_blob)
        ref_blob = self._read_region(header.table_ref_offset, header.table_ref_size)
        table_refs = _decode_table_refs(ref_blob)

        tables: Dict[str, TableState] = {}
        for table_doc in schema_doc["tables"]:
            table_name = table_doc["name"]
            columns = [_column_from_schema(column_doc) for column_doc in table_doc["columns"]]
            table = Table(
                table_name,
                columns,
                primary_key=table_doc.get("primary_key"),
                comment=table_doc.get("comment"),
            )
            table.next_id = int(table_doc.get("next_id", 1))
            table.data = {}

            ref = table_refs[table_name]
            pk_index = self._read_pk_index(ref)

            table._lazy_loaded = True
            table._data_file = self.file_path
            table._backend = self
            table._pk_offsets = {pk: offset for pk, (offset, _length) in pk_index.items()}

            # restore indexes if present
            if ref.index_meta_size and ref.index_data_size:
                meta_blob = self._read_region(ref.index_meta_offset, ref.index_meta_size)
                data_blob = self._read_region(ref.index_data_offset, ref.index_data_size)
                try:
                    meta = json.loads(meta_blob.decode('utf-8'))
                except Exception:
                    raise SerializationError('Invalid PTK7 index meta')
                for entry in meta:
                    col = entry.get('column')
                    itype = entry.get('type')
                    off = int(entry.get('offset', 0))
                    size = int(entry.get('size', 0))
                    if size == 0:
                        continue
                    blob = data_blob[off: off + size]
                    # decode pairs
                    column = table.columns.get(col)
                    if column is None:
                        continue
                    # 延迟解码：创建 LazyIndex 占位符，实际解码在首次访问时进行
                    # blob 已经截取为对应索引的数据段
                    # instantiate lazy placeholder of correct subclass so isinstance checks work
                    lazy: BaseIndex
                    if itype == 'sorted':
                        lazy = _LazySortedIndex(col, blob, column, table)
                    else:
                        lazy = _LazyHashIndex(col, blob, column, table)
                    table.indexes[col] = lazy

            tables[table_name] = TableState(table=table, pk_index=pk_index)

        self._tables = tables

    def select(self, table_name: str, pk: Any) -> Dict[str, Any]:
        state = self.table_state(table_name)
        normalized_pk = state.table._normalize_pk(pk)
        if normalized_pk in state.overlay.deleted:
            raise RecordNotFoundError(table_name, normalized_pk)
        if normalized_pk in state.overlay.updated:
            return state.overlay.updated[normalized_pk].copy()
        if normalized_pk in state.overlay.inserted:
            return state.overlay.inserted[normalized_pk].copy()
        if normalized_pk in state.overlay.row_cache:
            return state.overlay.row_cache[normalized_pk].copy()
        if normalized_pk not in state.pk_index:
            raise RecordNotFoundError(table_name, normalized_pk)

        offset, length = state.pk_index[normalized_pk]
        record = self._read_row_at(state, offset, length, normalized_pk)
        state.overlay.row_cache[normalized_pk] = record
        return record.copy()

    def read_lazy_record(
        self,
        file_path: Path,
        offset: int,
        columns: Dict[str, Column],
        pk: Any = None,
    ) -> Dict[str, Any]:
        with open(file_path, "rb") as handle:
            handle.seek(offset)
            length_data = handle.read(RECORD_LENGTH_STRUCT.size)
            if len(length_data) < RECORD_LENGTH_STRUCT.size:
                raise SerializationError("PTK7 record length prefix is incomplete")
            payload_length = RECORD_LENGTH_STRUCT.unpack(length_data)[0]
            payload = handle.read(payload_length)
            if len(payload) < payload_length:
                raise SerializationError("PTK7 record payload is incomplete")

        ordered_columns = list(columns.values())
        pk_name = _find_primary_key(ordered_columns)
        record = decode_row(ordered_columns, payload, pk_name=pk_name)
        if pk_name is not None and pk is not None:
            record[pk_name] = pk
        return record

    def flush(self, *, changed_tables: Optional[Set[str]] = None) -> None:
        del changed_tables

        schema_bytes = _encode_schema_document(list(self._tables.values()))
        table_layouts = [_build_table_layout(state) for state in self._tables.values()]

        table_ref_offset = HEADER_STRUCT.size + len(schema_bytes)
        table_ref_size = sum(layout.ref_size for layout in table_layouts)

        # Precompute index meta/data blobs per table (depends only on table.indexes and columns)
        index_meta_blobs: List[bytes] = []
        index_data_blobs: List[bytes] = []
        for state in self._tables.values():
            table = state.table
            meta_entries = []
            data_buf = bytearray()
            for col_name, index in table.indexes.items():
                pairs = []
                if isinstance(index, (_LazyHashIndex, _LazySortedIndex)):
                    index._materialize()
                # 使用 isinstance 判断索引类型以获得更稳健的类型信息
                if isinstance(index, HashIndex):
                    # HashIndex: map -> value -> set(pk)
                    map_obj = getattr(index, 'map', {})
                    for value, pk_set in map_obj.items():
                        for pk in pk_set:
                            pairs.append((value, pk))
                    index_type = 'hash'
                elif isinstance(index, SortedIndex):
                    # SortedIndex: sorted_values and value_to_pks
                    for value in getattr(index, 'sorted_values', []):
                        pks = getattr(index, 'value_to_pks', {}).get(value, set())
                        for pk in pks:
                            pairs.append((value, pk))
                    index_type = 'sorted'
                else:
                    # 未知类型：尝试按通用结构读取
                    for value, pk_set in getattr(index, 'map', {}).items():
                        for pk in pk_set:
                            pairs.append((value, pk))
                    index_type = 'hash'

                if not pairs:
                    continue
                column = table.columns.get(col_name)
                if column is None:
                    continue
                encoded = encode_sorted_pairs(pairs, column)
                offset = len(data_buf)
                data_buf.extend(encoded)
                size = len(encoded)
                meta_entries.append({
                    'column': col_name,
                    'type': index_type,
                    'offset': offset,
                    'size': size,
                })
            meta_bytes = json.dumps(meta_entries, ensure_ascii=False).encode('utf-8')
            index_meta_blobs.append(meta_bytes)
            index_data_blobs.append(bytes(data_buf))

        # Now compute offsets and build TableBlockRef entries
        cursor = table_ref_offset + table_ref_size
        resolved_refs: List[TableBlockRef] = []
        resolved_pk_dirs: List[bytes] = []
        for layout, meta_blob, data_blob in zip(table_layouts, index_meta_blobs, index_data_blobs):
            data_offset = cursor
            cursor += len(layout.data_bytes)

            pk_dir_offset = cursor
            pk_dir_bytes = _encode_pk_dir(layout.records, data_offset)
            cursor += len(pk_dir_bytes)

            index_meta_offset = cursor
            index_meta_size = len(meta_blob)
            cursor += index_meta_size

            index_data_offset = cursor
            index_data_size = len(data_blob)
            cursor += index_data_size

            ref = TableBlockRef(
                name=layout.table_name,
                record_count=len(layout.records),
                next_id=layout.next_id,
                data_offset=data_offset,
                data_size=len(layout.data_bytes),
                pk_dir_offset=pk_dir_offset,
                pk_dir_size=len(pk_dir_bytes),
                index_meta_offset=index_meta_offset,
                index_meta_size=index_meta_size,
                index_data_offset=index_data_offset,
                index_data_size=index_data_size,
            )
            resolved_refs.append(ref)
            resolved_pk_dirs.append(pk_dir_bytes)

        table_ref_bytes = b"".join(ref.pack() for ref in resolved_refs)
        header = FileHeaderV7(
            table_count=len(resolved_refs),
            schema_offset=HEADER_STRUCT.size,
            schema_size=len(schema_bytes),
            table_ref_offset=table_ref_offset,
            table_ref_size=len(table_ref_bytes),
            file_size=cursor,
        )

        fd, temp_path_str = tempfile.mkstemp(
            dir=str(self.file_path.parent),
            prefix=f".{self.file_path.stem}.",
            suffix=".tmp",
        )
        temp_path = Path(temp_path_str)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(header.pack())
                handle.write(schema_bytes)
                handle.write(table_ref_bytes)
                for layout, pk_dir_bytes, meta_blob, data_blob in zip(table_layouts, resolved_pk_dirs, index_meta_blobs, index_data_blobs):
                    handle.write(layout.data_bytes)
                    handle.write(pk_dir_bytes)
                    handle.write(meta_blob)
                    handle.write(data_blob)
            temp_path.replace(self.file_path)
            # Do not call self.open() here — opening the file (and decoding indexes) should be
            # deferred until the Storage/consumer requests it. Re-opening here doubles reopen cost.
            # The backend file has been atomically replaced; leave in-memory structures as-is.
        except Exception:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            raise

    def _read_header(self) -> FileHeaderV7:
        with open(self.file_path, "rb") as handle:
            header_data = handle.read(HEADER_STRUCT.size)
        return FileHeaderV7.unpack(header_data)

    def _read_region(self, offset: int, size: int) -> bytes:
        with open(self.file_path, "rb") as handle:
            handle.seek(offset)
            data = handle.read(size)
        if len(data) < size:
            raise SerializationError(
                f"PTK7 region is incomplete at offset {offset} (need {size}, got {len(data)})"
            )
        return data

    def _read_pk_index(self, ref: TableBlockRef) -> Dict[Any, Tuple[int, int]]:
        if ref.pk_dir_size == 0:
            return {}
        blob = self._read_region(ref.pk_dir_offset, ref.pk_dir_size)
        if len(blob) % PK_DIR_INT_STRUCT.size != 0:
            raise SerializationError("PTK7 pk directory size is invalid")

        pk_index: Dict[Any, Tuple[int, int]] = {}
        offset = 0
        while offset < len(blob):
            entry = PkDirEntry.unpack_int(blob[offset: offset + PK_DIR_INT_STRUCT.size])
            pk_index[entry.pk] = (entry.offset, entry.length)
            offset += PK_DIR_INT_STRUCT.size
        return pk_index

    def _read_row_at(self, state: TableState, offset: int, length: int, pk: Any) -> Dict[str, Any]:
        payload_length = length - RECORD_LENGTH_STRUCT.size
        if payload_length < 0:
            raise SerializationError("PTK7 record length is invalid")

        with open(self.file_path, "rb") as handle:
            handle.seek(offset)
            raw = handle.read(length)
        if len(raw) < length:
            raise SerializationError("PTK7 record entry is incomplete")

        stored_payload_length = RECORD_LENGTH_STRUCT.unpack(raw[: RECORD_LENGTH_STRUCT.size])[0]
        if stored_payload_length != payload_length:
            raise SerializationError("PTK7 record length prefix mismatch")

        payload = raw[RECORD_LENGTH_STRUCT.size:]
        columns = list(state.table.columns.values())
        record = decode_row(columns, payload, pk_name=state.table.primary_key)
        if state.table.primary_key is not None:
            record[state.table.primary_key] = pk
        return record


@dataclass
class _RecordLayout:
    pk: Any
    entry_bytes: bytes


@dataclass
class _TableLayout:
    table_name: str
    next_id: int
    records: List[_RecordLayout]
    data_bytes: bytes
    ref_size: int


def _build_table_layout(state: TableState) -> _TableLayout:
    columns = list(state.table.columns.values())
    records: List[_RecordLayout] = []
    data_bytes = bytearray()
    for pk, record in sorted(state.table.data.items(), key=lambda item: item[0]):
        payload = encode_row(columns, record, pk_name=state.table.primary_key)
        entry_bytes = RECORD_LENGTH_STRUCT.pack(len(payload)) + payload
        data_bytes.extend(entry_bytes)
        records.append(_RecordLayout(pk=pk, entry_bytes=entry_bytes))

    ref_size = TABLE_REF_PREFIX_STRUCT.size + len(state.table.name.encode("utf-8")) + TABLE_REF_BODY_STRUCT.size
    return _TableLayout(
        table_name=state.table.name,
        next_id=state.table.next_id,
        records=records,
        data_bytes=bytes(data_bytes),
        ref_size=ref_size,
    )


def _encode_pk_dir(records: List[_RecordLayout], data_offset: int) -> bytes:
    pk_dir = bytearray()
    cursor = data_offset
    for record in records:
        entry = PkDirEntry(pk=record.pk, offset=cursor, length=len(record.entry_bytes))
        pk_dir.extend(entry.pack_int())
        cursor += len(record.entry_bytes)
    return bytes(pk_dir)


def _find_primary_key(columns: List[Column]) -> Optional[str]:
    for column in columns:
        if column.primary_key:
            return column.name
    return None


def _encode_schema_document(states: List[TableState]) -> bytes:
    document = {
        "tables": [
            {
                "name": state.table.name,
                "primary_key": state.table.primary_key,
                "next_id": state.table.next_id,
                "comment": state.table.comment,
                "columns": [_column_to_schema(column) for column in state.table.columns.values()],
            }
            for state in states
        ]
    }
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def _decode_schema_document(blob: bytes) -> Dict[str, Any]:
    try:
        document = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SerializationError("Failed to decode PTK7 schema document") from exc
    if not isinstance(document, dict) or "tables" not in document:
        raise SerializationError("Invalid PTK7 schema document")
    return document


def _column_to_schema(column: Column) -> Dict[str, Any]:
    return {
        "name": column.name,
        "type_name": TypeRegistry.get_type_name(column.col_type),
        "nullable": column.nullable,
        "primary_key": column.primary_key,
        "index": column.index,
        "comment": column.comment,
    }


def _column_from_schema(document: Dict[str, Any]) -> Column:
    return Column(
        TypeRegistry.get_type_by_name(document["type_name"]),
        name=document["name"],
        nullable=bool(document.get("nullable", True)),
        primary_key=bool(document.get("primary_key", False)),
        index=document.get("index", False),
        comment=document.get("comment"),
    )


def _decode_table_refs(blob: bytes) -> Dict[str, TableBlockRef]:
    refs: Dict[str, TableBlockRef] = {}
    offset = 0
    while offset < len(blob):
        if offset + TABLE_REF_PREFIX_STRUCT.size > len(blob):
            raise SerializationError("PTK7 table ref region is incomplete")
        name_length = TABLE_REF_PREFIX_STRUCT.unpack(blob[offset: offset + TABLE_REF_PREFIX_STRUCT.size])[0]
        consumed = TABLE_REF_PREFIX_STRUCT.size + name_length + TABLE_REF_BODY_STRUCT.size
        ref = TableBlockRef.unpack(blob[offset: offset + consumed])
        refs[ref.name] = ref
        offset += consumed
    return refs


def probe_ptk7(file_path: Union[str, Path]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    path = Path(file_path).expanduser()
    if not path.exists():
        return False, {"error": "file_not_found"}

    file_stat = path.stat()
    if file_stat.st_size < HEADER_STRUCT.size:
        return False, {"error": "file_too_small"}

    with open(path, "rb") as handle:
        header_data = handle.read(HEADER_STRUCT.size)

    try:
        header = FileHeaderV7.unpack(header_data)
    except SerializationError:
        return False, None

    if header.magic != MAGIC_V7:
        return False, None

    return True, {
        "engine": "pytuck",
        "format_version": "PTK7",
        "file_size": file_stat.st_size,
        "modified": file_stat.st_mtime,
        "confidence": "high",
        "table_count": header.table_count,
    }


__all__ = [
    "TableOverlay",
    "TableState",
    "StorePTK7",
    "probe_ptk7",
]
