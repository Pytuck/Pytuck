from dataclasses import replace
from pathlib import Path

import pytest

from pytuck import Column, Storage
from pytuck.backends.pytuck_format import (
    AUTH_TAG_SIZE,
    CRYPTO_META_STRUCT,
    FileHeaderV7,
    HEADER_STRUCT,
    PK_DIR_INT_STRUCT,
    PkDirEntry,
    TABLE_REF_BODY_STRUCT,
    TABLE_REF_PREFIX_STRUCT,
    TableBlockRef,
    encode_row,
)
from pytuck.backends.pytuck_index import decode_sorted_pairs, encode_sorted_pairs
from pytuck.common.exceptions import SerializationError


def test_file_header_v7_roundtrip() -> None:
    header = FileHeaderV7(version=7, table_count=2, schema_offset=64, schema_size=128)
    packed = header.pack()
    assert len(packed) == 64
    assert FileHeaderV7.unpack(packed) == header


def test_file_header_v7_validates_plain_layout() -> None:
    schema_size = 24
    table_ref_size = 12
    file_size = HEADER_STRUCT.size + schema_size + table_ref_size + 8
    header = FileHeaderV7(
        table_count=1,
        schema_offset=HEADER_STRUCT.size,
        schema_size=schema_size,
        table_ref_offset=HEADER_STRUCT.size + schema_size,
        table_ref_size=table_ref_size,
        file_size=file_size,
    )

    header.validate_layout(file_size)


def test_file_header_v7_rejects_truncated_authenticated_layout() -> None:
    schema_offset = HEADER_STRUCT.size + CRYPTO_META_STRUCT.size
    header = FileHeaderV7(
        table_count=1,
        schema_offset=schema_offset,
        schema_size=24,
        table_ref_offset=schema_offset + 24,
        table_ref_size=12,
        file_size=schema_offset + 24 + 12 + 8 + AUTH_TAG_SIZE,
    ).set_encryption("high").set_authenticated()

    with pytest.raises(SerializationError, match="file size mismatch"):
        header.validate_layout(header.file_size - 1)


def test_file_header_v7_rejects_authenticated_flag_without_encryption() -> None:
    """认证标签不能脱离加密标志存在，否则读取路径不会执行认证。"""
    schema_size = 24
    table_ref_size = 12
    file_size = HEADER_STRUCT.size + schema_size + table_ref_size + AUTH_TAG_SIZE
    header = FileHeaderV7(
        table_count=1,
        flags=FileHeaderV7.FLAG_AUTHENTICATED,
        schema_offset=HEADER_STRUCT.size,
        schema_size=schema_size,
        table_ref_offset=HEADER_STRUCT.size + schema_size,
        table_ref_size=table_ref_size,
        file_size=file_size,
    )

    with pytest.raises(SerializationError, match="requires encryption"):
        header.validate_layout(file_size)


def test_pk_dir_entry_roundtrip() -> None:
    entry = PkDirEntry(pk=42, offset=1024, length=37)
    assert PkDirEntry.unpack_int(entry.pack_int()) == entry


def test_table_block_ref_roundtrip() -> None:
    ref = TableBlockRef(
        name="users",
        record_count=2,
        next_id=3,
        data_offset=256,
        data_size=128,
        pk_dir_offset=384,
        pk_dir_size=64,
        index_meta_offset=448,
        index_meta_size=32,
        index_data_offset=480,
        index_data_size=96,
    )
    assert TableBlockRef.unpack(ref.pack()) == ref


def test_encode_row_skips_primary_key_payload() -> None:
    columns = [
        Column(int, name="id", primary_key=True),
        Column(str, name="name"),
    ]
    payload = encode_row(columns, {"id": 1, "name": "Alice"}, pk_name="id")
    assert payload


def test_sorted_pairs_roundtrip() -> None:
    column = Column(str, name="name", index=True)
    pairs = [("Alice", 1), ("Alice", 3), ("Bob", 2)]
    blob = encode_sorted_pairs(pairs, column)
    assert decode_sorted_pairs(blob, column) == pairs


def _write_plain_database(path: Path) -> None:
    db = Storage(file_path=path, engine="pytuck")
    db.create_table(
        "items",
        [
            Column(int, name="id", primary_key=True),
            Column(str, name="value"),
        ],
    )
    db.insert("items", {"id": 7, "value": "seven"})
    db.flush()
    db.close()


def _first_table_ref_body_offset(raw: bytes, header: FileHeaderV7) -> int:
    name_length = TABLE_REF_PREFIX_STRUCT.unpack_from(raw, header.table_ref_offset)[0]
    return header.table_ref_offset + TABLE_REF_PREFIX_STRUCT.size + name_length


def test_pytuck_open_rejects_table_count_mismatch(tmp_path: Path) -> None:
    """文件头表数量必须与 schema 和表引用一致。"""
    path = tmp_path / "count-mismatch.pytuck"
    _write_plain_database(path)
    raw = bytearray(path.read_bytes())
    header = FileHeaderV7.unpack(raw[:HEADER_STRUCT.size])
    raw[:HEADER_STRUCT.size] = replace(header, table_count=2).pack()
    path.write_bytes(raw)

    with pytest.raises(SerializationError, match="table count"):
        Storage(file_path=path, engine="pytuck")


def test_pytuck_open_rejects_table_region_outside_file(tmp_path: Path) -> None:
    """表引用声明的数据区域不得越过实际文件边界。"""
    path = tmp_path / "region-outside.pytuck"
    _write_plain_database(path)
    raw = bytearray(path.read_bytes())
    header = FileHeaderV7.unpack(raw[:HEADER_STRUCT.size])
    body_offset = _first_table_ref_body_offset(raw, header)
    body = list(TABLE_REF_BODY_STRUCT.unpack_from(raw, body_offset))
    body[2] = header.file_size + 1
    TABLE_REF_BODY_STRUCT.pack_into(raw, body_offset, *body)
    path.write_bytes(raw)

    with pytest.raises(SerializationError, match="outside the file"):
        Storage(file_path=path, engine="pytuck")


def test_pytuck_open_rejects_primary_key_entry_outside_table_data(
    tmp_path: Path,
) -> None:
    """主键目录中的记录偏移必须落在所属表的数据块内。"""
    path = tmp_path / "pk-outside.pytuck"
    _write_plain_database(path)
    raw = bytearray(path.read_bytes())
    header = FileHeaderV7.unpack(raw[:HEADER_STRUCT.size])
    body_offset = _first_table_ref_body_offset(raw, header)
    body = TABLE_REF_BODY_STRUCT.unpack_from(raw, body_offset)
    pk_dir_offset = body[4]
    pk, _record_offset, length = PK_DIR_INT_STRUCT.unpack_from(raw, pk_dir_offset)
    PK_DIR_INT_STRUCT.pack_into(raw, pk_dir_offset, pk, header.file_size + 1, length)
    path.write_bytes(raw)

    damaged = Storage(file_path=path, engine="pytuck")
    with pytest.raises(SerializationError, match="outside table data"):
        damaged.select("items", 7)
