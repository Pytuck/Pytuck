"""
懒加载测试

覆盖 pytuck/backends/backend_binary.py 的懒加载功能：
- 启用懒加载后表标记为 _lazy_loaded
- 懒加载模式下按主键查询单条记录
- 索引字段在懒加载下工作
- 全表数据加载（populate_tables_with_data）
- 加密模式下懒加载正常工作（通过 decrypt_at 实现按需解密）
- 多表懒加载
"""

from pathlib import Path
from typing import Type

import pytest

from pytuck import Storage, declarative_base, Session, Column
from pytuck import PureBaseModel, insert, select
from pytuck.common.options import BinaryBackendOptions
from pytuck.backends.backend_binary import BinaryBackend


# ---------- 懒加载基础测试 ----------


class TestLazyLoadBasic:
    """懒加载基础功能测试"""

    def _create_and_populate(self, temp_dir: Path) -> Path:
        """创建并填充数据库文件，返回路径"""
        db_path = temp_dir / 'lazy.pytuck'
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions()
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int, nullable=True)

        session = Session(db)
        session.execute(insert(User).values(name='Alice', age=20))
        session.execute(insert(User).values(name='Bob', age=25))
        session.execute(insert(User).values(name='Charlie', age=30))
        session.commit()
        db.flush()
        db.close()

        return db_path

    def test_lazy_load_enabled(self, temp_dir: Path) -> None:
        """启用懒加载后 table._lazy_loaded=True"""
        db_path = self._create_and_populate(temp_dir)

        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=True))
        tables = backend.load()

        assert 'users' in tables
        table = tables['users']
        assert table._lazy_loaded is True
        # 懒加载模式下 data 应该为空
        assert len(table.data) == 0
        # 但 pk_offsets 应该有数据
        assert table._pk_offsets is not None
        assert len(table._pk_offsets) == 3

    def test_lazy_load_query_single(self, temp_dir: Path) -> None:
        """懒加载模式下按主键查询单条记录"""
        db_path = self._create_and_populate(temp_dir)

        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=True))
        tables = backend.load()
        table = tables['users']

        # 通过 get 按需加载
        record = table.get(1)
        assert record['name'] == 'Alice'
        assert record['age'] == 20

        record2 = table.get(2)
        assert record2['name'] == 'Bob'
        assert record2['age'] == 25

    def test_lazy_load_query_nonexistent(self, temp_dir: Path) -> None:
        """懒加载下查询不存在的主键"""
        from pytuck.common.exceptions import RecordNotFoundError

        db_path = self._create_and_populate(temp_dir)

        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=True))
        tables = backend.load()
        table = tables['users']

        with pytest.raises(RecordNotFoundError):
            table.get(999)

    def test_lazy_load_with_index(self, temp_dir: Path) -> None:
        """索引字段在懒加载下被恢复"""
        db_path = temp_dir / 'lazy_idx.pytuck'
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions()
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, index=True)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.execute(insert(User).values(name='Bob'))
        session.execute(insert(User).values(name='Alice'))
        session.commit()
        db.flush()
        db.close()

        # 懒加载打开
        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=True))
        tables = backend.load()
        table = tables['users']

        # materialize 全表后索引可用
        backend.populate_tables_with_data(tables)
        # 数据已加载，按 name 字段统计 Alice 出现次数
        names = [r['name'] for r in table.data.values()]
        assert names.count('Alice') == 2

    def test_lazy_load_supports_flag(self, temp_dir: Path) -> None:
        """supports_lazy_loading 返回正确值"""
        backend_lazy = BinaryBackend('test.pytuck', BinaryBackendOptions(lazy_load=True))
        assert backend_lazy.supports_lazy_loading() is True

        backend_normal = BinaryBackend('test.pytuck', BinaryBackendOptions(lazy_load=False))
        assert backend_normal.supports_lazy_loading() is False


# ---------- 填充数据测试 ----------


class TestPopulateTablesWithData:
    """populate_tables_with_data 测试"""

    def test_populate_fills_all_records(self, temp_dir: Path) -> None:
        """populate 后 table.data 包含所有记录"""
        db_path = temp_dir / 'lazy_populate.pytuck'
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions()
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.execute(insert(User).values(name='Bob'))
        session.commit()
        db.flush()
        db.close()

        # 懒加载打开
        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=True))
        tables = backend.load()

        # 数据未加载
        assert len(tables['users'].data) == 0

        # populate
        backend.populate_tables_with_data(tables)

        # 数据已加载
        assert len(tables['users'].data) == 2
        names = {r['name'] for r in tables['users'].data.values()}
        assert names == {'Alice', 'Bob'}

    def test_populate_idempotent(self, temp_dir: Path) -> None:
        """多次 populate 幂等"""
        db_path = temp_dir / 'lazy_idem.pytuck'
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions()
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.commit()
        db.flush()
        db.close()

        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=True))
        tables = backend.load()

        backend.populate_tables_with_data(tables)
        assert len(tables['users'].data) == 1

        # 再次 populate 应该幂等
        backend.populate_tables_with_data(tables)
        assert len(tables['users'].data) == 1

    def test_populate_non_lazy_noop(self, temp_dir: Path) -> None:
        """非懒加载模式下 populate 是 no-op"""
        db_path = temp_dir / 'non_lazy.pytuck'
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions()
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.commit()
        db.flush()
        db.close()

        # 非懒加载模式
        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=False))
        tables = backend.load()
        # 默认 reopen 语义：load 后 data 为空，直到 materialize
        assert len(tables['users'].data) == 0  # 数据尚未加载

        # populate 是 no-op，但可以按需 materialize
        backend.populate_tables_with_data(tables)
        # 按需读取任一主键以 materialize
        record = tables['users'].get(1)
        assert record['name'] == 'Alice'


