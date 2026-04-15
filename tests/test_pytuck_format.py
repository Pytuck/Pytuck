from pytuck import Column
from pytuck.backends.pytuck_format import FileHeaderV7, PkDirEntry, TableBlockRef, encode_row
from pytuck.backends.pytuck_index import decode_sorted_pairs, encode_sorted_pairs


def test_file_header_v7_roundtrip() -> None:
    header = FileHeaderV7(version=7, table_count=2, schema_offset=64, schema_size=128)
    packed = header.pack()
    assert len(packed) == 64
    assert FileHeaderV7.unpack(packed) == header


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
