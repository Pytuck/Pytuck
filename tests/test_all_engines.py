"""
Pytuck - 所有存储引擎综合测试

测试所有8种存储引擎的功能：
- pytuck: Pytuck 单文件引擎（默认）
- json: JSON引擎
- jsonl: JSONL引擎（ZIP压缩）
- csv: CSV引擎（ZIP压缩）
- sqlite: SQLite引擎
- duckdb: DuckDB引擎
- excel: Excel引擎（需要 openpyxl）
- xml: XML引擎（需要 lxml）
"""

import sys
import tempfile
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Type

import pytest

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pytuck import Storage, declarative_base, Session, Column, PureBaseModel
from pytuck import select, insert, update, delete
from pytuck.backends import BackendRegistry
from pytuck.common.options import SqliteBackendOptions


# 所有引擎配置：(引擎名称, 文件扩展名)
ALL_ENGINES = [
    ('pytuck', 'pytuck'),
    ('json', 'json'),
    ('jsonl', 'zip'),
    ('csv', 'zip'),
    ('sqlite', 'sqlite'),
    ('duckdb', 'duckdb'),
    ('excel', 'xlsx'),
    ('xml', 'xml'),
]


def is_engine_available(engine_name: str) -> bool:
    """检查引擎是否可用"""
    backend_class = BackendRegistry.get(engine_name)
    return backend_class is not None and backend_class.is_available()


def get_skip_reason(engine_name: str) -> str:
    """获取跳过引擎的原因"""
    backend_class = BackendRegistry.get(engine_name)
    if backend_class and backend_class.REQUIRED_DEPENDENCIES:
        deps = ', '.join(backend_class.REQUIRED_DEPENDENCIES)
        return f"需要安装依赖: {deps}"
    return f"引擎 '{engine_name}' 不可用"


@pytest.fixture
def temp_db_path(tmp_path: Path):
    """提供临时数据库文件路径的工厂 fixture"""
    def _make_path(engine_name: str, file_ext: str) -> Path:
        return tmp_path / f'test_{engine_name}.{file_ext}'
    return _make_path


