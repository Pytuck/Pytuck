"""
JSONL 后端 ZIP 密码功能测试

覆盖范围：
- 带密码保存和加载
- 错误密码 / 无密码读取
- probe() 检测加密状态
- get_metadata() 处理加密情况
- 密码校验边界
"""

import zipfile
from pathlib import Path
from typing import Type

import pytest

from pytuck import Column, CRUDBaseModel, EncryptionError, SerializationError, Storage, declarative_base
from pytuck.backends.backend_jsonl import JSONLBackend
from pytuck.common.exceptions import ValidationError
from pytuck.common.options import JsonlBackendOptions


class TestJsonlEncryptionBasic:
    """JSONL 加密基本功能测试"""

    def test_save_and_load_with_password(self, tmp_path: Path) -> None:
        """带密码保存和加载"""
        db_path = tmp_path / 'encrypted_jsonl.zip'
        password = 'test_password_123'

        options = JsonlBackendOptions(password=password)
        db = Storage(file_path=str(db_path), engine='jsonl', backend_options=options)
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int, nullable=True)

        User.create(id=1, name='Alice', age=25)
        User.create(id=2, name='Bob', age=30)
        db.flush()
        db.close()

        with zipfile.ZipFile(str(db_path), 'r') as zf:
            encrypted = any((info.flag_bits & 0x1) != 0 for info in zf.infolist())
            assert encrypted is True

        db2 = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=password)
        )
        Base2: Type[CRUDBaseModel] = declarative_base(db2, crud=True)

        class User2(Base2):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int, nullable=True)

        users = User2.all()
        assert len(users) == 2
        assert users[0].name == 'Alice'
        assert users[1].name == 'Bob'
        db2.close()

    def test_load_with_wrong_password(self, tmp_path: Path) -> None:
        """错误密码应抛出 EncryptionError"""
        db_path = tmp_path / 'encrypted_jsonl.zip'
        correct_password = 'correct_password'
        wrong_password = 'wrong_password'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=correct_password)
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        with pytest.raises((EncryptionError, SerializationError)):
            Storage(
                file_path=str(db_path),
                engine='jsonl',
                backend_options=JsonlBackendOptions(password=wrong_password)
            )

    def test_load_encrypted_without_password(self, tmp_path: Path) -> None:
        """加密 ZIP 无密码时应抛出 EncryptionError"""
        db_path = tmp_path / 'encrypted_jsonl.zip'
        password = 'test_password'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=password)
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        with pytest.raises(EncryptionError) as exc_info:
            Storage(file_path=str(db_path), engine='jsonl', backend_options=JsonlBackendOptions())

        assert 'encrypted' in str(exc_info.value).lower()


class TestJsonlEncryptionProbe:
    """JSONL 加密 probe() 功能测试"""

    def test_probe_encrypted_file(self, tmp_path: Path) -> None:
        """probe() 应检测到加密状态"""
        db_path = tmp_path / 'encrypted_jsonl.zip'
        password = 'test_password'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=password)
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        matched, info = JSONLBackend.probe(str(db_path))
        assert matched is True
        assert info is not None
        assert info.get('engine') == 'jsonl'
        assert info.get('encrypted') is True
        assert info.get('requires_password') is True
        assert info.get('confidence') == 'medium'

    def test_probe_unencrypted_file(self, tmp_path: Path) -> None:
        """probe() 对未加密文件应保持原有行为"""
        db_path = tmp_path / 'plain_jsonl.zip'

        db = Storage(file_path=str(db_path), engine='jsonl', backend_options=JsonlBackendOptions())
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        matched, info = JSONLBackend.probe(str(db_path))
        assert matched is True
        assert info is not None
        assert info.get('engine') == 'jsonl'
        assert info.get('encrypted') is not True
        assert info.get('confidence') == 'high'


class TestJsonlEncryptionMetadata:
    """JSONL 加密 get_metadata() 功能测试"""

    def test_get_metadata_encrypted_with_password(self, tmp_path: Path) -> None:
        """加密文件使用正确密码获取 metadata"""
        db_path = tmp_path / 'encrypted_jsonl.zip'
        password = 'test_password'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=password)
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        backend = JSONLBackend(str(db_path), JsonlBackendOptions(password=password))
        metadata = backend.get_metadata()
        assert metadata.get('engine') == 'jsonl'
        assert metadata.get('encrypted') is True
        assert metadata.get('table_count') == 1
        assert metadata.get('version') == 1

    def test_get_metadata_encrypted_without_password(self, tmp_path: Path) -> None:
        """加密文件无密码时 get_metadata 返回有限信息"""
        db_path = tmp_path / 'encrypted_jsonl.zip'
        password = 'test_password'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=password)
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        backend = JSONLBackend(str(db_path), JsonlBackendOptions())
        metadata = backend.get_metadata()
        assert metadata.get('engine') == 'jsonl'
        assert metadata.get('encrypted') is True
        assert metadata.get('requires_password') is True
        assert metadata.get('table_count') is None

    def test_get_metadata_encrypted_with_wrong_password(self, tmp_path: Path) -> None:
        """加密文件使用错误密码时返回 incorrect_password"""
        db_path = tmp_path / 'encrypted_jsonl.zip'
        correct_password = 'test_password'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=correct_password)
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        backend = JSONLBackend(str(db_path), JsonlBackendOptions(password='wrong_password'))
        metadata = backend.get_metadata()
        assert metadata.get('engine') == 'jsonl'
        assert metadata.get('encrypted') is True
        assert metadata.get('error') == 'incorrect_password'


class TestJsonlEncryptionMultiTable:
    """JSONL 加密多表测试"""

    def test_multiple_tables_encrypted(self, tmp_path: Path) -> None:
        """多表加密存储"""
        db_path = tmp_path / 'multi_table_jsonl.zip'
        password = 'multi_table_password'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=password)
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        class Product(Base):
            __tablename__ = 'products'
            id = Column(int, primary_key=True)
            title = Column(str)
            price = Column(float)

        User.create(id=1, name='Alice')
        Product.create(id=1, title='Book', price=19.99)
        db.flush()
        db.close()

        db2 = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password=password)
        )
        Base2: Type[CRUDBaseModel] = declarative_base(db2, crud=True)

        class User2(Base2):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        class Product2(Base2):
            __tablename__ = 'products'
            id = Column(int, primary_key=True)
            title = Column(str)
            price = Column(float)

        assert len(User2.all()) == 1
        assert len(Product2.all()) == 1
        db2.close()


class TestJsonlEncryptionEdgeCases:
    """JSONL 加密边界情况测试"""

    def test_empty_password_is_no_encryption(self, tmp_path: Path) -> None:
        """空字符串密码等同于无密码"""
        db_path = tmp_path / 'empty_password_jsonl.zip'

        db = Storage(
            file_path=str(db_path),
            engine='jsonl',
            backend_options=JsonlBackendOptions(password='')
        )
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        User.create(id=1, name='Alice')
        db.flush()
        db.close()

        with zipfile.ZipFile(str(db_path), 'r') as zf:
            encrypted = any((info.flag_bits & 0x1) != 0 for info in zf.infolist())
            assert encrypted is False

    def test_unicode_password_rejected(self) -> None:
        """中文/Unicode 密码应在创建 Options 时被拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            JsonlBackendOptions(password='密码123中文')

        assert 'ASCII' in str(exc_info.value)

    def test_password_reassignment_validated(self) -> None:
        """密码重新赋值时也应校验"""
        opts = JsonlBackendOptions(password='valid123')

        with pytest.raises(ValidationError):
            opts.password = '密码123'
