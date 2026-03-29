"""
懒加载 schema 操作测试

验证 pytuck 引擎在 lazy 模式下，scan 和整表 schema 操作也能正确处理磁盘中的记录。
"""

from pathlib import Path
from typing import Type

from pytuck import Storage, Column, PureBaseModel, declarative_base
from pytuck.common.options import BinaryBackendOptions


class TestLazySchema:
    """懒加载 schema 操作测试"""

    def _create_users_db(self, temp_dir: Path) -> Path:
        """创建并填充测试数据库"""
        db_path = temp_dir / 'lazy_schema.pytuck'
        db = Storage(file_path=str(db_path), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            email = Column(str)
            age = Column(int)

        db.insert('users', {'id': 1, 'name': 'Alice', 'email': 'alice@test.com', 'age': 20})
        db.insert('users', {'id': 2, 'name': 'Bob', 'email': 'bob@test.com', 'age': 30})
        db.flush()
        db.close()
        return db_path

    def test_scan_reads_disk_records_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 scan 应能遍历磁盘记录"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}

        rows = list(table.scan())

        assert len(rows) == 2
        assert {record['name'] for _, record in rows} == {'Alice', 'Bob'}
        assert set(table.data.keys()) == {1, 2}

        db.close()

    def test_build_index_reads_disk_records_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 build_index 应基于磁盘记录建立索引"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}
        assert 'name' not in table.indexes

        table.build_index('name')

        assert table.indexes['name'].lookup('Alice') == {1}
        assert table.indexes['name'].lookup('Bob') == {2}
        assert set(table.data.keys()) == {1, 2}

        db.close()

    def test_add_column_fills_disk_records_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 add_column 应填充磁盘记录"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}

        table.add_column(Column(str, name='status'), default_value='active')

        assert table.data[1]['status'] == 'active'
        assert table.data[2]['status'] == 'active'

        db.close()

    def test_alter_column_converts_disk_records_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 alter_column 应转换磁盘记录"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}

        table.alter_column('age', col_type=str)

        assert table.columns['age'].col_type == str
        assert table.data[1]['age'] == '20'
        assert table.data[2]['age'] == '30'

        db.close()

    def test_set_primary_key_reads_disk_records_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 set_primary_key 应基于磁盘记录重建主键"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}

        table.set_primary_key('email')

        assert table.primary_key == 'email'
        assert 'alice@test.com' in table.data
        assert 'bob@test.com' in table.data
        assert 1 not in table.data
        assert 2 not in table.data

        db.close()

    def test_set_primary_key_marks_dirty_and_clears_lazy_offsets(self, temp_dir: Path) -> None:
        """lazy 模式下 set_primary_key 后应设置脏标志并清空旧主键 offset 映射"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}
        assert table._pk_offsets is not None
        assert set(table._pk_offsets.keys()) == {1, 2}

        table.set_primary_key('email')

        assert table._schema_dirty is True
        assert table._data_dirty is True
        assert table._pk_offsets is None
        assert set(table.data.keys()) == {'alice@test.com', 'bob@test.com'}

        db.close()

    def test_reorder_columns_marks_dirty_and_reorders_record_keys(self, temp_dir: Path) -> None:
        """lazy 模式下 reorder_columns 应设置脏标志并更新记录字段顺序"""
        db_path = self._create_users_db(temp_dir)
        from pytuck.common.options import BinaryBackendOptions
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        table = db.tables['users']
        assert table.data == {}

        # Force materialize one record to test record key ordering
        table._ensure_all_loaded()
        assert set(table.data.keys()) == {1, 2}

        table.reorder_columns(['age', 'email', 'name', 'id'])

        assert table._schema_dirty is True
        assert table._data_dirty is True

        # 检查字段顺序
        first = table.data[next(iter(table.data))]
        assert list(first.keys()) == ['age', 'email', 'name', 'id']

        db.close()
