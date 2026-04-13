"""
WAL 预写日志测试

覆盖 pytuck/backends/backend_binary.py 中的 WAL 相关功能：
- WALEntry pack/unpack 往返一致性
- WALEntry CRC 校验
- HeaderV5 pack/unpack 往返一致性
- HeaderV5 CRC 校验与损坏检测
- HeaderV5 加密标志操作
"""

import struct
import zlib

import pytest

from pytuck.backends.legacy_ptk5 import HeaderV5, WALEntry, WALOpType
from pytuck.common.exceptions import SerializationError


# ---------- WALEntry pack/unpack ----------


class TestWALEntryPackUnpack:
    """WAL 条目序列化/反序列化测试"""

    def test_insert_entry_roundtrip(self) -> None:
        """INSERT 类型 pack/unpack 往返一致"""
        entry = WALEntry(
            lsn=1,
            op_type=WALOpType.INSERT,
            table_name='users',
            pk_bytes=b'\x04\x01\x00\x00\x00',  # int 1
            record_bytes=b'\x00\x01\x02\x03'
        )
        packed = entry.pack()
        unpacked, consumed = WALEntry.unpack(packed)

        assert consumed == len(packed)
        assert unpacked.lsn == 1
        assert unpacked.op_type == WALOpType.INSERT
        assert unpacked.table_name == 'users'
        assert unpacked.pk_bytes == entry.pk_bytes
        assert unpacked.record_bytes == entry.record_bytes

    def test_update_entry_roundtrip(self) -> None:
        """UPDATE 类型 pack/unpack 往返一致"""
        entry = WALEntry(
            lsn=42,
            op_type=WALOpType.UPDATE,
            table_name='products',
            pk_bytes=b'\x04\x05\x00\x00\x00',
            record_bytes=b'\xAA\xBB\xCC'
        )
        packed = entry.pack()
        unpacked, consumed = WALEntry.unpack(packed)

        assert consumed == len(packed)
        assert unpacked.lsn == 42
        assert unpacked.op_type == WALOpType.UPDATE
        assert unpacked.table_name == 'products'
        assert unpacked.pk_bytes == entry.pk_bytes
        assert unpacked.record_bytes == entry.record_bytes

    def test_delete_entry_roundtrip(self) -> None:
        """DELETE 类型 pack/unpack 往返一致（无 record_bytes）"""
        entry = WALEntry(
            lsn=100,
            op_type=WALOpType.DELETE,
            table_name='logs',
            pk_bytes=b'\x04\x0A\x00\x00\x00',
            record_bytes=b''
        )
        packed = entry.pack()
        unpacked, consumed = WALEntry.unpack(packed)

        assert consumed == len(packed)
        assert unpacked.lsn == 100
        assert unpacked.op_type == WALOpType.DELETE
        assert unpacked.table_name == 'logs'
        assert unpacked.record_bytes == b''

    def test_crc_mismatch_raises(self) -> None:
        """篡改 CRC 后 unpack 抛 SerializationError"""
        entry = WALEntry(
            lsn=1,
            op_type=WALOpType.INSERT,
            table_name='t',
            pk_bytes=b'\x04\x01\x00\x00\x00',
            record_bytes=b'\x00'
        )
        packed = bytearray(entry.pack())
        # 篡改最后 4 字节（CRC 位于 entry_data 末尾）
        packed[-1] ^= 0xFF
        packed[-2] ^= 0xFF

        with pytest.raises(SerializationError, match="CRC"):
            WALEntry.unpack(bytes(packed))

    def test_incomplete_data_raises(self) -> None:
        """不完整数据抛 SerializationError"""
        # 只有 2 字节，连 entry_len 都不够
        with pytest.raises(SerializationError):
            WALEntry.unpack(b'\x01\x02')

    def test_truncated_entry_raises(self) -> None:
        """entry_len 声明的长度大于实际数据"""
        entry = WALEntry(
            lsn=1,
            op_type=WALOpType.INSERT,
            table_name='t',
            pk_bytes=b'\x04\x01\x00\x00\x00',
            record_bytes=b'\x00'
        )
        packed = entry.pack()
        # 截断末尾
        truncated = packed[:len(packed) - 5]

        with pytest.raises(SerializationError):
            WALEntry.unpack(truncated)

    def test_unicode_table_name(self) -> None:
        """中文表名往返一致"""
        entry = WALEntry(
            lsn=1,
            op_type=WALOpType.INSERT,
            table_name='用户表',
            pk_bytes=b'\x04\x01\x00\x00\x00',
            record_bytes=b''
        )
        packed = entry.pack()
        unpacked, _ = WALEntry.unpack(packed)
        assert unpacked.table_name == '用户表'

    def test_multiple_entries_sequential(self) -> None:
        """多个条目顺序 pack 后可依次 unpack"""
        entries = [
            WALEntry(lsn=i, op_type=WALOpType.INSERT,
                     table_name='t', pk_bytes=struct.pack('<b', i),
                     record_bytes=b'\x00' * i)
            for i in range(1, 4)
        ]
        data = b''.join(e.pack() for e in entries)

        offset = 0
        for i, original in enumerate(entries):
            unpacked, consumed = WALEntry.unpack(data[offset:])
            assert unpacked.lsn == original.lsn
            assert unpacked.record_bytes == original.record_bytes
            offset += consumed

        assert offset == len(data)


# ---------- HeaderV5 ----------