# ---------- 加密与懒加载交互 ----------


class TestLazyLoadWithEncryption:
    """加密模式下懒加载行为测试"""

    def _create_encrypted_db(self, db_path: Path, level: str = 'low', password: str = 'test') -> None:
        """创建加密数据库并填充数据"""
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(
                encryption=level, password=password
            )
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int, nullable=True)

        session = Session(db)
        session.execute(insert(User).values(name='Alice', age=20))
        session.execute(insert(User).values(name='Bob', age=25))
        session.execute(insert(User).values(name='Charlie', age=30))
        session.commit()
        db.flush()
        db.close()

    def test_encrypted_lazy_load_low(self, temp_dir: Path) -> None:
        """low 级别加密 + 懒加载正常工作"""
        db_path = temp_dir / 'enc_lazy_low.pytuck'
        self._create_encrypted_db(db_path, level='low')

        backend = BinaryBackend(
            str(db_path),
            BinaryBackendOptions(lazy_load=True, encryption='low', password='test')
        )
        tables = backend.load()
        table = tables['users']

        # 应该是懒加载
        assert table._lazy_loaded is True
        assert len(table.data) == 0

        # 按需读取正确
        assert table.get(1)['name'] == 'Alice'
        assert table.get(1)['age'] == 20
        assert table.get(2)['name'] == 'Bob'
        assert table.get(3)['name'] == 'Charlie'

    def test_encrypted_lazy_load_all_records_match(self, temp_dir: Path) -> None:
        """加密懒加载读取所有记录，与全量加载结果一致"""
        db_path = temp_dir / 'enc_lazy_match.pytuck'
        self._create_encrypted_db(db_path)

        # 全量加载
        backend_full = BinaryBackend(
            str(db_path),
            BinaryBackendOptions(lazy_load=False, encryption='low', password='test')
        )
        tables_full = backend_full.load()
        full_data = dict(tables_full['users'].data)

        # 懒加载
        backend_lazy = BinaryBackend(
            str(db_path),
            BinaryBackendOptions(lazy_load=True, encryption='low', password='test')
        )
        tables_lazy = backend_lazy.load()
        table_lazy = tables_lazy['users']

        # 逐条对比
        for pk, expected_record in full_data.items():
            lazy_record = table_lazy.get(pk)
            assert lazy_record == expected_record, f"pk={pk}: {lazy_record} != {expected_record}"

    def test_encrypted_lazy_load_populate(self, temp_dir: Path) -> None:
        """加密懒加载后 populate_tables_with_data 正确填充"""
        db_path = temp_dir / 'enc_lazy_populate.pytuck'
        self._create_encrypted_db(db_path)

        backend = BinaryBackend(
            str(db_path),
            BinaryBackendOptions(lazy_load=True, encryption='low', password='test')
        )
        tables = backend.load()

        # 懒加载，数据未加载
        assert len(tables['users'].data) == 0

        # populate 填充数据
        backend.populate_tables_with_data(tables)

        # 数据已加载
        assert len(tables['users'].data) == 3
        names = {r['name'] for r in tables['users'].data.values()}
        assert names == {'Alice', 'Bob', 'Charlie'}

    def test_encrypted_lazy_load_multi_table(self, temp_dir: Path) -> None:
        """多表加密懒加载"""
        db_path = temp_dir / 'enc_lazy_multi.pytuck'
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(encryption='low', password='secret')
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        class Product(Base):
            __tablename__ = 'products'
            id = Column(int, primary_key=True)
            title = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.execute(insert(User).values(name='Bob'))
        session.execute(insert(Product).values(title='Widget'))
        session.execute(insert(Product).values(title='Gadget'))
        session.commit()
        db.flush()
        db.close()

        # 加密懒加载
        backend = BinaryBackend(
            str(db_path),
            BinaryBackendOptions(lazy_load=True, encryption='low', password='secret')
        )
        tables = backend.load()

        # 两个表都应该是懒加载
        assert tables['users']._lazy_loaded is True
        assert tables['products']._lazy_loaded is True

        # 按需读取
        assert tables['users'].get(1)['name'] == 'Alice'
        assert tables['users'].get(2)['name'] == 'Bob'
        assert tables['products'].get(1)['title'] == 'Widget'
        assert tables['products'].get(2)['title'] == 'Gadget'


