"""
边界值测试

测试方法：
- 边界值法：最小值、最大值、边界附近值
- 等价类法：有效等价类、无效等价类
"""

import math
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Type

import pytest

from pytuck import Storage, Session, Column, PureBaseModel, declarative_base
from pytuck import select, insert


class TestStringBoundaryValues:
    """字符串边界值"""

    def test_empty_string(self, tmp_path: Path) -> None:
        """空字符串"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(Item).values(id=1, name=''))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.name == ''

        session.close()
        db.close()

    def test_very_long_string(self, tmp_path: Path) -> None:
        """超长字符串（10000+ 字符）"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            content = Column(str)

        long_string = 'A' * 10000

        session = Session(db)
        session.execute(insert(Item).values(id=1, content=long_string))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.content == long_string
        assert len(item.content) == 10000

        session.close()
        db.close()

    def test_unicode_emoji(self, tmp_path: Path) -> None:
        """Unicode emoji 字符"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            text = Column(str)

        emoji_text = '😀🎉🚀💯🔥✨🌟💡🎯🏆'

        session = Session(db)
        session.execute(insert(Item).values(id=1, text=emoji_text))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.text == emoji_text

        session.close()
        db.close()

    def test_unicode_non_bmp(self, tmp_path: Path) -> None:
        """非 BMP Unicode 字符（如数学符号、古文字）"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            text = Column(str)

        # 数学双线字体、音乐符号、古埃及象形文字等
        non_bmp_text = '𝕳𝖊𝖑𝖑𝖔 𝄞𝄢 𓀀𓂋'

        session = Session(db)
        session.execute(insert(Item).values(id=1, text=non_bmp_text))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.text == non_bmp_text

        session.close()
        db.close()

    def test_control_characters(self, tmp_path: Path) -> None:
        """控制字符（\n, \t, \r）"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            text = Column(str)

        control_text = 'Line1\nLine2\tTab\rCarriage'

        session = Session(db)
        session.execute(insert(Item).values(id=1, text=control_text))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.text == control_text
        assert '\n' in item.text
        assert '\t' in item.text
        assert '\r' in item.text

        session.close()
        db.close()

    def test_mixed_unicode_ascii(self, tmp_path: Path) -> None:
        """混合 Unicode 和 ASCII"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            text = Column(str)

        mixed_text = 'Hello 你好 Привет مرحبا 🌍'

        session = Session(db)
        session.execute(insert(Item).values(id=1, text=mixed_text))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.text == mixed_text

        session.close()
        db.close()


class TestNumericBoundaryValues:
    """数值边界值"""

    def test_int_zero(self, tmp_path: Path) -> None:
        """整数零"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            value = Column(int)

        session = Session(db)
        session.execute(insert(Item).values(id=1, value=0))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.value == 0

        session.close()
        db.close()

    def test_int_large_value(self, tmp_path: Path) -> None:
        """大整数值"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            value = Column(int)

        large_int = 2**62  # 大整数

        session = Session(db)
        session.execute(insert(Item).values(id=1, value=large_int))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.value == large_int

        session.close()
        db.close()

    def test_int_negative(self, tmp_path: Path) -> None:
        """负整数"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            value = Column(int)

        session = Session(db)
        session.execute(insert(Item).values(id=1, value=-999999))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.value == -999999

        session.close()
        db.close()

    def test_float_zero(self, tmp_path: Path) -> None:
        """浮点零"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            value = Column(float)

        session = Session(db)
        session.execute(insert(Item).values(id=1, value=0.0))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.value == 0.0

        session.close()
        db.close()

    def test_float_very_small(self, tmp_path: Path) -> None:
        """极小浮点数"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            value = Column(float)

        tiny_float = 1e-300

        session = Session(db)
        session.execute(insert(Item).values(id=1, value=tiny_float))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.value == tiny_float

        session.close()
        db.close()

    def test_float_very_large(self, tmp_path: Path) -> None:
        """极大浮点数"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            value = Column(float)

        large_float = 1e300

        session = Session(db)
        session.execute(insert(Item).values(id=1, value=large_float))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.value == large_float

        session.close()
        db.close()

    def test_float_negative(self, tmp_path: Path) -> None:
        """负浮点数"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            value = Column(float)

        session = Session(db)
        session.execute(insert(Item).values(id=1, value=-123.456))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.value == -123.456

        session.close()
        db.close()


class TestCollectionBoundaryValues:
    """集合类型边界值"""

    def test_empty_list(self, tmp_path: Path) -> None:
        """空列表"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            tags = Column(list)

        session = Session(db)
        session.execute(insert(Item).values(id=1, tags=[]))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.tags == []

        session.close()
        db.close()

    def test_empty_dict(self, tmp_path: Path) -> None:
        """空字典"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            metadata = Column(dict)

        session = Session(db)
        session.execute(insert(Item).values(id=1, metadata={}))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.metadata == {}

        session.close()
        db.close()

    def test_nested_list(self, tmp_path: Path) -> None:
        """嵌套列表"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            matrix = Column(list)

        nested_list = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        session = Session(db)
        session.execute(insert(Item).values(id=1, matrix=nested_list))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.matrix == nested_list

        session.close()
        db.close()

    def test_deeply_nested_structure(self, tmp_path: Path) -> None:
        """深度嵌套结构"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            data = Column(dict)

        deep_structure = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': {
                            'value': 'deep'
                        }
                    }
                }
            }
        }

        session = Session(db)
        session.execute(insert(Item).values(id=1, data=deep_structure))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.data == deep_structure
        assert item.data['level1']['level2']['level3']['level4']['value'] == 'deep'

        session.close()
        db.close()

    def test_list_with_mixed_types(self, tmp_path: Path) -> None:
        """混合类型列表"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            data = Column(list)

        mixed_list = [1, 'two', 3.0, True, None, {'key': 'value'}, [1, 2, 3]]

        session = Session(db)
        session.execute(insert(Item).values(id=1, data=mixed_list))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.data == mixed_list

        session.close()
        db.close()


