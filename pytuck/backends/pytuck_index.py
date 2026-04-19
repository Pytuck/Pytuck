from __future__ import annotations

"""
PTK7 排序索引块编码与解码。
"""

import struct
from typing import Any

from ..common.exceptions import SerializationError
from ..core.orm import Column
from ..core.types import TypeCode, TypeRegistry

INDEX_HEADER_STRUCT = struct.Struct("<BI")
PK_STRUCT = struct.Struct("<q")

def encode_sorted_pairs(pairs: list[tuple[Any, int]], column: Column) -> bytes:
    type_code, codec = TypeRegistry.get_codec(column.col_type)
    encoded = bytearray()
    encoded.extend(INDEX_HEADER_STRUCT.pack(int(type_code), len(pairs)))
    for value, pk in pairs:
        encoded.extend(codec.encode(value))
        encoded.extend(PK_STRUCT.pack(int(pk)))
    return bytes(encoded)

def decode_sorted_pairs(blob: bytes, column: Column) -> list[tuple[Any, int]]:
    if len(blob) < INDEX_HEADER_STRUCT.size:
        raise SerializationError(
            f"Not enough data to decode sorted pair header (need {INDEX_HEADER_STRUCT.size}, got {len(blob)})"
        )

    stored_type_code, count = INDEX_HEADER_STRUCT.unpack(blob[: INDEX_HEADER_STRUCT.size])
    expected_type_code, _ = TypeRegistry.get_codec(column.col_type)
    if stored_type_code != int(expected_type_code):
        raise SerializationError(
            f"Sorted pair type mismatch: expected {int(expected_type_code)}, got {stored_type_code}"
        )

    try:
        _, codec = TypeRegistry.get_codec_by_code(TypeCode(stored_type_code))
    except (ValueError, SerializationError) as exc:
        raise SerializationError(f"Unknown sorted pair type code: {stored_type_code}") from exc

    offset = INDEX_HEADER_STRUCT.size
    pairs: list[tuple[Any, int]] = []
    for _ in range(count):
        value, consumed = codec.decode(blob[offset:])
        offset += consumed
        if offset + PK_STRUCT.size > len(blob):
            raise SerializationError("Not enough data to decode sorted pair pk")
        pk = PK_STRUCT.unpack(blob[offset: offset + PK_STRUCT.size])[0]
        offset += PK_STRUCT.size
        pairs.append((value, pk))
    return pairs

__all__ = [
    "INDEX_HEADER_STRUCT",
    "PK_STRUCT",
    "encode_sorted_pairs",
    "decode_sorted_pairs",
]
