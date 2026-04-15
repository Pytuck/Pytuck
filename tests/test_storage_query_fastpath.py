"""
懒加载写路径测试

验证 pytuck 引擎在 lazy 模式下，写路径仍能正确处理磁盘中的记录。
"""

from pathlib import Path
from typing import Type

import pytest

from pytuck import Storage, declarative_base, Session, Column
from pytuck import PureBaseModel, insert, select
from pytuck.common.options import PytuckBackendOptions
from pytuck.common.exceptions import RecordNotFoundError


# ---------- 现有测试 ----------


def test_select_pk_fastpath(temp_dir: Path) -> None:
    """测试通过 Select 按主键查询能返回单条记录（为后续 fastpath 实现预期行为）"""
    db_path = temp_dir / 'fastpath.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck', backend_options=PytuckBackendOptions())
    Base: Type[PureBaseModel] = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str)

    session = Session(db)
    session.execute(insert(User).values(name='Alice'))
    session.execute(insert(User).values(name='Bob'))
    session.commit()
    db.flush()
    db.close()

    # 以默认 reopen 语义打开 backend
    backend = db.backend.__class__(str(db_path), PytuckBackendOptions())
    tables = backend.load()
    table = tables['users']

    # 通过 Table.get 查询主键 1
    record = table.get(1)
    assert record['name'] == 'Alice'

    # 也使用查询 API
    db2 = Storage(file_path=str(db_path), engine='pytuck', backend_options=PytuckBackendOptions())
    Base2: Type[PureBaseModel] = declarative_base(db2)
    session2 = Session(db2)
    stmt = select(User).where(User.id == 1)

    # monkeypatch db2.select 以计数，确保走了 Storage.select fast-path
    call_count = {'select': 0}
    orig_select = db2.select
    def counted_select(table, pk):
        call_count['select'] += 1
        return orig_select(table, pk)
    db2.select = counted_select

    res = session2.execute(stmt)
    rows = res.all()
    assert len(rows) == 1
    # 确认 fast-path 被调用一次
    assert call_count['select'] == 1
    # query API 返回模型实例，检查属性
    assert getattr(rows[0], 'name') == 'Alice'

    db2.close()


def test_reopen_and_select_returns_item(temp_dir: Path) -> None:
    """reopen 一个已 flush 的 pytuck 文件后，能正确 select 到记录（fastpath reopen 主路径）"""
    db_path = temp_dir / 'wal_init.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck', backend_options=PytuckBackendOptions())
    Base: Type[PureBaseModel] = declarative_base(db)

    class Item(Base):
        __tablename__ = 'items'
        id = Column(int, primary_key=True)
        name = Column(str)

    session = Session(db)
    session.execute(insert(Item).values(name='one'))
    session.commit()
    db.flush()
    db.close()

    # reopen 已存在文件并按默认主路径打开
    db2 = Storage(file_path=str(db_path), engine='pytuck', backend_options=PytuckBackendOptions())
    Base2: Type[PureBaseModel] = declarative_base(db2)
    session2 = Session(db2)
    res = session2.execute(select(Item).where(Item.id == 1)).all()
    assert len(res) == 1
    assert getattr(res[0], 'name') == 'one'
    db2.close()


# ---------- 新增失败测试（验证异常不会被吞） ----------


def test_select_fastpath_propagates_non_recordnotfound_exceptions(temp_dir: Path) -> None:
    """如果 storage.select 抛出非 RecordNotFoundError（例如 RuntimeError），
    session.execute(select(...)).all() 不应静默返回空列表，而应把异常向上传播。
    """
    db_path = temp_dir / 'fastpath_error.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck')
    Base: Type[PureBaseModel] = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str)

    session = Session(db)
    session.execute(insert(User).values(id=1, name='Alice'))
    session.commit()
    db.flush()

    # monkeypatch storage.select 在被按主键 fast-path 调用时抛出 RuntimeError
    orig_select = db.select
    def fake_select(table, pk):
        raise RuntimeError('boom')
    db.select = fake_select

    with pytest.raises(RuntimeError):
        session.execute(select(User).where(User.id == 1)).all()

    # 恢复并关闭
    db.select = orig_select
    db.close()