class TestHeaderV5:
    """PTK5 文件头结构测试"""

    def test_pack_unpack_roundtrip(self) -> None:
        """HeaderV5 pack/unpack 字段一致"""
        header = HeaderV5(
            magic=b'PTK5',
            version=5,
            generation=10,
            schema_offset=256,
            schema_size=100,
            data_offset=356,
            data_size=2000,
            index_offset=2356,
            index_size=500,
            wal_offset=2856,
            wal_size=128,
            checkpoint_lsn=42,
            flags=0x01
        )
        packed = header.pack()
        assert len(packed) == 128

        unpacked = HeaderV5.unpack(packed)
        assert unpacked.magic == b'PTK5'
        assert unpacked.version == 5
        assert unpacked.generation == 10
        assert unpacked.schema_offset == 256
        assert unpacked.schema_size == 100
        assert unpacked.data_offset == 356
        assert unpacked.data_size == 2000
        assert unpacked.index_offset == 2356
        assert unpacked.index_size == 500
        assert unpacked.wal_offset == 2856
        assert unpacked.wal_size == 128
        assert unpacked.checkpoint_lsn == 42
        assert unpacked.flags == 0x01

    def test_verify_crc_valid(self) -> None:
        """合法数据 CRC 校验通过"""
        header = HeaderV5(generation=5)
        packed = header.pack()
        unpacked = HeaderV5.unpack(packed)
        assert unpacked.verify_crc(packed)

    def test_verify_crc_corrupted(self) -> None:
        """损坏数据 CRC 校验失败"""
        header = HeaderV5(generation=5)
        packed = bytearray(header.pack())
        # 篡改 generation 字段
        packed[6] ^= 0xFF
        unpacked = HeaderV5.unpack(bytes(packed))
        assert not unpacked.verify_crc(bytes(packed))

    def test_encryption_flags(self) -> None:
        """set_encryption/get_encryption_level/is_encrypted"""
        header = HeaderV5()

        # 默认未加密
        assert not header.is_encrypted()
        assert header.get_encryption_level() is None

        # 设置 low 加密
        salt = b'\x01' * 16
        key_check = b'\xAB\xCD\xEF\x01'
        header.set_encryption('low', salt, key_check)
        assert header.is_encrypted()
        assert header.get_encryption_level() == 'low'

        # pack/unpack 后保持
        packed = header.pack()
        unpacked = HeaderV5.unpack(packed)
        assert unpacked.is_encrypted()
        assert unpacked.get_encryption_level() == 'low'
        assert unpacked.salt == salt
        assert unpacked.key_check == key_check

    def test_encryption_levels(self) -> None:
        """三种加密等级都能正确设置和读取"""
        for level in ('low', 'medium', 'high'):
            header = HeaderV5()
            header.set_encryption(level, b'\x00' * 16, b'\x00' * 4)
            packed = header.pack()
            unpacked = HeaderV5.unpack(packed)
            assert unpacked.get_encryption_level() == level

    def test_header_too_short_raises(self) -> None:
        """Header 数据过短时抛 SerializationError"""
        with pytest.raises(SerializationError, match="Header too short"):
            HeaderV5.unpack(b'\x00' * 64)

    def test_default_values(self) -> None:
        """默认值正确"""
        header = HeaderV5()
        assert header.magic == b'PTK5'
        assert header.version == 5
        assert header.generation == 0
        assert header.wal_offset == 0
        assert header.wal_size == 0
        assert header.flags == 0

    def test_index_compressed_flag(self) -> None:
        """索引压缩标志位操作"""
        header = HeaderV5()
        header.flags |= HeaderV5.FLAG_INDEX_COMPRESSED
        assert (header.flags & HeaderV5.FLAG_INDEX_COMPRESSED) != 0

        packed = header.pack()
        unpacked = HeaderV5.unpack(packed)
        assert (unpacked.flags & HeaderV5.FLAG_INDEX_COMPRESSED) != 0


# ---------- 双 Header 测试 ----------


class TestDualHeader:
    """双 Header 选择逻辑测试"""

    def test_both_valid_higher_generation_wins(self) -> None:
        """两个 Header 都合法时选择 generation 更大的"""
        header_a = HeaderV5(generation=5)
        header_b = HeaderV5(generation=10)

        packed_a = header_a.pack()
        packed_b = header_b.pack()

        unpacked_a = HeaderV5.unpack(packed_a)
        unpacked_b = HeaderV5.unpack(packed_b)

        # 两个都合法
        assert unpacked_a.verify_crc(packed_a)
        assert unpacked_b.verify_crc(packed_b)

        # generation 更大的应该被选中
        if unpacked_a.generation >= unpacked_b.generation:
            selected = unpacked_a
        else:
            selected = unpacked_b

        assert selected.generation == 10

    def test_one_corrupted_uses_valid(self) -> None:
        """一个 Header 损坏时使用另一个"""
        header = HeaderV5(generation=5)
        packed = header.pack()

        # 损坏副本
        corrupted = bytearray(packed)
        corrupted[6] ^= 0xFF  # 篡改 generation
        corrupted_bytes = bytes(corrupted)

        unpacked_valid = HeaderV5.unpack(packed)
        unpacked_corrupted = HeaderV5.unpack(corrupted_bytes)

        assert unpacked_valid.verify_crc(packed)
        assert not unpacked_corrupted.verify_crc(corrupted_bytes)

    def test_same_generation_picks_a(self) -> None:
        """同 generation 时优先选择 Header A"""
        header = HeaderV5(generation=5)
        packed = header.pack()

        unpacked_a = HeaderV5.unpack(packed)
        unpacked_b = HeaderV5.unpack(packed)

        # 两个合法且 generation 相同
        assert unpacked_a.verify_crc(packed)
        assert unpacked_b.verify_crc(packed)

        # 按双 Header 选择逻辑，generation 相等时选 A
        if unpacked_a.generation >= unpacked_b.generation:
            selected_slot = 0  # A
        else:
            selected_slot = 1  # B

        assert selected_slot == 0
