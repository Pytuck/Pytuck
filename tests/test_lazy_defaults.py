"""
懒加载默认值测试

验证 pytuck 引擎以当前默认配置重新打开文件时，会沿用统一的 lazy reopen 语义。
"""

from pathlib import Path

from pytuck import Storage, Column
from pytuck.common.options import get_default_backend_options, PytuckBackendOptions


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

    def test_default_backend_options_returns_current_pytuck_options(self) -> None:
        """pytuck 默认后端选项应只暴露当前字段"""
        opts = get_default_backend_options('pytuck')

        assert isinstance(opts, PytuckBackendOptions)
        assert opts.encryption is None
        assert opts.password is None

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

    def test_explicit_backend_options_still_uses_reopen_path(self, temp_dir: Path) -> None:
        """显式传入当前 pytuck 选项时，重新打开仍应沿用统一 lazy 语义"""
        db_path = self._create_users_db(temp_dir, 'lazy_explicit_options.pytuck')
        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=PytuckBackendOptions()
        )

        table = db.tables['users']
        # 当前 pytuck reopen 语义：重新打开后默认以 lazy 路径 materialize 数据
        assert table._lazy_loaded is True
        assert table.data == {}
        assert db.select('users', 1)['name'] == 'Alice'

        db.close()
