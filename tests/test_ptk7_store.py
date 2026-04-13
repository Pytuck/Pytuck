from pathlib import Path
from typing import Any, List, Tuple, Type

import pytest

import pytuck.backends.ptk7_store as ptk7_store
from pytuck import Storage, Column, declarative_base, Session
from pytuck import insert, select
from pytuck.common.options import BinaryBackendOptions


def test_ptk7_reopen_restores_indexes(temp_dir: Path) -> None:
    """PTK7 reopen 应恢复索引元数据，使等值/排序查询在懒模式下可用"""
    db_path = temp_dir / 'ptk7_idx.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck', backend_options=BinaryBackendOptions())
    Base: Type = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str, index=True)
        age = Column(int)

    session = Session(db)
    session.execute(insert(User).values(name='Alice', age=20))
    session.execute(insert(User).values(name='Bob', age=25))
    session.execute(insert(User).values(name='Alice', age=30))
    session.commit()
    db.flush()
    db.close()

    # reopen backend (lazy)
    db2 = Storage(file_path=str(db_path), engine='pytuck')
    table = db2.tables['users']
    # table should be lazy loaded but indexes usable without full materialize
    assert table._lazy_loaded is True
    # equality lookup by name should find pks for 'Alice'
    idx_pks = table.indexes['name'].lookup('Alice')
    assert 1 in idx_pks or 3 in idx_pks
    # sorted order by age using storage.query should work (order_by uses sorted index if available)
    results = db2.query('users', [], order_by='age')
    ages = [r['age'] for r in results]
    assert ages == sorted(ages)


def test_ptk7_open_defers_index_decode_until_lookup(
    temp_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PTK7 打开时不应提前解码索引块，而是在真正使用索引时再解码"""
    db_path = temp_dir / 'ptk7_deferred_index_decode.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck', backend_options=BinaryBackendOptions())
    Base: Type = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str, index=True)
        age = Column(int, index='sorted')

    session = Session(db)
    session.execute(insert(User).values(name='Alice', age=20))
    session.execute(insert(User).values(name='Bob', age=25))
    session.execute(insert(User).values(name='Alice', age=30))
    session.commit()
    db.flush()
    db.close()

    decoded_columns: List[str] = []
    original_decode = ptk7_store.decode_sorted_pairs

    def tracked_decode(blob: bytes, column: Column) -> List[Tuple[Any, int]]:
        assert column.name is not None
        decoded_columns.append(column.name)
        return original_decode(blob, column)

    monkeypatch.setattr(ptk7_store, 'decode_sorted_pairs', tracked_decode)

    db2 = Storage(file_path=str(db_path), engine='pytuck')
    table = db2.tables['users']
    assert table._lazy_loaded is True
    assert decoded_columns == []

    row = db2.select('users', 1)
    assert row['name'] == 'Alice'
    assert decoded_columns == []

    assert table.indexes['name'].lookup('Alice') == {1, 3}
    assert decoded_columns == ['name']

    assert table.indexes['age'].supports_range_query() is True
    assert decoded_columns == ['name']

    Base2: Type = declarative_base(db2)

    class UserReloaded(Base2):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str, index=True)
        age = Column(int, index='sorted')

    session2 = Session(db2)
    users = session2.execute(select(UserReloaded).order_by('age')).all()
    assert [user.age for user in users] == [20, 25, 30]
    assert decoded_columns == ['name', 'age']
    session2.close()
    db2.close()


def test_ptk7_flush_does_not_reopen_written_file(
    temp_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PTK7 flush 写盘后不应立即 reopen 文件重建索引"""
    db_path = temp_dir / 'ptk7_flush_no_reopen.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck', backend_options=BinaryBackendOptions())
    Base: Type = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str, index=True)

    session = Session(db)
    session.execute(insert(User).values(name='Alice'))
    session.commit()

    original_open = ptk7_store.StorePTK7.open

    def fail_open(self: ptk7_store.StorePTK7) -> None:
        raise AssertionError('flush should not reopen PTK7 file')

    monkeypatch.setattr(ptk7_store.StorePTK7, 'open', fail_open)
    db.flush()
    monkeypatch.setattr(ptk7_store.StorePTK7, 'open', original_open)

    db.close()

    db2 = Storage(file_path=str(db_path), engine='pytuck')
    assert db2.select('users', 1)['name'] == 'Alice'
    db2.close()


def test_ptk7_reopen_then_flush_preserves_existing_index_entries(temp_dir: Path) -> None:
    """PTK7 reopen 后再写入并 flush，不应丢失旧索引项"""
    db_path = temp_dir / 'ptk7_reopen_preserve_index.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck', backend_options=BinaryBackendOptions())
    Base: Type = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str, index=True)

    session = Session(db)
    session.execute(insert(User).values(name='Alice'))
    session.execute(insert(User).values(name='Bob'))
    session.commit()
    db.flush()
    db.close()

    db2 = Storage(file_path=str(db_path), engine='pytuck')
    db2.insert('users', {'name': 'Charlie'})
    db2.flush()
    db2.close()

    db3 = Storage(file_path=str(db_path), engine='pytuck')
    table = db3.tables['users']
    assert table.indexes['name'].lookup('Alice') == {1}
    assert table.indexes['name'].lookup('Bob') == {2}
    assert table.indexes['name'].lookup('Charlie') == {3}
    db3.close()
