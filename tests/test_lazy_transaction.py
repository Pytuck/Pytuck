"""
懒加载事务测试

验证 pytuck 引擎在 lazy 模式下，事务回滚也能正确恢复磁盘记录与 lazy 元数据。
"""

from pathlib import Path

import pytest

from pytuck import Storage, Column
from pytuck.common.options import PytuckBackendOptions


class TestLazyTransaction:
    """懒加载事务测试"""

    def _create_users_db(self, temp_dir: Path) -> Path:
        """创建并填充测试数据库"""
        db_path = temp_dir / 'lazy_transaction.pytuck'
        db = Storage(file_path=str(db_path), engine='pytuck')
        db.create_table(
            'users',
            [
                Column(int, name='id', primary_key=True),
                Column(str, name='name')
            ]
        )
        db.insert('users', {'id': 1, 'name': 'Alice'})
        db.flush()
        db.close()
        return db_path

    def test_update_insert_rollback_restores_lazy_state(self, temp_dir: Path) -> None:
        """lazy 模式下 update + insert 回滚后应恢复数据与 dirty 标记"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=PytuckBackendOptions()
        )

        table = db.tables['users']
        assert table._lazy_loaded is True
        assert table.data == {}
        assert table._pk_offsets is not None
        assert set(table._pk_offsets.keys()) == {1}
        assert table._data_dirty is False
        assert table._schema_dirty is False

        with pytest.raises(RuntimeError):
            with db.transaction():
                db.update('users', 1, {'name': 'Alice2'})
                db.insert('users', {'id': 2, 'name': 'Bob'})

                assert table._data_dirty is True
                assert table.has_pk(2) is True

                raise RuntimeError('boom')

        assert table._lazy_loaded is True
        assert table.data == {}
        assert table._pk_offsets is not None
        assert set(table._pk_offsets.keys()) == {1}
        assert table._data_dirty is False
        assert table._schema_dirty is False
        assert table.has_pk(2) is False
        assert db.count_rows('users') == 1
        assert db.select('users', 1)['name'] == 'Alice'

        db.close()

    def test_delete_rollback_restores_lazy_state(self, temp_dir: Path) -> None:
        """lazy 模式下 delete 回滚后应恢复主键 offset 与 dirty 标记"""
        db_path = self._create_users_db(temp_dir)
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=PytuckBackendOptions()
        )

        table = db.tables['users']
        assert table._lazy_loaded is True
        assert table.data == {}
        assert table._pk_offsets is not None
        assert set(table._pk_offsets.keys()) == {1}
        assert table._data_dirty is False
        assert table._schema_dirty is False

        with pytest.raises(RuntimeError):
            with db.transaction():
                db.delete('users', 1)

                assert table._data_dirty is True
                assert table._pk_offsets is not None
                assert 1 not in table._pk_offsets

                raise RuntimeError('boom')

        assert table._lazy_loaded is True
        assert table.data == {}
        assert table._pk_offsets is not None
        assert set(table._pk_offsets.keys()) == {1}
        assert table._data_dirty is False
        assert table._schema_dirty is False
        assert db.count_rows('users') == 1
        assert db.select('users', 1)['name'] == 'Alice'

        db.close()