# ---------- decrypt_at 一致性测试 ----------


class TestDecryptAtConsistency:
    """验证 decrypt_at 与 decrypt 结果一致"""

    def test_xor_cipher_decrypt_at(self) -> None:
        """XORCipher.decrypt_at 与完整 decrypt 结果一致"""
        from pytuck.common.crypto import XORCipher
        key = b'test-key-for-xor-cipher'
        cipher = XORCipher(key)

        plaintext = b'Hello, World! This is a test of XOR cipher random access decryption.'
        encrypted = cipher.encrypt(plaintext)

        # 从各种偏移位置解密片段
        for offset in [0, 5, 13, 32, 50]:
            for length in [1, 4, 10, 15]:
                end = min(offset + length, len(encrypted))
                fragment = encrypted[offset:end]
                decrypted = cipher.decrypt_at(offset, fragment)
                assert decrypted == plaintext[offset:end], \
                    f"XOR decrypt_at failed at offset={offset}, length={length}"

    def test_lcg_cipher_decrypt_at(self) -> None:
        """LCGCipher.decrypt_at 与完整 decrypt 结果一致"""
        from pytuck.common.crypto import LCGCipher
        key = b'test-key-for-lcg-cipher'
        cipher = LCGCipher(key)

        plaintext = b'Hello, World! This is a test of LCG cipher random access decryption.'
        encrypted = cipher.encrypt(plaintext)

        # 从各种偏移位置解密片段
        for offset in [0, 5, 13, 32, 50]:
            for length in [1, 4, 10, 15]:
                end = min(offset + length, len(encrypted))
                fragment = encrypted[offset:end]
                decrypted = cipher.decrypt_at(offset, fragment)
                assert decrypted == plaintext[offset:end], \
                    f"LCG decrypt_at failed at offset={offset}, length={length}"

    def test_chacha20_cipher_decrypt_at(self) -> None:
        """ChaCha20Cipher.decrypt_at 与完整 decrypt 结果一致"""
        from pytuck.common.crypto import ChaCha20Cipher
        key = b'test-key-for-chacha20-cipher!!!!'  # 需要足够长
        cipher = ChaCha20Cipher(key)

        # 使用较大的数据以跨越多个 64 字节块
        plaintext = b'A' * 200 + b'B' * 100 + b'C' * 50
        encrypted = cipher.encrypt(plaintext)

        # 从各种偏移位置解密片段，包括跨块边界
        test_cases = [
            (0, 10),       # 第一个块内
            (60, 10),      # 跨第一和第二个块的边界
            (64, 10),      # 第二个块开头
            (128, 20),     # 第三个块
            (0, 64),       # 完整第一个块
            (0, 128),      # 两个完整块
            (100, 200),    # 跨多个块的大片段
        ]
        for offset, length in test_cases:
            end = min(offset + length, len(encrypted))
            fragment = encrypted[offset:end]
            decrypted = cipher.decrypt_at(offset, fragment)
            assert decrypted == plaintext[offset:end], \
                f"ChaCha20 decrypt_at failed at offset={offset}, length={length}"

    def test_decrypt_at_full_data(self) -> None:
        """decrypt_at(0, data) 等价于 decrypt(data)"""
        from pytuck.common.crypto import XORCipher, LCGCipher, ChaCha20Cipher

        plaintext = b'Full data decryption test with various cipher types.'

        for CipherClass, key in [
            (XORCipher, b'key1'),
            (LCGCipher, b'key2'),
            (ChaCha20Cipher, b'key3'),
        ]:
            cipher = CipherClass(key)
            encrypted = cipher.encrypt(plaintext)

            # decrypt_at(0, ...) 应等价于 decrypt(...)
            assert cipher.decrypt_at(0, encrypted) == cipher.decrypt(encrypted)


# ---------- 多表懒加载 ----------


class TestLazyLoadMultipleTables:
    """多表懒加载测试"""

    def test_multiple_tables_lazy(self, temp_dir: Path) -> None:
        """多表都能独立懒加载"""
        db_path = temp_dir / 'lazy_multi.pytuck'
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions()
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        class Product(Base):
            __tablename__ = 'products'
            id = Column(int, primary_key=True)
            title = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.execute(insert(User).values(name='Bob'))
        session.execute(insert(Product).values(title='Widget'))
        session.commit()
        db.flush()
        db.close()

        # 懒加载
        backend = BinaryBackend(str(db_path), BinaryBackendOptions(lazy_load=True))
        tables = backend.load()

        assert 'users' in tables
        assert 'products' in tables

        # 两个表都应该是懒加载状态
        assert tables['users']._lazy_loaded is True
        assert tables['products']._lazy_loaded is True

        # 按需读取
        assert tables['users'].get(1)['name'] == 'Alice'
        assert tables['products'].get(1)['title'] == 'Widget'