class TestDatetimeBoundaryValues:
    """日期时间边界值"""

    def test_datetime_now(self, tmp_path: Path) -> None:
        """当前时间"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            created_at = Column(datetime)

        now = datetime.now()

        session = Session(db)
        session.execute(insert(Item).values(id=1, created_at=now))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        # 由于序列化可能丢失微秒精度，比较到秒
        assert item.created_at.replace(microsecond=0) == now.replace(microsecond=0)

        session.close()
        db.close()

    def test_date_only(self, tmp_path: Path) -> None:
        """只有日期"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            birth_date = Column(date)

        today = date.today()

        session = Session(db)
        session.execute(insert(Item).values(id=1, birth_date=today))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.birth_date == today

        session.close()
        db.close()

    def test_timedelta(self, tmp_path: Path) -> None:
        """时间间隔"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            duration = Column(timedelta)

        delta = timedelta(days=5, hours=3, minutes=30, seconds=15)

        session = Session(db)
        session.execute(insert(Item).values(id=1, duration=delta))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.duration == delta

        session.close()
        db.close()


class TestBooleanBoundaryValues:
    """布尔值边界值"""

    def test_bool_true(self, tmp_path: Path) -> None:
        """布尔真"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            active = Column(bool)

        session = Session(db)
        session.execute(insert(Item).values(id=1, active=True))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.active is True

        session.close()
        db.close()

    def test_bool_false(self, tmp_path: Path) -> None:
        """布尔假"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            active = Column(bool)

        session = Session(db)
        session.execute(insert(Item).values(id=1, active=False))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.active is False

        session.close()
        db.close()


class TestBytesBoundaryValues:
    """字节类型边界值"""

    def test_empty_bytes(self, tmp_path: Path) -> None:
        """空字节"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            data = Column(bytes)

        session = Session(db)
        session.execute(insert(Item).values(id=1, data=b''))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.data == b''

        session.close()
        db.close()

    def test_binary_data(self, tmp_path: Path) -> None:
        """二进制数据"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            data = Column(bytes)

        binary_data = bytes(range(256))  # 所有可能的字节值

        session = Session(db)
        session.execute(insert(Item).values(id=1, data=binary_data))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.data == binary_data

        session.close()
        db.close()


class TestNullableBoundaryValues:
    """可空字段边界值"""

    def test_nullable_string_none(self, tmp_path: Path) -> None:
        """可空字符串设为 None"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=True)

        session = Session(db)
        session.execute(insert(Item).values(id=1, name=None))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.name is None

        session.close()
        db.close()

    def test_nullable_int_none(self, tmp_path: Path) -> None:
        """可空整数设为 None"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            count = Column(int, nullable=True)

        session = Session(db)
        session.execute(insert(Item).values(id=1, count=None))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.count is None

        session.close()
        db.close()

    def test_nullable_list_none(self, tmp_path: Path) -> None:
        """可空列表设为 None"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            tags = Column(list, nullable=True)

        session = Session(db)
        session.execute(insert(Item).values(id=1, tags=None))
        session.commit()

        item = session.get(Item, 1)
        assert item is not None
        assert item.tags is None

        session.close()
        db.close()


class TestMultipleRecordsBoundaryValues:
    """多记录边界值"""

    def test_single_record(self, tmp_path: Path) -> None:
        """单条记录"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)
        session.execute(insert(Item).values(id=1, name='only'))
        session.commit()

        result = session.execute(select(Item))
        items = result.all()
        assert len(items) == 1

        session.close()
        db.close()

    def test_many_records(self, tmp_path: Path) -> None:
        """大量记录（1000条）"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)

        # 插入 1000 条记录
        for i in range(1, 1001):
            session.execute(insert(Item).values(id=i, name=f'item_{i}'))
        session.commit()

        # 验证总数
        result = session.execute(select(Item))
        items = result.all()
        assert len(items) == 1000

        # 验证能正确获取特定记录
        item = session.get(Item, 500)
        assert item is not None
        assert item.name == 'item_500'

        session.close()
        db.close()

    def test_empty_table(self, tmp_path: Path) -> None:
        """空表查询"""
        db_file = tmp_path / 'test.pytuck'
        db = Storage(file_path=str(db_file), engine='pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            name = Column(str)

        session = Session(db)

        # 查询空表
        result = session.execute(select(Item))
        items = result.all()
        assert len(items) == 0

        # first() 应返回 None
        first_item = result.first()
        assert first_item is None

        session.close()
        db.close()
