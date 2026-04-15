from pathlib import Path
from typing import Type

from pytuck import Column, PureBaseModel, Session, Storage
from pytuck import declarative_base, insert
from pytuck.backends.backend_pytuck import PytuckBackend
from pytuck.common.options import PytuckBackendOptions
from tests.benchmark.benchmark import EngineBenchmark


def test_pytuck_backend_options_exposes_only_current_fields() -> None:
    from dataclasses import fields

    assert set(f.name for f in fields(PytuckBackendOptions)) == {'encryption', 'password'}


def test_storage_no_longer_exposes_legacy_wal_hooks() -> None:
    from pytuck.core.storage import Storage

    assert not hasattr(Storage, '_init_wal_mode')
    assert not hasattr(Storage, '_get_pytuck_backend')
    assert not hasattr(Storage, '_write_wal')


def test_pytuck_backend_probe_reports_format_v7_after_flush(tmp_path: Path) -> None:
    db_path = tmp_path / 'contract.pytuck'
    db = Storage(file_path=str(db_path), engine='pytuck')
    Base: Type[PureBaseModel] = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str, index=True)

    session = Session(db)
    session.execute(insert(User).values(name='Alice'))
    session.commit()
    db.flush()
    db.close()

    matched, info = PytuckBackend.probe(db_path)
    assert matched is True
    assert info is not None
    assert info['format_version'] == 'PTK7'


def test_benchmark_reports_reopen_metrics_for_pytuck(tmp_path: Path) -> None:
    benchmark = EngineBenchmark('pytuck', str(tmp_path), extended_tests=True)
    result = benchmark.run(50)

    assert 'reopen' in result
    assert 'reopen_first_query' in result
    assert 'pk_query' in result
    assert 'lazy_load' not in result


def test_default_backend_options_returns_pytuck_backend_options() -> None:
    opts = PytuckBackendOptions()
    assert getattr(opts, 'encryption', None) is None
    assert getattr(opts, 'password', None) is None