class TestAllEngines:
    """所有存储引擎的综合测试"""

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_engine_crud_operations(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试引擎的 CRUD 操作

        Args:
            engine_name: 引擎名称
            file_ext: 文件扩展名
            tmp_path: pytest 提供的临时目录
        """
        # 检查引擎是否可用
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_{engine_name}.{file_ext}'

        # 1. 创建数据库
        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class Student(Base):
            __tablename__ = 'students'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=False, index=True)
            age = Column(int)
            email = Column(str, nullable=True)
            active = Column(bool)
            avatar = Column(bytes, nullable=True)

        session = Session(db)

        # 2. 插入测试数据
        test_data = [
            {'name': 'Alice', 'age': 20, 'email': 'alice@example.com', 'active': True, 'avatar': b'avatar_alice'},
            {'name': 'Bob', 'age': 22, 'email': 'bob@example.com', 'active': False, 'avatar': b'avatar_bob'},
            {'name': 'Charlie', 'age': 19, 'email': None, 'active': True, 'avatar': None},
            {'name': 'David', 'age': 21, 'email': 'david@example.com', 'active': True, 'avatar': b'avatar_david'},
            {'name': 'Eve', 'age': 23, 'email': 'eve@example.com', 'active': False, 'avatar': b'avatar_eve'},
        ]

        for data in test_data:
            stmt = insert(Student).values(**data)
            session.execute(stmt)
        session.commit()

        # 3. 查询测试
        # 按 ID 查询
        stmt = select(Student).where(Student.id == 1)
        alice = session.execute(stmt).first()
        assert alice is not None
        assert alice.name == 'Alice'
        assert alice.age == 20
        assert alice.active is True
        assert alice.avatar == b'avatar_alice'

        # 索引查询
        stmt = select(Student).filter_by(name='Bob')
        bob = session.execute(stmt).first()
        assert bob is not None
        assert bob.email == 'bob@example.com'
        assert bob.active is False

        # 条件查询
        stmt = select(Student).filter_by(active=True)
        active_students = session.execute(stmt).all()
        assert len(active_students) == 3  # Alice, Charlie, David

        # 排序查询
        stmt = select(Student).order_by('age')
        sorted_students = session.execute(stmt).all()
        assert sorted_students[0].name == 'Charlie'  # 最年轻
        assert sorted_students[-1].name == 'Eve'  # 最年长

        # 4. 更新测试
        stmt = update(Student).where(Student.id == 1).values(age=21, email='alice.new@example.com')
        session.execute(stmt)
        session.commit()

        # 验证更新
        stmt = select(Student).where(Student.id == 1)
        alice_updated = session.execute(stmt).first()
        assert alice_updated.age == 21
        assert alice_updated.email == 'alice.new@example.com'

        # 5. 删除测试
        stmt = delete(Student).where(Student.name == 'Charlie')
        session.execute(stmt)
        session.commit()

        # 验证删除
        stmt = select(Student)
        remaining = session.execute(stmt).all()
        assert len(remaining) == 4

        # 6. 持久化测试
        session.close()
        db.close()

        # 验证文件已创建
        assert db_file.exists()

        # 7. 重新加载测试
        db2 = Storage(file_path=str(db_file), engine=engine_name)
        Base2: Type[PureBaseModel] = declarative_base(db2)

        class Student2(Base2):
            __tablename__ = 'students'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=False, index=True)
            age = Column(int)
            email = Column(str, nullable=True)
            active = Column(bool)
            avatar = Column(bytes, nullable=True)

        session2 = Session(db2)

        # 验证数据
        stmt = select(Student2)
        all_students = session2.execute(stmt).all()
        assert len(all_students) == 4

        # 验证具体数据
        stmt = select(Student2).where(Student2.id == 1)
        alice2 = session2.execute(stmt).first()
        assert alice2.age == 21
        assert alice2.email == 'alice.new@example.com'
        assert alice2.active is True
        assert alice2.avatar == b'avatar_alice'

        # 验证 bytes 类型
        stmt = select(Student2).where(Student2.id == 2)
        bob2 = session2.execute(stmt).first()
        assert bob2.avatar == b'avatar_bob'
        assert bob2.active is False

        # 索引查询验证
        stmt = select(Student2).filter_by(name='David')
        david = session2.execute(stmt).first()
        assert david.name == 'David'
        assert david.age == 21

        session2.close()
        db2.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_engine_null_handling(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试引擎的 NULL 值处理

        Args:
            engine_name: 引擎名称
            file_ext: 文件扩展名
            tmp_path: pytest 提供的临时目录
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_null_{engine_name}.{file_ext}'

        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class NullTest(Base):
            __tablename__ = 'null_test'
            id = Column(int, primary_key=True)
            str_field = Column(str, nullable=True)
            int_field = Column(int, nullable=True)
            bytes_field = Column(bytes, nullable=True)

        session = Session(db)

        # 插入包含 NULL 的数据
        session.execute(insert(NullTest).values(str_field='test', int_field=1, bytes_field=b'data'))
        session.execute(insert(NullTest).values(str_field=None, int_field=None, bytes_field=None))
        session.execute(insert(NullTest).values(str_field='', int_field=0, bytes_field=b''))
        session.commit()

        # 查询 NULL 值
        stmt = select(NullTest).filter_by(str_field=None)
        null_records = session.execute(stmt).all()
        assert len(null_records) == 1
        assert null_records[0].int_field is None
        assert null_records[0].bytes_field is None

        # 查询空字符串（不是 NULL）
        stmt = select(NullTest).where(NullTest.str_field == '')
        empty_records = session.execute(stmt).all()
        assert len(empty_records) == 1
        assert empty_records[0].int_field == 0
        assert empty_records[0].bytes_field == b''

        session.close()
        db.close()

    def test_excel_round_trip_coalesces_empty_values(self, tmp_path: Path) -> None:
        """Excel 引擎会将 None、空字符串和空 bytes 合并为空单元格语义。"""
        if not is_engine_available('excel'):
            pytest.skip(get_skip_reason('excel'))

        db_file = tmp_path / 'test_null_round_trip.xlsx'

        db = Storage(file_path=str(db_file), engine='excel')
        Base: Type[PureBaseModel] = declarative_base(db)

        class NullTest(Base):
            __tablename__ = 'null_test'
            id = Column(int, primary_key=True)
            str_field = Column(str, nullable=True)
            int_field = Column(int, nullable=True)
            bytes_field = Column(bytes, nullable=True)

        session = Session(db)
        session.execute(insert(NullTest).values(str_field='test', int_field=1, bytes_field=b'data'))
        session.execute(insert(NullTest).values(str_field=None, int_field=None, bytes_field=None))
        session.execute(insert(NullTest).values(str_field='', int_field=0, bytes_field=b''))
        session.commit()
        db.flush()
        session.close()
        db.close()

        db_reloaded = Storage(file_path=str(db_file), engine='excel')
        ReloadedBase: Type[PureBaseModel] = declarative_base(db_reloaded)

        class ReloadedNullTest(ReloadedBase):
            __tablename__ = 'null_test'
            id = Column(int, primary_key=True)
            str_field = Column(str, nullable=True)
            int_field = Column(int, nullable=True)
            bytes_field = Column(bytes, nullable=True)

        reloaded_session = Session(db_reloaded)
        reloaded_records = reloaded_session.execute(select(ReloadedNullTest).order_by('id')).all()

        assert [record.str_field for record in reloaded_records] == ['test', None, None]
        assert [record.int_field for record in reloaded_records] == [1, None, 0]
        assert [record.bytes_field for record in reloaded_records] == [b'data', None, None]

        reloaded_session.close()
        db_reloaded.close()

    def test_excel_external_headers_are_normalized_to_strings(self, tmp_path: Path) -> None:
        """外部 Excel 的非字符串表头应规范化为字符串，避免内部键类型不一致。"""
        if not is_engine_available('excel'):
            pytest.skip(get_skip_reason('excel'))

        import openpyxl

        db_file = tmp_path / 'external_headers.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'users'
        ws.append([123, 'name'])
        ws.append(['oops', 'Alice'])
        wb.save(str(db_file))
        wb.close()

        db = Storage(file_path=str(db_file), engine='excel')
        table = db.get_table('users')

        assert table is not None
        assert '123' in table.columns
        assert 123 not in table.columns
        assert table.data[1]['123'] == 'oops'
        db.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_engine_index_query(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试引擎的索引查询性能

        Args:
            engine_name: 引擎名称
            file_ext: 文件扩展名
            tmp_path: pytest 提供的临时目录
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_index_{engine_name}.{file_ext}'

        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class IndexTest(Base):
            __tablename__ = 'index_test'
            id = Column(int, primary_key=True)
            indexed_name = Column(str, index=True)
            non_indexed_value = Column(str)

        session = Session(db)

        # 插入测试数据
        for i in range(100):
            session.execute(insert(IndexTest).values(
                indexed_name=f'name_{i}',
                non_indexed_value=f'value_{i}'
            ))
        session.commit()

        # 索引查询
        stmt = select(IndexTest).filter_by(indexed_name='name_50')
        result = session.execute(stmt).first()
        assert result is not None
        assert result.indexed_name == 'name_50'
        assert result.non_indexed_value == 'value_50'

        # 非索引查询
        stmt = select(IndexTest).where(IndexTest.non_indexed_value == 'value_75')
        result = session.execute(stmt).first()
        assert result is not None
        assert result.indexed_name == 'name_75'

        session.close()
        db.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_engine_new_types_persistence(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试引擎的新类型（datetime, date, timedelta, list, dict）持久化

        Args:
            engine_name: 引擎名称
            file_ext: 文件扩展名
            tmp_path: pytest 提供的临时目录
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_newtypes_{engine_name}.{file_ext}'

        # 1. 创建数据库
        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class Task(Base):
            __tablename__ = 'tasks'
            id = Column(int, primary_key=True)
            title = Column(str)
            created_at = Column(datetime, nullable=True)
            due_date = Column(date, nullable=True)
            duration = Column(timedelta, nullable=True)
            tags = Column(list, nullable=True)
            options = Column(dict, nullable=True)

        session = Session(db)

        # 2. 准备测试数据
        now = datetime(2024, 1, 15, 10, 30, 45, 123456)
        today = date(2024, 1, 20)
        duration = timedelta(hours=2, minutes=30, seconds=15)
        tags = ['important', 'urgent', 'review']
        options = {'priority': 1, 'notify': True, 'assignees': ['Alice', 'Bob']}

        # 插入数据
        stmt = insert(Task).values(
            title='Test Task',
            created_at=now,
            due_date=today,
            duration=duration,
            tags=tags,
            options=options
        )
        session.execute(stmt)

        # 插入带 NULL 值的数据
        stmt = insert(Task).values(
            title='Empty Task',
            created_at=None,
            due_date=None,
            duration=None,
            tags=None,
            options=None
        )
        session.execute(stmt)
        session.commit()

        # 3. 持久化
        session.close()
        db.close()

        # 验证文件已创建
        assert db_file.exists()

        # 4. 重新加载测试
        db2 = Storage(file_path=str(db_file), engine=engine_name)
        Base2: Type[PureBaseModel] = declarative_base(db2)

        class Task2(Base2):
            __tablename__ = 'tasks'
            id = Column(int, primary_key=True)
            title = Column(str)
            created_at = Column(datetime, nullable=True)
            due_date = Column(date, nullable=True)
            duration = Column(timedelta, nullable=True)
            tags = Column(list, nullable=True)
            options = Column(dict, nullable=True)

        session2 = Session(db2)

        # 5. 验证加载的数据
        stmt = select(Task2).where(Task2.id == 1)
        task1 = session2.execute(stmt).first()

        assert task1 is not None
        assert task1.title == 'Test Task'

        # 验证 datetime
        assert task1.created_at is not None
        assert isinstance(task1.created_at, datetime)
        assert task1.created_at.year == 2024
        assert task1.created_at.month == 1
        assert task1.created_at.day == 15
        assert task1.created_at.hour == 10
        assert task1.created_at.minute == 30

        # 验证 date
        assert task1.due_date is not None
        assert isinstance(task1.due_date, date)
        assert task1.due_date == today

        # 验证 timedelta
        assert task1.duration is not None
        assert isinstance(task1.duration, timedelta)
        assert task1.duration.total_seconds() == duration.total_seconds()

        # 验证 list
        assert task1.tags is not None
        assert isinstance(task1.tags, list)
        assert task1.tags == tags

        # 验证 dict
        assert task1.options is not None
        assert isinstance(task1.options, dict)
        assert task1.options == options

        # 6. 验证 NULL 值
        stmt = select(Task2).where(Task2.id == 2)
        task2 = session2.execute(stmt).first()

        assert task2 is not None
        assert task2.title == 'Empty Task'
        assert task2.created_at is None
        assert task2.due_date is None
        assert task2.duration is None
        assert task2.tags is None
        assert task2.options is None

        session2.close()
        db2.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_engine_supported_type_round_trip(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试每个引擎对全部内置支持类型的 round-trip 保真。

        这里集中覆盖：
        int / str / float / bool / bytes / datetime / date /
        timedelta / list / dict。
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_supported_types_{engine_name}.{file_ext}'

        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class SupportedTypes(Base):
            __tablename__ = 'supported_types'
            id = Column(int, primary_key=True)
            int_field = Column(int)
            str_field = Column(str)
            float_field = Column(float)
            bool_field = Column(bool)
            bytes_field = Column(bytes)
            datetime_field = Column(datetime)
            date_field = Column(date)
            timedelta_field = Column(timedelta)
            list_field = Column(list)
            dict_field = Column(dict)

        aware_datetime = datetime(
            2024, 2, 29, 23, 45, 12, 654321,
            tzinfo=timezone(timedelta(hours=8, minutes=30))
        )
        exact_date = date(2024, 2, 29)
        exact_duration = timedelta(days=2, hours=3, minutes=4, seconds=5, microseconds=678901)
        binary_payload = bytes([0, 1, 2, 127, 128, 255]) + '你好'.encode('utf-8')
        list_payload = ['alpha', 1, True, None, {'nested': ['x', 2]}]
        dict_payload = {
            'name': '类型覆盖',
            'enabled': False,
            'threshold': 0.125,
            'items': ['a', {'deep': [1, 2, 3]}],
        }

        session = Session(db)
        session.execute(insert(SupportedTypes).values(
            int_field=-123456789,
            str_field='Hello, 类型 round-trip',
            float_field=-1234.56789,
            bool_field=False,
            bytes_field=binary_payload,
            datetime_field=aware_datetime,
            date_field=exact_date,
            timedelta_field=exact_duration,
            list_field=list_payload,
            dict_field=dict_payload,
        ))
        session.commit()
        db.flush()
        session.close()
        db.close()

        db_reloaded = Storage(file_path=str(db_file), engine=engine_name)
        ReloadedBase: Type[PureBaseModel] = declarative_base(db_reloaded)

        class ReloadedSupportedTypes(ReloadedBase):
            __tablename__ = 'supported_types'
            id = Column(int, primary_key=True)
            int_field = Column(int)
            str_field = Column(str)
            float_field = Column(float)
            bool_field = Column(bool)
            bytes_field = Column(bytes)
            datetime_field = Column(datetime)
            date_field = Column(date)
            timedelta_field = Column(timedelta)
            list_field = Column(list)
            dict_field = Column(dict)

        reloaded_session = Session(db_reloaded)
        record = reloaded_session.get(ReloadedSupportedTypes, 1)

        assert record is not None
        assert record.int_field == -123456789
        assert record.str_field == 'Hello, 类型 round-trip'
        assert record.float_field == pytest.approx(-1234.56789)
        assert record.bool_field is False
        assert record.bytes_field == binary_payload
        assert record.datetime_field == aware_datetime
        assert record.date_field == exact_date
        assert record.timedelta_field == exact_duration
        assert record.list_field == list_payload
        assert record.dict_field == dict_payload

        reloaded_session.close()
        db_reloaded.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_engine_column_name_mapping(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试引擎的 Column.name 与属性名映射

        验证当 Column.name 与属性名不同时，写入和读取都能正确工作。

        Args:
            engine_name: 引擎名称
            file_ext: 文件扩展名
            tmp_path: pytest 提供的临时目录
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_column_name_{engine_name}.{file_ext}'

        # 1. 创建数据库并写入
        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class Product(Base):
            __tablename__ = 'products'
            # 使用不带空格的 Column.name，避免 SQLite 语法问题
            id = Column(int, primary_key=True, name='product_id')
            product_name = Column(str, name='product_name_col')
            unit_price = Column(float, name='unit_price_col')
            in_stock = Column(bool, name='in_stock_col')

        session = Session(db)

        # 插入数据
        stmt = insert(Product).values(
            id=1,
            product_name='Widget',
            unit_price=19.99,
            in_stock=True
        )
        session.execute(stmt)
        stmt = insert(Product).values(
            id=2,
            product_name='Gadget',
            unit_price=29.99,
            in_stock=False
        )
        session.execute(stmt)
        session.commit()

        # 2. 验证存储层使用 Column.name
        records = db.query('products', [])
        assert len(records) == 2
        assert 'product_id' in records[0]
        assert 'product_name_col' in records[0]
        assert 'unit_price_col' in records[0]
        assert 'in_stock_col' in records[0]

        # 3. 验证读取时映射回属性名
        product = session.get(Product, 1)
        assert product is not None
        assert product.id == 1
        assert product.product_name == 'Widget'
        assert product.unit_price == 19.99
        assert product.in_stock is True

        # 4. 验证更新
        stmt = update(Product).where(Product.id == 1).values(unit_price=24.99)
        session.execute(stmt)
        session.commit()

        # 刷新对象以获取最新数据（update statement 不会自动刷新 identity map）
        session.refresh(product)
        assert product.unit_price == 24.99

        # 5. 验证条件查询
        stmt = select(Product).where(Product.in_stock == False)
        out_of_stock = session.execute(stmt).all()
        assert len(out_of_stock) == 1
        assert out_of_stock[0].product_name == 'Gadget'

        # 6. 持久化并重载
        session.close()
        db.close()

        # 验证文件已创建
        assert db_file.exists()

        # 7. 重新加载验证
        db2 = Storage(file_path=str(db_file), engine=engine_name)
        Base2: Type[PureBaseModel] = declarative_base(db2)

        class Product2(Base2):
            __tablename__ = 'products'
            id = Column(int, primary_key=True, name='product_id')
            product_name = Column(str, name='product_name_col')
            unit_price = Column(float, name='unit_price_col')
            in_stock = Column(bool, name='in_stock_col')

        session2 = Session(db2)

        # 验证重载后数据正确
        stmt = select(Product2)
        products = session2.execute(stmt).all()
        assert len(products) == 2

        # 使用 Session.get()
        product = session2.get(Product2, 1)
        assert product is not None
        assert product.product_name == 'Widget'
        assert product.unit_price == 24.99
        assert product.in_stock is True

        product2 = session2.get(Product2, 2)
        assert product2 is not None
        assert product2.product_name == 'Gadget'
        assert product2.in_stock is False

        session2.close()
        db2.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_engine_column_name_with_chinese(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试引擎的中文 Column.name 支持

        Args:
            engine_name: 引擎名称
            file_ext: 文件扩展名
            tmp_path: pytest 提供的临时目录
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_chinese_col_{engine_name}.{file_ext}'

        if engine_name == 'sqlite':
            db = Storage(
                file_path=str(db_file),
                engine=engine_name,
                backend_options=SqliteBackendOptions(use_native_sql=False)
            )
        else:
            db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True, name='编号')
            user_name = Column(str, name='用户名')
            email = Column(str, name='电子邮箱')

        session = Session(db)

        # 插入
        stmt = insert(User).values(id=1, user_name='张三', email='zhangsan@example.com')
        session.execute(stmt)
        session.commit()

        # 验证存储层
        records = db.query('users', [])
        assert '编号' in records[0]
        assert '用户名' in records[0]
        assert '电子邮箱' in records[0]
        assert records[0]['用户名'] == '张三'

        # 验证读取
        user = session.get(User, 1)
        assert user is not None
        assert user.user_name == '张三'
        assert user.email == 'zhangsan@example.com'

        # 持久化并重载
        session.close()
        db.close()

        db2 = Storage(file_path=str(db_file), engine=engine_name)
        Base2: Type[PureBaseModel] = declarative_base(db2)

        class User2(Base2):
            __tablename__ = 'users'
            id = Column(int, primary_key=True, name='编号')
            user_name = Column(str, name='用户名')
            email = Column(str, name='电子邮箱')

        session2 = Session(db2)

        user = session2.get(User2, 1)
        assert user is not None
        assert user.user_name == '张三'

        session2.close()
        db2.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_persistence_data_integrity(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试持久化数据完整性

        验证各引擎在保存一定数量记录后：
        1. flush 后文件大小合理（非空且不过小）
        2. close → reopen 后记录数完整
        3. 数据内容准确
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_integrity_{engine_name}.{file_ext}'
        record_count = 500

        # 1. 创建数据库并批量插入
        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=False, index=True)
            value = Column(float)
            active = Column(bool)

        session = Session(db)
        for i in range(record_count):
            stmt = insert(Item).values(
                name=f'Item_{i}',
                value=float(i) * 1.5,
                active=(i % 2 == 0)
            )
            session.execute(stmt)
        session.commit()

        # 2. flush 后验证文件大小合理
        db.flush()
        assert db_file.exists(), f"{engine_name}: 文件应该存在"

        file_size = db_file.stat().st_size
        # 500 条记录的文件不应小于 1KB（排除 DuckDB WAL 等异常）
        assert file_size > 1024, (
            f"{engine_name}: flush 后文件仅 {file_size} bytes，"
            f"500 条记录不应如此小，可能数据未正确持久化"
        )

        # 3. close → reopen → 验证记录数
        session.close()
        db.close()

        db2 = Storage(file_path=str(db_file), engine=engine_name)
        Base2: Type[PureBaseModel] = declarative_base(db2)

        class Item2(Base2):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=False, index=True)
            value = Column(float)
            active = Column(bool)

        session2 = Session(db2)

        stmt = select(Item2)
        all_items = session2.execute(stmt).all()
        assert len(all_items) == record_count, (
            f"{engine_name}: 期望 {record_count} 条记录，"
            f"实际 {len(all_items)} 条"
        )

        # 4. 验证首尾记录数据准确
        first = session2.execute(select(Item2).where(Item2.id == 1)).first()
        assert first is not None
        assert first.name == 'Item_0'
        assert first.value == 0.0
        assert first.active is True

        last = session2.execute(
            select(Item2).where(Item2.name == f'Item_{record_count - 1}')
        ).first()
        assert last is not None
        assert last.value == float(record_count - 1) * 1.5
        assert last.active == ((record_count - 1) % 2 == 0)

        # 5. 验证条件查询结果数量
        active_items = session2.execute(select(Item2).filter_by(active=True)).all()
        expected_active = (record_count + 1) // 2  # i % 2 == 0 的数量
        assert len(active_items) == expected_active, (
            f"{engine_name}: 期望 {expected_active} 条 active 记录，"
            f"实际 {len(active_items)} 条"
        )

        session2.close()
        db2.close()

    @pytest.mark.parametrize("engine_name,file_ext", ALL_ENGINES)
    def test_flush_then_reopen_without_close(self, engine_name: str, file_ext: str, tmp_path: Path) -> None:
        """
        测试 flush 后直接 reopen（不经过 close）的数据完整性

        验证 flush 已将数据写入文件，另一个 Storage 实例能正确读取。
        """
        if not is_engine_available(engine_name):
            pytest.skip(get_skip_reason(engine_name))

        db_file = tmp_path / f'test_flush_reopen_{engine_name}.{file_ext}'

        db = Storage(file_path=str(db_file), engine=engine_name)
        Base: Type[PureBaseModel] = declarative_base(db)

        class Record(Base):
            __tablename__ = 'records'
            id = Column(int, primary_key=True)
            data = Column(str)

        session = Session(db)
        for i in range(100):
            session.execute(insert(Record).values(data=f'data_{i}'))
        session.commit()
        db.flush()

        # 不 close，直接用新 Storage 读取文件
        # 注意：DuckDB native SQL 模式下，连接仍然持有锁，需要先 close
        if engine_name in ('duckdb', 'sqlite'):
            db.close()

        db2 = Storage(file_path=str(db_file), engine=engine_name)
        Base2: Type[PureBaseModel] = declarative_base(db2)

        class Record2(Base2):
            __tablename__ = 'records'
            id = Column(int, primary_key=True)
            data = Column(str)

        session2 = Session(db2)
        all_records = session2.execute(select(Record2)).all()
        assert len(all_records) == 100, (
            f"{engine_name}: flush 后应有 100 条记录，实际 {len(all_records)}"
        )

        session2.close()
        db2.close()
        if engine_name not in ('duckdb', 'sqlite'):
            db.close()


# 允许直接运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
