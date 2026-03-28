"""
DuckDB 后端原生 SQL 模式专项测试

覆盖 DuckDB 引擎的关键原生 SQL 路径：
- 默认启用 native SQL 模式
- DuplicateKeyError 映射
- count_rows() 计数
- NULL / IN 条件编译与查询
- schema-only load 后 Session.get() 查询
- 特殊列名的 SQL 引用
"""

from pathlib import Path
from typing import Type

import pytest

duckdb = pytest.importorskip('duckdb')

from pytuck import (
    Column,
    DuplicateKeyError,
    PureBaseModel,
    Session,
    Storage,
    declarative_base,
    insert,
    select,
)
from pytuck.common.options import DuckdbBackendOptions


class TestDuckdbNativeSqlDefault:
    """测试 DuckDB 默认原生 SQL 模式"""

    def test_native_mode_enabled_by_default(self, tmp_path: Path) -> None:
        """DuckDB 后端默认启用原生 SQL 模式"""
        db_file = tmp_path / 'default.duckdb'
        db = Storage(file_path=str(db_file), engine='duckdb')

        assert DuckdbBackendOptions().use_native_sql is True
        assert db.is_native_sql_mode is True

        db.close()


class TestDuckdbNativeSqlQueries:
    """测试 DuckDB 原生 SQL 查询路径"""

    def test_duplicate_key_error_via_session_insert(self, tmp_path: Path) -> None:
        """Session 原生插入遇到重复主键时抛出 DuplicateKeyError"""
        db_file = tmp_path / 'duplicate.duckdb'
        db = Storage(file_path=str(db_file), engine='duckdb')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(User).values(id=1, name='Alice'))
        session.commit()

        with pytest.raises(DuplicateKeyError) as exc_info:
            session.execute(insert(User).values(id=1, name='Bob'))

        assert exc_info.value.table_name == 'users'
        assert exc_info.value.pk == 1

        session.close()
        db.close()

    def test_count_rows_native_sql_mode(self, tmp_path: Path) -> None:
        """DuckDB 原生 SQL 模式下 count_rows 返回正确结果"""
        db_file = tmp_path / 'count_rows.duckdb'
        db = Storage(file_path=str(db_file), engine='duckdb')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        for name in ['Alice', 'Bob', 'Carol']:
            session.execute(insert(User).values(name=name))
        session.commit()

        assert db.count_rows('users') == 3

        session.close()
        db.close()

    def test_null_and_in_query_compilation(self, tmp_path: Path) -> None:
        """NULL 和 IN 条件在 DuckDB 原生查询路径下工作正常"""
        db_file = tmp_path / 'null_in.duckdb'
        db = Storage(file_path=str(db_file), engine='duckdb')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            email = Column(str, nullable=True)

        session = Session(db)
        session.execute(insert(User).values(name='Alice', email=None))
        session.execute(insert(User).values(name='Bob', email='bob@example.com'))
        session.execute(insert(User).values(name='Carol', email=None))
        session.commit()

        null_results = session.execute(
            select(User).filter_by(email=None).order_by('name')
        ).all()
        assert [user.name for user in null_results] == ['Alice', 'Carol']

        in_results = session.execute(
            select(User).where(User.name.in_(['Bob', 'Carol'])).order_by('name')
        ).all()
        assert [user.name for user in in_results] == ['Bob', 'Carol']

        session.close()
        db.close()

    def test_session_get_after_reopen_uses_schema_only_load(self, tmp_path: Path) -> None:
        """重新打开后 table.data 为空，但 Session.get() 仍可从 DuckDB 取数"""
        db_file = tmp_path / 'schema_only.duckdb'

        db1 = Storage(file_path=str(db_file), engine='duckdb')
        Base1: Type[PureBaseModel] = declarative_base(db1)

        class User(Base1):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session1 = Session(db1)
        session1.execute(insert(User).values(name='Alice'))
        session1.commit()
        session1.close()
        db1.close()

        db2 = Storage(file_path=str(db_file), engine='duckdb')
        assert 'users' in db2.tables
        assert len(db2.tables['users'].data) == 0

        Base2: Type[PureBaseModel] = declarative_base(db2)

        class User2(Base2):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session2 = Session(db2)
        alice = session2.get(User2, 1)

        assert alice is not None
        assert alice.id == 1
        assert alice.name == 'Alice'

        session2.close()
        db2.close()

    def test_backend_uses_catalog_without_pytuck_tables(self, tmp_path: Path) -> None:
        """DuckDB 后端不创建 _pytuck_tables，仍能从原生 catalog 恢复 schema 和备注"""
        db_file = tmp_path / 'catalog_only.duckdb'

        db1 = Storage(file_path=str(db_file), engine='duckdb')
        Base1: Type[PureBaseModel] = declarative_base(db1)

        class User(Base1):
            __tablename__ = 'users'
            __table_comment__ = '用户表'
            id = Column(int, primary_key=True)
            name = Column(str, comment='用户名')

        session1 = Session(db1)
        session1.execute(insert(User).values(name='Alice'))
        session1.commit()
        session1.close()
        db1.close()

        conn = duckdb.connect(str(db_file), read_only=True)
        try:
            table_names = {
                row[0]
                for row in conn.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
                ).fetchall()
            }
            table_comment = conn.execute(
                "SELECT comment FROM duckdb_tables() "
                "WHERE schema_name = 'main' AND table_name = 'users'"
            ).fetchone()
            column_comment = conn.execute(
                "SELECT comment FROM duckdb_columns() "
                "WHERE schema_name = 'main' AND table_name = 'users' AND column_name = 'name'"
            ).fetchone()
        finally:
            conn.close()

        assert 'users' in table_names
        assert '_pytuck_metadata' in table_names
        assert '_pytuck_tables' not in table_names
        assert table_comment is not None
        assert table_comment[0] == '用户表'
        assert column_comment is not None
        assert column_comment[0] == '用户名'

        db2 = Storage(file_path=str(db_file), engine='duckdb')
        table = db2.get_table('users')
        assert table.primary_key == 'id'
        assert table.comment == '用户表'
        assert table.columns['name'].comment == '用户名'
        db2.close()

    def test_custom_schema_round_trip(self, tmp_path: Path) -> None:
        """自定义 schema 下可建表、重开并继续查询"""
        db_file = tmp_path / 'custom_schema.duckdb'
        options = DuckdbBackendOptions(schema='analytics')

        db1 = Storage(file_path=str(db_file), engine='duckdb', backend_options=options)
        Base1: Type[PureBaseModel] = declarative_base(db1)

        class Event(Base1):
            __tablename__ = 'events'
            id = Column(int, primary_key=True)
            name = Column(str)

        session1 = Session(db1)
        session1.execute(insert(Event).values(name='Launch'))
        session1.commit()
        session1.close()
        db1.close()

        conn = duckdb.connect(str(db_file), read_only=True)
        try:
            tables = {
                (row[0], row[1])
                for row in conn.execute(
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_type = 'BASE TABLE'"
                ).fetchall()
            }
            event_row = conn.execute('SELECT name FROM analytics.events').fetchone()
        finally:
            conn.close()

        assert ('analytics', 'events') in tables
        assert ('main', 'events') not in tables
        assert event_row is not None
        assert event_row[0] == 'Launch'

        db2 = Storage(
            file_path=str(db_file),
            engine='duckdb',
            backend_options=DuckdbBackendOptions(schema='analytics')
        )
        assert 'events' in db2.tables
        assert len(db2.tables['events'].data) == 0

        Base2: Type[PureBaseModel] = declarative_base(db2)

        class Event2(Base2):
            __tablename__ = 'events'
            id = Column(int, primary_key=True)
            name = Column(str)

        session2 = Session(db2)
        event = session2.get(Event2, 1)

        assert event is not None
        assert event.id == 1
        assert event.name == 'Launch'

        session2.close()
        db2.close()

    def test_special_column_names_work_with_native_sql(self, tmp_path: Path) -> None:
        """带空格和点号的 Column.name 能正确生成并执行 SQL"""
        db_file = tmp_path / 'quoted_columns.duckdb'
        db = Storage(file_path=str(db_file), engine='duckdb')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Student(Base):
            __tablename__ = 'students'
            id = Column(int, primary_key=True)
            student_no = Column(str, name='Student No.')
            profile_name = Column(str, name='Profile.Name', nullable=True)

        session = Session(db)
        session.execute(insert(Student).values(student_no='S-002', profile_name='beta'))
        session.execute(insert(Student).values(student_no='S-001', profile_name='alpha'))
        session.commit()

        result = session.execute(
            select(Student)
            .where(Student.profile_name == 'alpha')
            .order_by('Student No.')
        ).first()

        assert result is not None
        assert result.student_no == 'S-001'
        assert result.profile_name == 'alpha'

        ordered = session.execute(select(Student).order_by('Student No.')).all()
        assert [student.student_no for student in ordered] == ['S-001', 'S-002']

        session.close()
        db.close()
