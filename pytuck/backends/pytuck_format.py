from __future__ import annotations

"""
Pytuck 单文件格式 v7 低层原语。
"""

from dataclasses import dataclass, replace
import struct
from typing import Any

from ..common.crypto import get_encryption_level_code, get_encryption_level_name
from ..common.exceptions import SerializationError
from ..core.orm import Column
from ..core.types import TypeRegistry

MAGIC_V7 = b"PTK7"
HEADER_STRUCT = struct.Struct("<4sHHIQQQQQQI")
CRYPTO_META_STRUCT = struct.Struct("<16s4s")
TABLE_REF_PREFIX_STRUCT = struct.Struct("<H")
TABLE_REF_BODY_STRUCT = struct.Struct("<QQQQQQQQQQ")
PK_DIR_INT_STRUCT = struct.Struct("<qQI")
NULL_BITMAP_STRUCT = struct.Struct("<I")

@dataclass(frozen=True)
class CryptoMetadataV7:
    salt: bytes = b"\x00" * 16
    key_check: bytes = b"\x00" * 4

    def pack(self) -> bytes:
        return CRYPTO_META_STRUCT.pack(
            self.salt[:16].ljust(16, b"\x00"),
            self.key_check[:4].ljust(4, b"\x00"),
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CryptoMetadataV7":
        if len(data) < CRYPTO_META_STRUCT.size:
            raise SerializationError(
                f"Not enough data to decode CryptoMetadataV7 (need {CRYPTO_META_STRUCT.size}, got {len(data)})"
            )
        salt, key_check = CRYPTO_META_STRUCT.unpack(data[: CRYPTO_META_STRUCT.size])
        return cls(salt=salt, key_check=key_check)

@dataclass(frozen=True)
class FileHeaderV7:
    FLAG_ENCRYPTION_ENABLED = 0x02
    FLAG_ENCRYPTION_LEVEL_MASK = 0x0C
    FLAG_ENCRYPTION_LEVEL_SHIFT = 2

    magic: bytes = MAGIC_V7
    version: int = 7
    flags: int = 0
    table_count: int = 0
    schema_offset: int = HEADER_STRUCT.size
    schema_size: int = 0
    table_ref_offset: int = 0
    table_ref_size: int = 0
    file_size: int = 0
    checksum: int = 0
    reserved: int = 0

    def pack(self) -> bytes:
        return HEADER_STRUCT.pack(
            self.magic,
            self.version,
            self.flags,
            self.table_count,
            self.schema_offset,
            self.schema_size,
            self.table_ref_offset,
            self.table_ref_size,
            self.file_size,
            self.checksum,
            self.reserved,
        )

    def is_encrypted(self) -> bool:
        return (self.flags & self.FLAG_ENCRYPTION_ENABLED) != 0

    def get_encryption_level(self) -> str | None:
        if not self.is_encrypted():
            return None
        level_code = (self.flags & self.FLAG_ENCRYPTION_LEVEL_MASK) >> self.FLAG_ENCRYPTION_LEVEL_SHIFT
        return get_encryption_level_name(level_code)

    def set_encryption(self, level: str) -> "FileHeaderV7":
        level_code = get_encryption_level_code(level)
        if level_code == 0:
            raise SerializationError(f"Invalid PTK7 encryption level: {level}")
        flags = self.flags | self.FLAG_ENCRYPTION_ENABLED
        flags = (flags & ~self.FLAG_ENCRYPTION_LEVEL_MASK) | (level_code << self.FLAG_ENCRYPTION_LEVEL_SHIFT)
        return replace(self, flags=flags)

    @classmethod
    def unpack(cls, data: bytes) -> "FileHeaderV7":
        if len(data) < HEADER_STRUCT.size:
            raise SerializationError(
                f"Not enough data to decode FileHeaderV7 (need {HEADER_STRUCT.size}, got {len(data)})"
            )
        values = HEADER_STRUCT.unpack(data[: HEADER_STRUCT.size])
        header = cls(*values)
        if header.magic != MAGIC_V7:
            raise SerializationError(f"Invalid PTK7 magic: expected {MAGIC_V7!r}, got {header.magic!r}")
        if header.version != 7:
            raise SerializationError(f"Unsupported PTK7 version: {header.version}")
        return header

@dataclass(frozen=True)
class TableBlockRef:
    name: str
    record_count: int
    next_id: int
    data_offset: int
    data_size: int
    pk_dir_offset: int
    pk_dir_size: int
    index_meta_offset: int
    index_meta_size: int
    index_data_offset: int
    index_data_size: int

    def pack(self) -> bytes:
        name_bytes = self.name.encode("utf-8")
        if len(name_bytes) > 0xFFFF:
            raise SerializationError("Table name too long for PTK7 TableBlockRef")
        return b"".join(
            [
                TABLE_REF_PREFIX_STRUCT.pack(len(name_bytes)),
                name_bytes,
                TABLE_REF_BODY_STRUCT.pack(
                    self.record_count,
                    self.next_id,
                    self.data_offset,
                    self.data_size,
                    self.pk_dir_offset,
                    self.pk_dir_size,
                    self.index_meta_offset,
                    self.index_meta_size,
                    self.index_data_offset,
                    self.index_data_size,
                ),
            ]
        )

    @classmethod
    def unpack(cls, data: bytes) -> "TableBlockRef":
        if len(data) < TABLE_REF_PREFIX_STRUCT.size:
            raise SerializationError("Not enough data to decode TableBlockRef name length")
        name_length = TABLE_REF_PREFIX_STRUCT.unpack(data[: TABLE_REF_PREFIX_STRUCT.size])[0]
        name_start = TABLE_REF_PREFIX_STRUCT.size
        name_end = name_start + name_length
        body_end = name_end + TABLE_REF_BODY_STRUCT.size
        if len(data) < body_end:
            raise SerializationError("Not enough data to decode TableBlockRef")
        try:
            name = data[name_start:name_end].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SerializationError("Invalid UTF-8 table name in TableBlockRef") from exc
        body = TABLE_REF_BODY_STRUCT.unpack(data[name_end:body_end])
        return cls(name, *body)

@dataclass(frozen=True)
class PkDirEntry:
    pk: Any
    offset: int
    length: int

    def pack_int(self) -> bytes:
        if not isinstance(self.pk, int):
            raise SerializationError(f"Expected int pk, got {type(self.pk)}")
        return PK_DIR_INT_STRUCT.pack(self.pk, self.offset, self.length)

    @classmethod
    def unpack_int(cls, data: bytes) -> "PkDirEntry":
        if len(data) < PK_DIR_INT_STRUCT.size:
            raise SerializationError(
                f"Not enough data to decode int pk entry (need {PK_DIR_INT_STRUCT.size}, got {len(data)})"
            )
        pk, offset, length = PK_DIR_INT_STRUCT.unpack(data[: PK_DIR_INT_STRUCT.size])
        return cls(pk=pk, offset=offset, length=length)

def encode_row(columns: list[Column], record: dict[str, Any], pk_name: str | None = None) -> bytes:
    payload_columns = [column for column in columns if column.name != pk_name]
    null_bits = 0
    payload = bytearray()
    for index, column in enumerate(payload_columns):
        col_name = column.name
        assert col_name is not None, "Column.name must be set"
        value = record.get(col_name)
        if value is None:
            null_bits |= 1 << index
            continue
        _, codec = TypeRegistry.get_codec(column.col_type)
        payload.extend(codec.encode(value))
    return NULL_BITMAP_STRUCT.pack(null_bits) + bytes(payload)

def decode_row(columns: list[Column], payload: bytes, pk_name: str | None = None) -> dict[str, Any]:
    if len(payload) < NULL_BITMAP_STRUCT.size:
        raise SerializationError(
            f"Not enough data to decode row payload (need at least {NULL_BITMAP_STRUCT.size}, got {len(payload)})"
        )

    payload_columns = [column for column in columns if column.name != pk_name]
    null_bits = NULL_BITMAP_STRUCT.unpack(payload[: NULL_BITMAP_STRUCT.size])[0]
    offset = NULL_BITMAP_STRUCT.size
    record: dict[str, Any] = {}
    for index, column in enumerate(payload_columns):
        col_name = column.name
        assert col_name is not None, "Column.name must be set"
        if null_bits & (1 << index):
            record[col_name] = None
            continue
        _, codec = TypeRegistry.get_codec(column.col_type)
        value, consumed = codec.decode(payload[offset:])
        offset += consumed
        record[col_name] = value
    return record

__all__ = [
    "MAGIC_V7",
    "HEADER_STRUCT",
    "CRYPTO_META_STRUCT",
    "PK_DIR_INT_STRUCT",
    "CryptoMetadataV7",
    "FileHeaderV7",
    "TableBlockRef",
    "PkDirEntry",
    "encode_row",
    "decode_row",
]
