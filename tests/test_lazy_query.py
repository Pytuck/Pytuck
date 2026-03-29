"""
懒加载查询测试

验证 pytuck 引擎在 lazy 模式下，标准查询路径也能按需读取磁盘记录。
"""

from pathlib import Path
from typing import Type

from pytuck import Storage, Session, Column, PureBaseModel, declarative_base, insert, select
from pytuck.common.options import BinaryBackendOptions


class TestLazyQuery:
    """懒加载查询测试"""

    def _create_users_db(self, temp_dir: Path) -> Path:
        """创建并填充测试数据库"""
        db_path = temp_dir / 'lazy_query.pytuck'
        db = Storage(file_path=str(db_path), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, index=True)
            age = Column(int)

        session = Session(db)
        session.execute(insert(User).values(name='Alice', age=20))
        session.execute(insert(User).values(name='Bob', age=30))
        session.commit()
        db.flush()
        session.close()
        db.close()
        return db_path

    def _create_sorted_users_db(self, temp_dir: Path) -> Path:
        """创建带有序索引的测试数据库"""
        db_path = temp_dir / 'lazy_query_sorted.pytuck'
        db = Storage(file_path=str(db_path), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int, index='sorted')

        session = Session(db)
        session.execute(insert(User).values(name='Charlie', age=35))
        session.execute(insert(User).values(name='Alice', age=20))
        session.execute(insert(User).values(name='Bob', age=30))
        session.commit()
        db.flush()
        session.close()
        db.close()
        return db_path

    def test_select_where_reads_matching_record_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 select.where 应按需读出匹配记录"""
        db_path = self._create_users_db(temp_dir)

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, index=True)
            age = Column(int)

        assert db.tables['users'].data == {}

        session = Session(db)
        users = session.execute(select(User).where(User.name == 'Alice')).all()

        assert len(users) == 1
        assert users[0].name == 'Alice'
        assert users[0].age == 20

        session.close()
        db.close()

    def test_select_where_without_index_still_scans_lazy_records(self, temp_dir: Path) -> None:
        """lazy 模式下无索引条件查询也应能扫描磁盘记录"""
        db_path = self._create_users_db(temp_dir)

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, index=True)
            age = Column(int)

        assert db.tables['users'].data == {}

        session = Session(db)
        users = session.execute(select(User).where(User.age >= 25)).all()

        assert len(users) == 1
        assert users[0].name == 'Bob'
        assert users[0].age == 30

        session.close()
        db.close()

    def test_count_rows_returns_real_count_in_lazy_mode(self, temp_dir: Path) -> None:
        """lazy 模式下 count_rows 应返回真实行数"""
        db_path = self._create_users_db(temp_dir)

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        assert db.tables['users'].data == {}
        assert db.count_rows('users') == 2

        db.close()

    def test_order_by_sorted_index_reads_lazy_records(self, temp_dir: Path) -> None:
        """lazy 模式下 order_by 应能走有序索引并读出磁盘记录"""
        db_path = self._create_sorted_users_db(temp_dir)

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int, index='sorted')

        assert db.tables['users'].data == {}

        session = Session(db)
        users = session.execute(select(User).order_by('age')).all()

        assert [user.name for user in users] == ['Alice', 'Bob', 'Charlie']

        session.close()
        db.close()

    def test_lazy_load_preserves_sorted_index_type(self, temp_dir: Path) -> None:
        """lazy 打开后 sorted 索引应保持范围查询能力"""
        db_path = self._create_sorted_users_db(temp_dir)

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )

        age_index = db.tables['users'].indexes['age']
        assert age_index.supports_range_query() is True

        db.close()

    def test_ensure_all_loaded_keeps_lazy_indexes_usable(self, temp_dir: Path) -> None:
        """_ensure_all_loaded 只补齐 data，不应破坏 lazy 打开时已恢复的索引"""
        db_path = self._create_users_db(temp_dir)

        db = Storage(
            file_path=str(db_path),
            engine='pytuck',
            backend_options=BinaryBackendOptions(lazy_load=True)
        )
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, index=True)
            age = Column(int)

        table = db.tables['users']
        assert table.data == {}
        assert table.indexes['name'].lookup('Alice') == {1}

        table._ensure_all_loaded()

        assert set(table.data.keys()) == {1, 2}
        assert table.indexes['name'].lookup('Alice') == {1}

        session = Session(db)
        users = session.execute(select(User).where(User.name == 'Alice')).all()

        assert [user.name for user in users] == ['Alice']

        session.close()
        db.close()
