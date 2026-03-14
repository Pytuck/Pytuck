"""
测试 Table 脏标记和后端增量保存功能
"""

import tempfile
import zipfile
from pathlib import Path
from typing import Type
from unittest.mock import patch, MagicMock

import pytest

from pytuck import Storage, Column, Session, declarative_base
from pytuck import PureBaseModel, CRUDBaseModel
from pytuck import select, insert, update, delete
from pytuck.core.storage import Table
from pytuck.core.orm import Column as ColumnClass


# ==================== TestTableDirtyFlag ====================

class TestTableDirtyFlag:
    """测试 Table 级别脏标记"""

    def _make_table(self) -> Table:
        """创建测试用 Table"""
        cols = [
            ColumnClass(int, name='id', primary_key=True),
            ColumnClass(str, name='name'),
            ColumnClass(int, name='age'),
        ]
        return Table('users', cols, primary_key='id')

    def test_initial_not_dirty(self) -> None:
        """新创建的 Table 默认不脏"""
        table = self._make_table()
        assert table._data_dirty is False
        assert table._schema_dirty is False
        assert table.is_dirty is False

    def test_dirty_after_insert(self) -> None:
        """insert 后 _data_dirty 为 True"""
        table = self._make_table()
        table.insert({'id': 1, 'name': 'Alice', 'age': 20})
        assert table._data_dirty is True
        assert table.is_dirty is True

    def test_dirty_after_update(self) -> None:
        """update 后 _data_dirty 为 True"""
        table = self._make_table()
        table.insert({'id': 1, 'name': 'Alice', 'age': 20})
        table._data_dirty = False  # 重置

        table.update(1, {'name': 'Bob'})
        assert table._data_dirty is True

    def test_dirty_after_delete(self) -> None:
        """delete 后 _data_dirty 为 True"""
        table = self._make_table()
        table.insert({'id': 1, 'name': 'Alice', 'age': 20})
        table._data_dirty = False  # 重置

        table.delete(1)
        assert table._data_dirty is True

    def test_dirty_after_bulk_insert(self) -> None:
        """bulk_insert 后 _data_dirty 为 True"""
        table = self._make_table()
        table.bulk_insert([
            {'id': 1, 'name': 'Alice', 'age': 20},
            {'id': 2, 'name': 'Bob', 'age': 25},
        ])
        assert table._data_dirty is True

    def test_dirty_after_bulk_update(self) -> None:
        """bulk_update 后 _data_dirty 为 True"""
        table = self._make_table()
        table.insert({'id': 1, 'name': 'Alice', 'age': 20})
        table.insert({'id': 2, 'name': 'Bob', 'age': 25})
        table._data_dirty = False

        table.bulk_update([(1, {'name': 'Alice2'}), (2, {'name': 'Bob2'})])
        assert table._data_dirty is True

    def test_bulk_update_no_records_not_dirty(self) -> None:
        """bulk_update 空列表时不设置脏标记"""
        table = self._make_table()
        table.bulk_update([])
        assert table._data_dirty is False

    def test_dirty_after_add_column(self) -> None:
        """add_column 后 _schema_dirty 和 _data_dirty 为 True"""
        table = self._make_table()
        new_col = ColumnClass(str, name='email')
        table.add_column(new_col)
        assert table._schema_dirty is True
        assert table._data_dirty is True

    def test_dirty_after_drop_column(self) -> None:
        """drop_column 后 _schema_dirty 和 _data_dirty 为 True"""
        table = self._make_table()
        table.drop_column('age')
        assert table._schema_dirty is True
        assert table._data_dirty is True

    def test_dirty_after_alter_column(self) -> None:
        """alter_column 后 _schema_dirty 为 True"""
        table = self._make_table()
        table.alter_column('age', nullable=False, default=0)
        assert table._schema_dirty is True

    def test_reset_dirty(self) -> None:
        """reset_dirty 清除所有脏标记"""
        table = self._make_table()
        table.insert({'id': 1, 'name': 'Alice', 'age': 20})
        new_col = ColumnClass(str, name='email')
        table.add_column(new_col)
        assert table._data_dirty is True
        assert table._schema_dirty is True

        table.reset_dirty()
        assert table._data_dirty is False
        assert table._schema_dirty is False
        assert table.is_dirty is False

    def test_is_dirty_property(self) -> None:
        """is_dirty 返回 data_dirty 或 schema_dirty 的 OR"""
        table = self._make_table()
        assert table.is_dirty is False

        table._data_dirty = True
        assert table.is_dirty is True

        table._data_dirty = False
        table._schema_dirty = True
        assert table.is_dirty is True

        table._data_dirty = True
        assert table.is_dirty is True

    def test_new_table_dirty_via_storage(self) -> None:
        """Storage.create_table 创建的表应为脏"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.db'
            db = Storage(file_path=str(db_path))
            db.create_table('users', [
                ColumnClass(int, name='id', primary_key=True),
                ColumnClass(str, name='name'),
            ])
            table = db.tables['users']
            assert table._schema_dirty is True
            assert table._data_dirty is True
            db.close()


# ==================== TestStorageFlushChangedTables ====================

class TestStorageFlushChangedTables:
    """测试 Storage.flush() 的 changed_tables 传递"""

    def test_flush_resets_dirty_flags(self) -> None:
        """flush 后所有表的脏标记被重置"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.db'
            db = Storage(file_path=str(db_path))

            Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

            class User(Base):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)

            class Post(Base):
                __tablename__ = 'posts'
                id = Column(int, primary_key=True)
                title = Column(str)

            # 初始 flush（create_table 会标记 dirty）
            db.flush()

            # 验证 flush 后脏标记已清除
            assert db.tables['users'].is_dirty is False
            assert db.tables['posts'].is_dirty is False

            # 修改一个表
            User.create(name='Alice')
            assert db.tables['users'].is_dirty is True
            assert db.tables['posts'].is_dirty is False

            # flush 后所有脏标记清除
            db.flush()
            assert db.tables['users'].is_dirty is False
            assert db.tables['posts'].is_dirty is False
            db.close()

    def test_flush_passes_changed_tables_to_backend(self) -> None:
        """flush 时正确传递 changed_tables 给 backend"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.json'
            db = Storage(file_path=str(db_path), engine='json')

            Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

            class User(Base):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)

            class Post(Base):
                __tablename__ = 'posts'
                id = Column(int, primary_key=True)
                title = Column(str)

            # 初始 flush 保存表结构
            db.flush()

            # 修改一个表
            User.create(name='Alice')

            # Mock backend.save 并检查 changed_tables 参数
            original_save = db.backend.save
            captured_args = {}

            def mock_save(tables, *, changed_tables=None):
                captured_args['changed_tables'] = changed_tables
                return original_save(tables, changed_tables=changed_tables)

            db.backend.save = mock_save
            db.flush()

            assert 'changed_tables' in captured_args
            assert captured_args['changed_tables'] == {'users'}
            db.close()


# ==================== TestCsvIncrementalSave ====================

class TestCsvIncrementalSave:
    """测试 CSV 后端增量保存"""

    def _setup_db(self, db_path: Path) -> 'Storage':
        """创建含多表的 CSV 数据库"""
        db = Storage(file_path=str(db_path), engine='csv')
        Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int)

        class Post(Base):
            __tablename__ = 'posts'
            id = Column(int, primary_key=True)
            title = Column(str)
            content = Column(str)

        class Tag(Base):
            __tablename__ = 'tags'
            id = Column(int, primary_key=True)
            label = Column(str)

        # 插入初始数据
        User.create(name='Alice', age=20)
        User.create(name='Bob', age=25)
        Post.create(title='Hello', content='World')
        Post.create(title='Foo', content='Bar')
        Tag.create(label='python')
        Tag.create(label='database')

        # 初始全量保存
        db.flush()

        return db

    def test_incremental_save_basic(self) -> None:
        """修改一个表后增量保存，数据正确"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'
            db = self._setup_db(db_path)

            # 仅修改 users 表
            db.insert('users', {'name': 'Charlie', 'age': 30})

            # 增量保存
            db.flush()

            # 重新加载验证
            db2 = Storage(file_path=str(db_path), engine='csv')
            db2.backend.load()
            loaded_tables = db2.backend.load()
            assert len(loaded_tables['users'].data) == 3
            assert len(loaded_tables['posts'].data) == 2
            assert len(loaded_tables['tags'].data) == 2
            db.close()

    def test_incremental_save_preserves_unchanged(self) -> None:
        """增量保存时未变更表的 CSV 数据被原样保留"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'
            db = self._setup_db(db_path)

            # 读取旧 ZIP 中 posts 表的原始数据
            with zipfile.ZipFile(str(db_path), 'r') as zf:
                old_posts_data = zf.read('posts.csv')

            # 仅修改 users 表
            db.insert('users', {'name': 'Charlie', 'age': 30})
            db.flush()

            # 检查新 ZIP 中 posts 表的数据
            with zipfile.ZipFile(str(db_path), 'r') as zf:
                new_posts_data = zf.read('posts.csv')

            # 未变更表的 CSV 数据应完全一致
            assert old_posts_data == new_posts_data
            db.close()

    def test_incremental_save_delete_records(self) -> None:
        """删除记录后增量保存正确"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'
            db = self._setup_db(db_path)

            # 删除 tags 表中的一条记录
            db.delete('tags', 1)
            db.flush()

            # 重新加载验证
            loaded = db.backend.load()
            assert len(loaded['tags'].data) == 1
            assert len(loaded['users'].data) == 2
            assert len(loaded['posts'].data) == 2
            db.close()

    def test_incremental_save_multiple_tables(self) -> None:
        """多表修改后增量保存正确"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'
            db = self._setup_db(db_path)

            # 修改两个表
            db.insert('users', {'name': 'Charlie', 'age': 30})
            db.insert('tags', {'label': 'testing'})
            db.flush()

            # 重新加载验证
            loaded = db.backend.load()
            assert len(loaded['users'].data) == 3
            assert len(loaded['posts'].data) == 2
            assert len(loaded['tags'].data) == 3
            db.close()

    def test_full_save_when_no_old_file(self) -> None:
        """首次保存（无旧文件）走全量路径"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'
            db = Storage(file_path=str(db_path), engine='csv')
            Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

            class User(Base):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)

            User.create(name='Alice')

            # 首次 flush（无旧文件，应走全量路径）
            db.flush()
            assert db_path.exists()

            # 重新加载验证
            loaded = db.backend.load()
            assert len(loaded['users'].data) == 1
            db.close()

    def test_full_save_with_encryption(self) -> None:
        """加密时始终走全量路径"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'

            from pytuck.common.options import CsvBackendOptions
            db = Storage(
                file_path=str(db_path), engine='csv',
                backend_options=CsvBackendOptions(password='secret123')
            )
            Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

            class User(Base):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)

            User.create(name='Alice')
            db.flush()

            User.create(name='Bob')
            # 加密模式应走全量路径（不会出错）
            db.flush()

            # 重新加载验证
            db2 = Storage(
                file_path=str(db_path), engine='csv',
                backend_options=CsvBackendOptions(password='secret123')
            )
            loaded = db2.backend.load()
            assert len(loaded['users'].data) == 2
            db.close()

    def test_incremental_correctness_reload(self) -> None:
        """增量保存后重新 load 的数据与全量保存一致"""
        with tempfile.TemporaryDirectory() as tmp:
            # 方式1：增量保存
            db_path_inc = Path(tmp) / 'inc.csv'
            db_inc = self._setup_db(db_path_inc)
            db_inc.insert('users', {'name': 'Charlie', 'age': 30})
            db_inc.flush()  # 增量保存

            # 方式2：全量保存（新建数据库，相同数据）
            db_path_full = Path(tmp) / 'full.csv'
            db_full = Storage(file_path=str(db_path_full), engine='csv')
            Base2: Type[CRUDBaseModel] = declarative_base(db_full, crud=True)

            class User2(Base2):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)
                age = Column(int)

            class Post2(Base2):
                __tablename__ = 'posts'
                id = Column(int, primary_key=True)
                title = Column(str)
                content = Column(str)

            class Tag2(Base2):
                __tablename__ = 'tags'
                id = Column(int, primary_key=True)
                label = Column(str)

            User2.create(name='Alice', age=20)
            User2.create(name='Bob', age=25)
            User2.create(name='Charlie', age=30)
            Post2.create(title='Hello', content='World')
            Post2.create(title='Foo', content='Bar')
            Tag2.create(label='python')
            Tag2.create(label='database')
            db_full.flush()

            # 两者 load 后数据应一致
            loaded_inc = db_inc.backend.load()
            loaded_full = db_full.backend.load()

            for table_name in ['users', 'posts', 'tags']:
                assert len(loaded_inc[table_name].data) == len(loaded_full[table_name].data), \
                    f"Table {table_name} record count mismatch"

            db_inc.close()
            db_full.close()

    def test_incremental_with_new_table(self) -> None:
        """增量保存期间新增表的处理"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'
            db = Storage(file_path=str(db_path), engine='csv')
            Base: Type[CRUDBaseModel] = declarative_base(db, crud=True)

            class User(Base):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)

            User.create(name='Alice')
            db.flush()

            # 添加新表
            db.create_table('logs', [
                ColumnClass(int, name='id', primary_key=True),
                ColumnClass(str, name='message'),
            ])
            db.insert('logs', {'message': 'test log'})
            db.flush()  # 增量保存应包含新表

            # 重新加载验证
            loaded = db.backend.load()
            assert 'users' in loaded
            assert 'logs' in loaded
            assert len(loaded['logs'].data) == 1
            db.close()

    def test_incremental_handles_deleted_table(self) -> None:
        """增量保存时已从 tables 中移除的表不会被保留"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'test.csv'
            db = self._setup_db(db_path)

            # 从 tables 中移除一个表（模拟删除表）
            del db.tables['tags']
            db._dirty = True

            db.flush()

            # 重新加载验证
            loaded = db.backend.load()
            assert 'users' in loaded
            assert 'posts' in loaded
            assert 'tags' not in loaded
            db.close()
