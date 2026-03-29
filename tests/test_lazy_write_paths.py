"""
懒加载写路径测试

验证 pytuck 引擎在 lazy 模式下，写路径仍能正确处理磁盘中的记录。
"""

from pathlib import Path
from typing import Type

import pytest

from pytuck import Storage, Column, PureBaseModel, declarative_base, DuplicateKeyError
from pytuck.common.options import BinaryBackendOptions


class TestLazyWritePaths:
    """懒加载写路径测试"""

    def _create_users_db(self, temp_dir: Path) -> Path:
        """创建并填充测试数据库"""
        db_path = temp_dir / 'lazy_write_paths.pytuck'
        db = Storage(file_path=str(db_path), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int)

        db.insert('users', {'id': 1, 'name': 'Alice', 'age': 20})
        db.insert('users', {'id': 2, 'name': 'Bob', 'age': 30})
        db.flush()
        db.close()
        return db_path

    def test_insert_duplicate_pk_still_raises_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下显式插入重复主键仍应抛 DuplicateKeyError"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        assert db.tables['users'].data == {}

        with pytest.raises(DuplicateKeyError):
            db.insert('users', {'id': 1, 'name': 'Eve', 'age': 99})

        db.close()

    def test_update_existing_disk_record_succeeds_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 update 应能命中磁盘中的记录"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        assert db.tables['users'].data == {}

        db.update('users', 1, {'age': 21})

        updated = db.select('users', 1)
        assert updated['name'] == 'Alice'
        assert updated['age'] == 21

        db.close()

    def test_delete_existing_disk_record_succeeds_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 delete 应能删除磁盘中的记录"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        assert db.tables['users'].data == {}

        db.delete('users', 1)

        assert db.count_rows('users') == 1
        remaining = db.select('users', 2)
        assert remaining['name'] == 'Bob'

        db.close()

    def test_bulk_insert_duplicate_pk_still_raises_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 bulk_insert 显式插入重复主键仍应抛 DuplicateKeyError"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        assert db.tables['users'].data == {}

        with pytest.raises(DuplicateKeyError):
            db.bulk_insert('users', [{'id': 1, 'name': 'Eve', 'age': 99}])

        db.close()

    def test_bulk_update_existing_disk_record_succeeds_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 bulk_update 应能命中磁盘中的记录"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        assert db.tables['users'].data == {}

        updated_count = db.bulk_update('users', [(1, {'age': 21}), (2, {'age': 31})])

        assert updated_count == 2
        assert db.select('users', 1)['age'] == 21
        assert db.select('users', 2)['age'] == 31

        db.close()

    def test_flush_preserves_untouched_lazy_tables_during_full_checkpoint(self, temp_dir: Path) -> None:
        """lazy 模式下 flush 全量 checkpoint 不应写丢未改动表的数据"""
        db_path = temp_dir / 'lazy_flush_checkpoint.pytuck'
        db = Storage(file_path=str(db_path), engine='pytuck')
        db.create_table('users', [Column(int, name='id', primary_key=True), Column(str, name='name')])
        db.create_table('products', [Column(int, name='id', primary_key=True), Column(str, name='title')])
        db.insert('users', {'id': 1, 'name': 'Alice'})
        db.insert('products', {'id': 1, 'title': 'Book'})
        db.flush()
        db.close()

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        users = db.tables['users']
        products = db.tables['products']
        assert users.data == {}
        assert products.data == {}
        assert users._pk_offsets is not None
        assert products._pk_offsets is not None
        assert set(users._pk_offsets.keys()) == {1}
        assert set(products._pk_offsets.keys()) == {1}

        db.update('users', 1, {'name': 'Alice2'})
        db.flush()
        db.close()

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=False)
        )

        assert db.select('users', 1)['name'] == 'Alice2'
        assert db.select('products', 1)['title'] == 'Book'

        db.close()

    def test_ensure_all_loaded_materializes_disk_records_in_lazy_mode(self, temp_dir: Path) -> None:
        """_ensure_all_loaded 应将 lazy 表的磁盘记录全部加载到内存"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}

        table._ensure_all_loaded()

        assert set(table.data.keys()) == {1, 2}
        assert table.data[1]['name'] == 'Alice'
        assert table.data[2]['name'] == 'Bob'

        db.close()
