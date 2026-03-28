"""
JSONL 后端专项测试

覆盖 JSONL 引擎的关键 ZIP 容器与回读路径：
- `_metadata.json` + 每表 `.jsonl` 的归档结构
- `probe()` / `get_metadata()` 探测
- 多表与特殊类型 round-trip
- 删除文件
"""

import json
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Type

from pytuck import Column, PureBaseModel, Session, Storage, declarative_base, insert, select
from pytuck.backends import get_database_info, is_valid_pytuck_database
from pytuck.backends.backend_jsonl import JSONLBackend
from pytuck.common.options import JsonlBackendOptions


class TestJSONLBackendFormat:
    """测试 JSONL ZIP 文件格式与元数据"""

    def test_zip_archive_contains_metadata_and_table_jsonl_files(self, tmp_path: Path) -> None:
        """JSONL 引擎应保存为 ZIP 容器，包含 metadata 和每表 JSONL 文件"""
        db_file = tmp_path / 'format.zip'
        db = Storage(file_path=str(db_file), engine='jsonl')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        class Post(Base):
            __tablename__ = 'posts'
            id = Column(int, primary_key=True)
            title = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.execute(insert(Post).values(title='Hello JSONL'))
        session.commit()
        session.close()
        db.close()

        with zipfile.ZipFile(str(db_file), 'r') as zf:
            assert set(zf.namelist()) == {'_metadata.json', 'users.jsonl', 'posts.jsonl'}

            metadata = json.loads(zf.read('_metadata.json').decode('utf-8'))
            assert metadata['engine'] == 'jsonl'
            assert metadata['table_count'] == 2
            assert set(metadata['tables']) == {'users', 'posts'}

            user_records = [
                json.loads(line)
                for line in zf.read('users.jsonl').decode('utf-8').splitlines()
                if line.strip()
            ]
            post_records = [
                json.loads(line)
                for line in zf.read('posts.jsonl').decode('utf-8').splitlines()
                if line.strip()
            ]

        assert len(user_records) == 1
        assert user_records[0]['name'] == 'Alice'
        assert len(post_records) == 1
        assert post_records[0]['title'] == 'Hello JSONL'

    def test_probe_and_get_metadata(self, tmp_path: Path) -> None:
        """probe 与 get_metadata 可从 ZIP 中的 metadata 识别 JSONL 文件"""
        db_file = tmp_path / 'metadata.zip'
        db = Storage(file_path=str(db_file), engine='jsonl')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.commit()
        session.close()
        db.close()

        matched, info = JSONLBackend.probe(db_file)
        assert matched is True
        assert info is not None
        assert info['engine'] == 'jsonl'
        assert info['table_count'] == 1
        assert info['confidence'] == 'high'

        valid, engine_name = is_valid_pytuck_database(db_file)
        assert valid is True
        assert engine_name == 'jsonl'

        database_info = get_database_info(db_file)
        assert database_info is not None
        assert database_info['engine'] == 'jsonl'
        assert database_info['table_count'] == 1

        backend = JSONLBackend(str(db_file), JsonlBackendOptions())
        metadata = backend.get_metadata()
        assert metadata['engine'] == 'jsonl'
        assert metadata['table_count'] == 1
        assert metadata['version'] == 1
        assert metadata['json_impl'] == 'json'

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        """delete 会移除 JSONL ZIP 数据文件"""
        db_file = tmp_path / 'delete.zip'
        backend = JSONLBackend(str(db_file), JsonlBackendOptions())

        db = Storage(file_path=str(db_file), engine='jsonl')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(User).values(name='Alice'))
        session.commit()
        session.close()
        db.close()

        assert db_file.exists()
        backend.delete()
        assert not db_file.exists()


class TestJSONLBackendRoundTrip:
    """测试 JSONL 特殊类型与多表回读"""

    def test_round_trip_special_types_and_multi_table(self, tmp_path: Path) -> None:
        """多表、bytes、datetime/date/timedelta、list/dict、NULL 可正常往返"""
        db_file = tmp_path / 'round_trip.zip'
        db1 = Storage(file_path=str(db_file), engine='jsonl')
        Base1: Type[PureBaseModel] = declarative_base(db1)

        class Event(Base1):
            __tablename__ = 'events'
            id = Column(int, primary_key=True)
            name = Column(str)
            payload = Column(bytes, nullable=True)
            created_at = Column(datetime)
            birthday = Column(date)
            duration = Column(timedelta)
            tags = Column(list)
            meta = Column(dict)
            note = Column(str, nullable=True)

        class User(Base1):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            active = Column(bool)

        created_at = datetime(2026, 3, 28, 12, 34, 56, tzinfo=timezone.utc)
        birthday = date(2024, 12, 1)
        duration = timedelta(days=2, seconds=15)

        session1 = Session(db1)
        session1.execute(
            insert(Event).values(
                name='Launch',
                payload=b'payload-bytes',
                created_at=created_at,
                birthday=birthday,
                duration=duration,
                tags=['alpha', 'beta'],
                meta={'source': 'jsonl', 'ok': True},
                note=None,
            )
        )
        session1.execute(insert(User).values(name='Alice', active=True))
        session1.commit()
        session1.close()
        db1.close()

        backend = JSONLBackend(str(db_file), JsonlBackendOptions())
        tables = backend.load()
        assert set(tables) == {'events', 'users'}
        event_record = tables['events'].data[1]
        assert event_record['payload'] == b'payload-bytes'
        assert event_record['created_at'] == created_at
        assert event_record['birthday'] == birthday
        assert event_record['duration'] == duration
        assert event_record['tags'] == ['alpha', 'beta']
        assert event_record['meta'] == {'source': 'jsonl', 'ok': True}
        assert event_record['note'] is None

        db2 = Storage(file_path=str(db_file), engine='jsonl')
        Base2: Type[PureBaseModel] = declarative_base(db2)

        class Event2(Base2):
            __tablename__ = 'events'
            id = Column(int, primary_key=True)
            name = Column(str)
            payload = Column(bytes, nullable=True)
            created_at = Column(datetime)
            birthday = Column(date)
            duration = Column(timedelta)
            tags = Column(list)
            meta = Column(dict)
            note = Column(str, nullable=True)

        class User2(Base2):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            active = Column(bool)

        session2 = Session(db2)
        loaded_event = session2.execute(select(Event2)).first()
        loaded_user = session2.execute(select(User2)).first()

        assert loaded_event is not None
        assert loaded_event.name == 'Launch'
        assert loaded_event.payload == b'payload-bytes'
        assert loaded_event.created_at == created_at
        assert loaded_event.birthday == birthday
        assert loaded_event.duration == duration
        assert loaded_event.tags == ['alpha', 'beta']
        assert loaded_event.meta == {'source': 'jsonl', 'ok': True}
        assert loaded_event.note is None

        assert loaded_user is not None
        assert loaded_user.name == 'Alice'
        assert loaded_user.active is True

        session2.close()
        db2.close()
