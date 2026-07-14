from __future__ import annotations

"""
PTK7 主存储路径实现。
"""

from dataclasses import dataclass, field
import hmac
import json
import os
from pathlib import Path
import struct
import tempfile
from typing import Any, Literal, cast

from ..common.crypto import CryptoProvider, ENCRYPTION_LEVELS, CipherType, get_cipher
from ..common.exceptions import (
    ConfigurationError,
    EncryptionError,
    MigrationError,
    RecordNotFoundError,
    SerializationError,
    TableNotFoundError,
)
from ..common.options import PytuckBackendOptions
from ..core.orm import Column
from ..core.storage import Table
from ..core.types import TypeRegistry
from .pytuck_format import (
    AUTH_TAG_SIZE,
    CRYPTO_META_STRUCT,
    CryptoMetadataV7,
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
from .pytuck_index import decode_sorted_pairs, encode_sorted_pairs
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

    def lookup(self, value: Any) -> set[Any]:
        self._materialize()
        return SortedIndex.lookup(self, value)

    def range_query(
        self,
        min_val: Any | None = None,
        max_val: Any | None = None,
        include_min: bool = True,
        include_max: bool = True,
    ) -> set[Any]:
        self._materialize()
        return SortedIndex.range_query(self, min_val, max_val, include_min, include_max)

    def get_sorted_pks(self, reverse: bool = False) -> list[Any]:
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

    def lookup(self, value: Any) -> set[Any]:
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
    inserted: dict[Any, dict[str, Any]] = field(default_factory=dict)
    updated: dict[Any, dict[str, Any]] = field(default_factory=dict)
    deleted: set[Any] = field(default_factory=set)
    row_cache: dict[Any, dict[str, Any]] = field(default_factory=dict)

@dataclass
class TableState:
    table: Table
    pk_index: dict[Any, tuple[int, int]] = field(default_factory=dict)
    overlay: TableOverlay = field(default_factory=TableOverlay)
    source_ref: TableBlockRef | None = None

class StorePTK7:
    def __init__(
        self,
        file_path: str | Path,
        options: PytuckBackendOptions | None = None,
    ) -> None:
        self.file_path: Path = Path(file_path).expanduser()
        self.options: PytuckBackendOptions = options or PytuckBackendOptions()
        self._tables: dict[str, TableState] = {}
        self._cipher: CipherType | None = None
        self._payload_offset: int = 0
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
        self._cipher = None
        self._payload_offset = 0

    def create_table(
        self,
        table_name: str,
        columns: list[Column],
        primary_key: str | None = None,
        comment: str | None = None,
    ) -> None:
        resolved_primary_key = primary_key or _find_primary_key(columns)
        table = Table(table_name, columns, primary_key=resolved_primary_key, comment=comment)
        self._tables[table_name] = TableState(table=table)

    def insert(self, table_name: str, record: dict[str, Any]) -> Any:
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

    def replace_tables(self, tables: dict[str, Table]) -> None:
        existing_by_identity = {
            id(state.table): state
            for state in self._tables.values()
        }
        replaced: dict[str, TableState] = {}
        for table_name, table in tables.items():
            state = existing_by_identity.get(id(table))
            if state is None:
                state = TableState(table=table)
            else:
                state.table = table
            replaced[table_name] = state
        self._tables = replaced

    def load_tables(self) -> dict[str, Table]:
        if not self._tables and self.exists():
            self.open()
        return {
            table_name: state.table
            for table_name, state in self._tables.items()
        }

    def open(self) -> None:
        header = self._read_header()
        header.validate_layout(self.file_path.stat().st_size)
        self._cipher = None
        self._payload_offset = 0

        if header.is_encrypted():
            if not self.options.password:
                raise EncryptionError("文件已加密，需要提供密码")
            if header.schema_offset < HEADER_STRUCT.size + CRYPTO_META_STRUCT.size:
                raise SerializationError("PTK7 encrypted metadata is incomplete")

            encryption_level = header.get_encryption_level()
            if not encryption_level:
                raise EncryptionError("无法识别加密等级")
            self.options.encryption = cast(
                Literal['low', 'medium', 'high'],
                encryption_level,
            )

            metadata_blob = self._read_region(HEADER_STRUCT.size, CRYPTO_META_STRUCT.size)
            metadata = CryptoMetadataV7.unpack(metadata_blob)
            key = CryptoProvider.derive_key(self.options.password, metadata.salt, encryption_level)
            if not CryptoProvider.verify_key(key, metadata.key_check):
                raise EncryptionError("密码错误")
            if header.is_authenticated():
                self._verify_file_authentication(header, key)
                cipher_key = CryptoProvider.derive_encryption_key(key)
            else:
                # 兼容读取认证标签引入前写出的 PTK7 加密文件。
                cipher_key = key
            self._cipher = get_cipher(encryption_level, cipher_key)
            self._payload_offset = header.table_ref_offset + header.table_ref_size

        schema_blob = self._read_region(header.schema_offset, header.schema_size)
        schema_doc = _decode_schema_document(schema_blob)
        ref_blob = self._read_region(header.table_ref_offset, header.table_ref_size)
        table_refs = _decode_table_refs(ref_blob)
        self._validate_table_refs(header, schema_doc, table_refs)

        tables: dict[str, TableState] = {}
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

            if ref.index_meta_size and ref.index_data_size:
                meta_blob = self._read_payload_region(ref.index_meta_offset, ref.index_meta_size)
                data_blob = self._read_payload_region(ref.index_data_offset, ref.index_data_size)
                try:
                    meta = json.loads(meta_blob.decode("utf-8"))
                except Exception as exc:
                    raise SerializationError("Invalid PTK7 index meta") from exc
                for entry in meta:
                    col = entry.get("column")
                    itype = entry.get("type")
                    off = int(entry.get("offset", 0))
                    size = int(entry.get("size", 0))
                    if size == 0:
                        continue
                    blob = data_blob[off: off + size]
                    column = table.columns.get(col)
                    if column is None:
                        continue
                    lazy: BaseIndex
                    if itype == "sorted":
                        lazy = _LazySortedIndex(col, blob, column, table)
                    else:
                        lazy = _LazyHashIndex(col, blob, column, table)
                    table.indexes[col] = lazy

            tables[table_name] = TableState(
                table=table,
                pk_index=pk_index,
                source_ref=ref,
            )

        self._tables = tables

    def select(self, table_name: str, pk: Any) -> dict[str, Any]:
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
        self._validate_record_location(state, offset, length)
        record = self._read_row_at(state, offset, length, normalized_pk)
        state.overlay.row_cache[normalized_pk] = record
        return record.copy()

    def read_lazy_record(
        self,
        file_path: Path,
        offset: int,
        columns: dict[str, Column],
        pk: Any = None,
    ) -> dict[str, Any]:
        del file_path
        state = next(
            (
                candidate
                for candidate in self._tables.values()
                if candidate.table.columns is columns
            ),
            None,
        )
        ref = state.source_ref if state is not None else None
        if ref is not None and not (
            ref.data_offset <= offset < ref.data_offset + ref.data_size
        ):
            raise SerializationError("PTK7 record offset is outside table data")

        length_data = self._read_payload_region(offset, RECORD_LENGTH_STRUCT.size)
        if len(length_data) < RECORD_LENGTH_STRUCT.size:
            raise SerializationError("PTK7 record length prefix is incomplete")
        payload_length = RECORD_LENGTH_STRUCT.unpack(length_data)[0]
        if ref is not None and (
            offset + RECORD_LENGTH_STRUCT.size + payload_length
            > ref.data_offset + ref.data_size
        ):
            raise SerializationError("PTK7 record payload is outside table data")
        payload = self._read_payload_region(offset + RECORD_LENGTH_STRUCT.size, payload_length)
        if len(payload) < payload_length:
            raise SerializationError("PTK7 record payload is incomplete")

        ordered_columns = list(columns.values())
        pk_name = _find_primary_key(ordered_columns)
        record = decode_row(ordered_columns, payload, pk_name=pk_name)
        if pk_name is not None and pk is not None:
            record[pk_name] = pk
        return record

    def _can_reuse_persisted_table(
        self,
        table_name: str,
        state: TableState,
        changed_tables: set[str] | None,
    ) -> bool:
        """判断未修改的延迟加载表能否直接复用原 PTK7 数据块。"""
        return bool(
            changed_tables is not None
            and table_name not in changed_tables
            and not state.table.is_dirty
            and state.table._lazy_loaded
            and state.source_ref is not None
        )

    def _reuse_table_layout(
        self,
        state: TableState,
    ) -> tuple['_TableLayout', bytes, bytes]:
        """读取未修改表的编码块，不解码记录或索引。"""
        ref = state.source_ref
        if ref is None:
            raise SerializationError("PTK7 source table reference is missing")
        data_bytes = self._read_payload_region(ref.data_offset, ref.data_size)
        records: list[_RecordLayout] = []
        # pk_index 保留磁盘目录顺序；复用 data_bytes 时同时验证记录连续性，
        # 避免重新排序和逐记录函数调用给受限环境增加额外开销。
        cursor = ref.data_offset
        for pk, (offset, length) in state.pk_index.items():
            if offset != cursor or length < RECORD_LENGTH_STRUCT.size:
                raise SerializationError(
                    f"PTK7 primary-key directory is not contiguous for {ref.name!r}"
                )
            records.append(_RecordLayout(pk=pk, length=length))
            cursor += length
        if cursor != ref.data_offset + ref.data_size:
            raise SerializationError(
                f"PTK7 primary-key directory does not cover table {ref.name!r}"
            )
        layout = _TableLayout(
            table_name=state.table.name,
            next_id=state.table.next_id,
            records=records,
            data_bytes=data_bytes,
            ref_size=_table_ref_size(state.table.name),
        )
        index_meta = self._read_payload_region(
            ref.index_meta_offset,
            ref.index_meta_size,
        )
        index_data = self._read_payload_region(
            ref.index_data_offset,
            ref.index_data_size,
        )
        return layout, index_meta, index_data

    @staticmethod
    def _encode_table_indexes(state: TableState) -> tuple[bytes, bytes]:
        """编码已修改表的索引元数据和数据。"""
        table = state.table
        meta_entries: list[dict[str, Any]] = []
        data_buf = bytearray()
        for col_name, index in table.indexes.items():
            pairs: list[tuple[Any, Any]] = []
            if isinstance(index, (_LazyHashIndex, _LazySortedIndex)):
                index._materialize()
            if isinstance(index, HashIndex):
                map_obj = getattr(index, "map", {})
                for value, pk_set in map_obj.items():
                    for pk in pk_set:
                        pairs.append((value, pk))
                index_type = "hash"
            elif isinstance(index, SortedIndex):
                for value in getattr(index, "sorted_values", []):
                    pks = getattr(index, "value_to_pks", {}).get(value, set())
                    for pk in pks:
                        pairs.append((value, pk))
                index_type = "sorted"
            else:
                for value, pk_set in getattr(index, "map", {}).items():
                    for pk in pk_set:
                        pairs.append((value, pk))
                index_type = "hash"

            if not pairs:
                continue
            column = table.columns.get(col_name)
            if column is None:
                continue
            encoded = encode_sorted_pairs(pairs, column)
            offset = len(data_buf)
            data_buf.extend(encoded)
            meta_entries.append(
                {
                    "column": col_name,
                    "type": index_type,
                    "offset": offset,
                    "size": len(encoded),
                }
            )
        meta_bytes = json.dumps(meta_entries, ensure_ascii=False).encode("utf-8")
        return meta_bytes, bytes(data_buf)

    def flush(self, *, changed_tables: set[str] | None = None) -> None:
        encryption_level = getattr(self.options, 'encryption', None)
        cipher: CipherType | None = None
        master_key: bytes | None = None
        crypto_metadata: CryptoMetadataV7 | None = None
        metadata_size = 0
        if encryption_level is not None:
            if encryption_level not in ENCRYPTION_LEVELS:
                raise ConfigurationError(f"无效的加密等级: {encryption_level}")
            if not self.options.password:
                raise ConfigurationError("加密需要提供密码")
            salt = os.urandom(16)
            master_key = CryptoProvider.derive_key(
                self.options.password,
                salt,
                encryption_level,
            )
            key_check = CryptoProvider.compute_key_check(master_key)
            cipher_key = CryptoProvider.derive_encryption_key(master_key)
            cipher = get_cipher(encryption_level, cipher_key)
            crypto_metadata = CryptoMetadataV7(salt=salt, key_check=key_check)
            metadata_size = CRYPTO_META_STRUCT.size

        states = list(self._tables.items())
        schema_bytes = _encode_schema_document([state for _name, state in states])
        table_layouts: list[_TableLayout] = []
        index_meta_blobs: list[bytes] = []
        index_data_blobs: list[bytes] = []
        for table_name, state in states:
            if self._can_reuse_persisted_table(table_name, state, changed_tables):
                layout, meta_bytes, data_bytes = self._reuse_table_layout(state)
            else:
                if state.table._lazy_loaded:
                    state.table._ensure_all_loaded()
                layout = _build_table_layout(state)
                meta_bytes, data_bytes = self._encode_table_indexes(state)
            table_layouts.append(layout)
            index_meta_blobs.append(meta_bytes)
            index_data_blobs.append(data_bytes)

        table_ref_size = sum(layout.ref_size for layout in table_layouts)
        schema_offset = HEADER_STRUCT.size + metadata_size
        table_ref_offset = schema_offset + len(schema_bytes)
        payload_offset = table_ref_offset + table_ref_size

        payload_buffer = bytearray()
        resolved_refs: list[TableBlockRef] = []
        for layout, meta_blob, data_blob in zip(table_layouts, index_meta_blobs, index_data_blobs):
            data_offset = payload_offset + len(payload_buffer)
            payload_buffer.extend(layout.data_bytes)

            pk_dir_offset = payload_offset + len(payload_buffer)
            pk_dir_bytes = _encode_pk_dir(layout.records, data_offset)
            payload_buffer.extend(pk_dir_bytes)

            index_meta_offset = payload_offset + len(payload_buffer)
            index_meta_size = len(meta_blob)
            payload_buffer.extend(meta_blob)

            index_data_offset = payload_offset + len(payload_buffer)
            index_data_size = len(data_blob)
            payload_buffer.extend(data_blob)

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

        table_ref_bytes = b"".join(ref.pack() for ref in resolved_refs)
        payload_bytes = bytes(payload_buffer)
        if cipher is not None:
            payload_bytes = cipher.encrypt(payload_bytes)

        header = FileHeaderV7(
            table_count=len(resolved_refs),
            schema_offset=schema_offset,
            schema_size=len(schema_bytes),
            table_ref_offset=table_ref_offset,
            table_ref_size=len(table_ref_bytes),
            file_size=(
                payload_offset
                + len(payload_bytes)
                + (AUTH_TAG_SIZE if master_key is not None else 0)
            ),
        )
        if encryption_level is not None:
            header = header.set_encryption(encryption_level).set_authenticated()

        crypto_metadata_bytes = (
            crypto_metadata.pack() if crypto_metadata is not None else b""
        )
        auth_tag = b""
        if master_key is not None:
            auth_tag = CryptoProvider.compute_auth_tag(
                master_key,
                (
                    header.pack(),
                    crypto_metadata_bytes,
                    schema_bytes,
                    table_ref_bytes,
                    payload_bytes,
                ),
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
                handle.write(crypto_metadata_bytes)
                handle.write(schema_bytes)
                handle.write(table_ref_bytes)
                handle.write(payload_bytes)
                handle.write(auth_tag)
            temp_path.replace(self.file_path)
            self._cipher = cipher
            self._payload_offset = payload_offset if cipher is not None else 0
            for (_table_name, state), layout, ref in zip(
                states,
                table_layouts,
                resolved_refs,
            ):
                pk_index: dict[Any, tuple[int, int]] = {}
                cursor = ref.data_offset
                for record in layout.records:
                    pk_index[record.pk] = (cursor, record.length)
                    cursor += record.length
                state.pk_index = pk_index
                state.source_ref = ref
                state.overlay = TableOverlay()
                state.table._data_file = self.file_path
                state.table._backend = self
                if state.table._lazy_loaded:
                    state.table._pk_offsets = {
                        pk: offset
                        for pk, (offset, _length) in pk_index.items()
                    }
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

    def _verify_file_authentication(self, header: FileHeaderV7, key: bytes) -> None:
        """流式校验新 PTK7 文件的长度与 HMAC-SHA256 认证标签。"""
        actual_size = self.file_path.stat().st_size
        if header.file_size != actual_size or actual_size < AUTH_TAG_SIZE:
            raise EncryptionError("PTK7 文件完整性校验失败：文件长度不匹配")

        authenticated_size = actual_size - AUTH_TAG_SIZE
        authenticator = CryptoProvider.create_authenticator(key)
        with open(self.file_path, "rb") as handle:
            remaining = authenticated_size
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise EncryptionError("PTK7 文件完整性校验失败：文件被截断")
                authenticator.update(chunk)
                remaining -= len(chunk)
            stored_tag = handle.read(AUTH_TAG_SIZE)

        if len(stored_tag) != AUTH_TAG_SIZE or not hmac.compare_digest(
            authenticator.digest(),
            stored_tag,
        ):
            raise EncryptionError("PTK7 文件完整性校验失败：认证标签无效")

    def _read_region(self, offset: int, size: int) -> bytes:
        with open(self.file_path, "rb") as handle:
            handle.seek(offset)
            data = handle.read(size)
        if len(data) < size:
            raise SerializationError(
                f"PTK7 region is incomplete at offset {offset} (need {size}, got {len(data)})"
            )
        return data

    def _read_payload_region(self, offset: int, size: int) -> bytes:
        if size == 0:
            return b""
        data = self._read_region(offset, size)
        if self._cipher is None:
            return data
        if offset < self._payload_offset:
            raise SerializationError("PTK7 encrypted payload offset is invalid")
        return self._cipher.decrypt_at(offset - self._payload_offset, data)

    @staticmethod
    def _validate_table_refs(
        header: FileHeaderV7,
        schema_doc: dict[str, Any],
        table_refs: dict[str, TableBlockRef],
    ) -> None:
        """验证 schema 与表引用数量、名称和各数据区域的文件边界。"""
        table_documents = schema_doc.get("tables")
        if not isinstance(table_documents, list):
            raise SerializationError("PTK7 schema tables must be a list")

        schema_names: list[str] = []
        for document in table_documents:
            if not isinstance(document, dict) or not isinstance(document.get("name"), str):
                raise SerializationError("PTK7 schema contains an invalid table entry")
            schema_names.append(document["name"])

        if len(schema_names) != len(set(schema_names)):
            raise SerializationError("PTK7 schema contains duplicate table names")
        if len(schema_names) != header.table_count:
            raise SerializationError("PTK7 table count does not match schema")
        if set(schema_names) != set(table_refs):
            raise SerializationError("PTK7 schema and table references do not match")

        payload_start = header.table_ref_offset + header.table_ref_size
        content_end = header.file_size
        if header.is_authenticated():
            content_end -= AUTH_TAG_SIZE

        for ref in table_refs.values():
            if ref.pk_dir_size != ref.record_count * PK_DIR_INT_STRUCT.size:
                raise SerializationError(
                    f"PTK7 primary-key directory size is invalid for table {ref.name!r}"
                )
            regions = (
                (ref.data_offset, ref.data_size),
                (ref.pk_dir_offset, ref.pk_dir_size),
                (ref.index_meta_offset, ref.index_meta_size),
                (ref.index_data_offset, ref.index_data_size),
            )
            for offset, size in regions:
                if offset < payload_start or offset + size > content_end:
                    raise SerializationError(
                        f"PTK7 table region is outside the file for table {ref.name!r}"
                    )

    def _read_pk_index(self, ref: TableBlockRef) -> dict[Any, tuple[int, int]]:
        if ref.pk_dir_size == 0:
            return {}
        blob = self._read_payload_region(ref.pk_dir_offset, ref.pk_dir_size)
        if len(blob) % PK_DIR_INT_STRUCT.size != 0:
            raise SerializationError("PTK7 pk directory size is invalid")

        pk_index: dict[Any, tuple[int, int]] = {}
        offset = 0
        while offset < len(blob):
            entry = PkDirEntry.unpack_int(blob[offset: offset + PK_DIR_INT_STRUCT.size])
            pk_index[entry.pk] = (entry.offset, entry.length)
            offset += PK_DIR_INT_STRUCT.size
        if len(pk_index) != ref.record_count:
            raise SerializationError(
                f"PTK7 primary-key count does not match table {ref.name!r}"
            )
        return pk_index

    @staticmethod
    def _validate_record_location(
        state: TableState,
        offset: int,
        length: int,
    ) -> None:
        """在读取或复用记录时验证它位于所属表数据块内。"""
        ref = state.source_ref
        if ref is None:
            raise SerializationError("PTK7 source table reference is missing")
        if (
            length < RECORD_LENGTH_STRUCT.size
            or offset < ref.data_offset
            or offset + length > ref.data_offset + ref.data_size
        ):
            raise SerializationError(
                f"PTK7 primary-key entry is outside table data for {ref.name!r}"
            )

    def _read_row_at(self, state: TableState, offset: int, length: int, pk: Any) -> dict[str, Any]:
        payload_length = length - RECORD_LENGTH_STRUCT.size
        if payload_length < 0:
            raise SerializationError("PTK7 record length is invalid")

        raw = self._read_payload_region(offset, length)
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
    length: int

@dataclass
class _TableLayout:
    table_name: str
    next_id: int
    records: list[_RecordLayout]
    data_bytes: bytes
    ref_size: int

def _build_table_layout(state: TableState) -> _TableLayout:
    columns = list(state.table.columns.values())
    records: list[_RecordLayout] = []
    data_bytes = bytearray()
    for pk, record in sorted(state.table.data.items(), key=lambda item: item[0]):
        payload = encode_row(columns, record, pk_name=state.table.primary_key)
        entry_bytes = RECORD_LENGTH_STRUCT.pack(len(payload)) + payload
        data_bytes.extend(entry_bytes)
        records.append(_RecordLayout(pk=pk, length=len(entry_bytes)))

    return _TableLayout(
        table_name=state.table.name,
        next_id=state.table.next_id,
        records=records,
        data_bytes=bytes(data_bytes),
        ref_size=_table_ref_size(state.table.name),
    )


def _table_ref_size(table_name: str) -> int:
    """返回指定表名对应的 PTK7 表引用字节数。"""
    return (
        TABLE_REF_PREFIX_STRUCT.size
        + len(table_name.encode("utf-8"))
        + TABLE_REF_BODY_STRUCT.size
    )

def _encode_pk_dir(records: list[_RecordLayout], data_offset: int) -> bytes:
    pk_dir = bytearray()
    cursor = data_offset
    for record in records:
        entry = PkDirEntry(pk=record.pk, offset=cursor, length=record.length)
        pk_dir.extend(entry.pack_int())
        cursor += record.length
    return bytes(pk_dir)

def _find_primary_key(columns: list[Column]) -> str | None:
    for column in columns:
        if column.primary_key:
            return column.name
    return None

def _encode_schema_document(states: list[TableState]) -> bytes:
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

def _decode_schema_document(blob: bytes) -> dict[str, Any]:
    try:
        document = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SerializationError("Failed to decode PTK7 schema document") from exc
    if not isinstance(document, dict) or "tables" not in document:
        raise SerializationError("Invalid PTK7 schema document")
    return document

def _column_to_schema(column: Column) -> dict[str, Any]:
    return {
        "name": column.name,
        "type_name": TypeRegistry.get_type_name(column.col_type),
        "nullable": column.nullable,
        "primary_key": column.primary_key,
        "index": column.index,
        "comment": column.comment,
    }

def _column_from_schema(document: dict[str, Any]) -> Column:
    return Column(
        TypeRegistry.get_type_by_name(document["type_name"]),
        name=document["name"],
        nullable=bool(document.get("nullable", True)),
        primary_key=bool(document.get("primary_key", False)),
        index=document.get("index", False),
        comment=document.get("comment"),
    )

def _decode_table_refs(blob: bytes) -> dict[str, TableBlockRef]:
    refs: dict[str, TableBlockRef] = {}
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

def probe_ptk7(file_path: str | Path) -> tuple[bool, dict[str, Any] | None]:
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
        header.validate_layout(file_stat.st_size)
    except SerializationError:
        return False, {"error": "invalid_layout"}

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
    "PytuckStore",
    "probe_pytuck",
]

# Backwards/compatibility aliases required by Task 2 wiring
PytuckStore = StorePTK7
probe_pytuck = probe_ptk7
