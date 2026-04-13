"""
懒加载默认值测试

验证 pytuck 引擎默认以 lazy 模式重新打开文件，且显式传入 lazy_load=False 时仍沿用 PTK7 的统一 reopen 语义。
"""

from pathlib import Path

from pytuck import Storage, Column
from pytuck.common.options import get_default_backend_options, BinaryBackendOptions


class TestLazyDefaults:
    """懒加载默认值测试"""

    def _create_users_db(self, temp_dir: Path, file_name: str) -> Path:
        """创建并填充测试数据库"""
        db_path = temp_dir / file_name
        db = Storage(file_path=str(db_path), engine='pytuck')
        db.create_table('users', [Column(int, name='id', primary_key=True), Column(str, name='name')])
        db.insert('users', {'id': 1, 'name': 'Alice'})
        db.flush()
        db.close()
        return db_path

    def test_default_backend_options_enable_lazy_load(self) -> None:
        """pytuck 默认后端选项应启用 lazy_load"""
        opts = get_default_backend_options('pytuck')

        assert isinstance(opts, BinaryBackendOptions)
        assert opts.lazy_load is True

    def test_open_without_backend_options_uses_lazy_path(self, temp_dir: Path) -> None:
        """未显式传 backend_options 时，重新打开 pytuck 文件应默认走 lazy 路径"""
        db_path = self._create_users_db(temp_dir, 'lazy_default.pytuck')
        db = Storage(file_path=str(db_path), engine='pytuck')

        table = db.tables['users']
        assert table._lazy_loaded is True
        assert table.data == {}
        assert table._pk_offsets is not None
        assert set(table._pk_offsets.keys()) == {1}
        assert db.select('users', 1)['name'] == 'Alice'

        db.close()

    def test_explicit_lazy_false_still_uses_reopen_path(self, temp_dir: Path) -> None:
        """显式 lazy_load=False 时仍应沿用 PTK7 的统一 reopen 语义"""
        db_path = self._create_users_db(temp_dir, 'lazy_explicit_false.pytuck')
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=False)
        )

        table = db.tables['users']
        # PTK7 reopen 语义：lazy_load=False 仅为兼容字段，reopen 仍为目录级 lazy 行为
        assert table._lazy_loaded is True
        assert table.data == {}
        assert db.select('users', 1)['name'] == 'Alice'

        db.close()
