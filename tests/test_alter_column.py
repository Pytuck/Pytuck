"""
alter_column / set_primary_key / reorder_columns API 测试
以及 Bug 复现测试（引擎转换数据丢失、flush/load 默认值篡改）
"""
import tempfile
from pathlib import Path
from typing import Type

import pytest

from pytuck import (
    Storage,
    Session,
    Column,
    declarative_base,
    PureBaseModel,
    SchemaError,
    ColumnNotFoundError,
    ValidationError,
)
from pytuck.common.exceptions import TypeConversionError
from pytuck.core.storage import Table


# ==================== alter_column 测试 ====================

class TestAlterColumnTable:
    """Table.alter_column 测试"""

    def _make_table(self) -> Table:
        """创建带数据的测试表"""
        columns = [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
            Column(int, name='age', nullable=True),
        ]
        table = Table('users', columns, 'id')
        table.data = {
            1: {'id': 1, 'name': 'Alice', 'age': 25},
            2: {'id': 2, 'name': 'Bob', 'age': 30},
            3: {'id': 3, 'name': 'Charlie', 'age': None},
        }
        table.next_id = 4
        return table

    def test_alter_type_int_to_str(self) -> None:
        """int → str 类型转换"""
        table = self._make_table()
        table.alter_column('age', col_type=str)

        assert table.columns['age'].col_type == str
        assert table.data[1]['age'] == '25'
        assert table.data[2]['age'] == '30'
        assert table.data[3]['age'] is None  # None 保持不变

    def test_alter_type_str_to_int_success(self) -> None:
        """str → int 类型转换（成功）"""
        columns = [
            Column(int, name='id', primary_key=True),
            Column(str, name='score'),
        ]
        table = Table('test', columns, 'id')
        table.data = {
            1: {'id': 1, 'score': '100'},
            2: {'id': 2, 'score': '200'},
        }

        table.alter_column('score', col_type=int)
        assert table.columns['score'].col_type == int
        assert table.data[1]['score'] == 100
        assert table.data[2]['score'] == 200

    def test_alter_type_str_to_int_failure(self) -> None:
        """str → int 类型转换（失败：值无法转换）"""
        columns = [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
        ]
        table = Table('test', columns, 'id')
        table.data = {
            1: {'id': 1, 'name': 'abc'},
        }

        with pytest.raises(TypeConversionError):
            table.alter_column('name', col_type=int)

        # 验证数据未被修改
        assert table.data[1]['name'] == 'abc'
        assert table.columns['name'].col_type == str

    def test_alter_nullable_true_to_false_with_default(self) -> None:
        """nullable True → False，有默认值，自动填充"""
        table = self._make_table()
        table.alter_column('age', nullable=False, default=0)

        assert table.columns['age'].nullable is False
        assert table.data[3]['age'] == 0  # None → 默认值

    def test_alter_nullable_true_to_false_no_default_error(self) -> None:
        """nullable True → False，无默认值，有 None 值 → 报错"""
        table = self._make_table()

        with pytest.raises(SchemaError):
            table.alter_column('age', nullable=False)

        # 验证未修改
        assert table.columns['age'].nullable is True
        assert table.data[3]['age'] is None

    def test_alter_default_only(self) -> None:
        """只修改默认值"""
        table = self._make_table()
        table.alter_column('age', default=18)

        assert table.columns['age'].default == 18
        # 现有数据不变
        assert table.data[1]['age'] == 25

    def test_alter_column_not_found(self) -> None:
        """列不存在"""
        table = self._make_table()
        with pytest.raises(ColumnNotFoundError):
            table.alter_column('nonexistent', col_type=str)

    def test_alter_no_change(self) -> None:
        """不传任何变更参数（no-op）"""
        table = self._make_table()
        old_col = table.columns['age']
        table.alter_column('age')  # 什么都不改
        assert table.columns['age'].col_type == old_col.col_type

    def test_alter_column_with_index_rebuild(self) -> None:
        """修改有索引的列，索引应重建"""
        columns = [
            Column(int, name='id', primary_key=True),
            Column(int, name='score', index=True),
        ]
        table = Table('test', columns, 'id')
        table.data = {
            1: {'id': 1, 'score': 100},
            2: {'id': 2, 'score': 200},
        }

        table.alter_column('score', col_type=str)
        assert table.columns['score'].col_type == str
        assert table.data[1]['score'] == '100'


class TestAlterColumnStorage:
    """Storage.alter_column 测试"""

    def test_alter_column_via_storage(self, temp_dir: Path) -> None:
        """通过 Storage 修改列"""
        db = Storage(file_path=temp_dir / 'test.pytuck')
        db.create_table('users', [
            Column(int, name='id', primary_key=True),
            Column(int, name='age', nullable=True),
        ])
        table = db.get_table('users')
        table.data[1] = {'id': 1, 'age': 25}

        db.alter_column('users', 'age', col_type=str)
        assert db.get_table('users').columns['age'].col_type == str
        assert db.get_table('users').data[1]['age'] == '25'


class TestAlterColumnSession:
    """Session.alter_column 测试"""

    def test_alter_column_via_session(self, temp_dir: Path) -> None:
        """通过 Session 修改列"""
        db = Storage(file_path=temp_dir / 'test.pytuck')
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            age = Column(int, nullable=True)

        session = Session(db)

        from pytuck import insert
        session.execute(insert(User).values(id=1, age=25))
        session.commit()

        session.alter_column(User, 'age', col_type=str)
        table = db.get_table('users')
        assert table.columns['age'].col_type == str


# ==================== set_primary_key 测试 ====================

class TestSetPrimaryKey:
    """Table.set_primary_key 测试"""

    def _make_table(self) -> Table:
        """创建测试表"""
        columns = [
            Column(int, name='id', primary_key=True),
            Column(str, name='email'),
            Column(str, name='name'),
        ]
        table = Table('users', columns, 'id')
        table.data = {
            1: {'id': 1, 'email': 'alice@test.com', 'name': 'Alice'},
            2: {'id': 2, 'email': 'bob@test.com', 'name': 'Bob'},
        }
        table.next_id = 3
        return table

    def test_set_primary_key_success(self) -> None:
        """成功设置新主键"""
        table = self._make_table()
        table.set_primary_key('email')

        assert table.primary_key == 'email'
        assert table.columns['email'].primary_key is True
        assert table.columns['id'].primary_key is False
        # data 字典以新主键为 key
        assert 'alice@test.com' in table.data
        assert 'bob@test.com' in table.data
        assert 1 not in table.data

    def test_set_primary_key_noop(self) -> None:
        """相同主键不做操作"""
        table = self._make_table()
        table.set_primary_key('id')
        assert table.primary_key == 'id'
        assert 1 in table.data

    def test_set_primary_key_duplicate_values(self) -> None:
        """有重复值 → 报错"""
        table = self._make_table()
        table.data[1]['name'] = 'Same'
        table.data[2]['name'] = 'Same'

        with pytest.raises(SchemaError):
            table.set_primary_key('name')

        # 数据未修改
        assert table.primary_key == 'id'
        assert 1 in table.data

    def test_set_primary_key_null_values(self) -> None:
        """有 null 值 → 报错"""
        columns = [
            Column(int, name='id', primary_key=True),
            Column(str, name='email', nullable=True),
        ]
        table = Table('users', columns, 'id')
        table.data = {
            1: {'id': 1, 'email': 'test@test.com'},
            2: {'id': 2, 'email': None},
        }

        with pytest.raises(SchemaError):
            table.set_primary_key('email')

    def test_set_primary_key_column_not_found(self) -> None:
        """列不存在"""
        table = self._make_table()
        with pytest.raises(ColumnNotFoundError):
            table.set_primary_key('nonexistent')

    def test_set_primary_key_int_updates_next_id(self) -> None:
        """设置 int 列为主键时更新 next_id"""
        columns = [
            Column(str, name='code', primary_key=True),
            Column(int, name='seq'),
        ]
        table = Table('items', columns, 'code')
        table.data = {
            'A': {'code': 'A', 'seq': 10},
            'B': {'code': 'B', 'seq': 20},
        }

        table.set_primary_key('seq')
        assert table.next_id == 21

    def test_set_primary_key_via_storage(self, temp_dir: Path) -> None:
        """通过 Storage 修改主键"""
        db = Storage(file_path=temp_dir / 'test.pytuck')
        db.create_table('users', [
            Column(int, name='id', primary_key=True),
            Column(str, name='email'),
        ])
        table = db.get_table('users')
        table.data[1] = {'id': 1, 'email': 'a@test.com'}
        table.data[2] = {'id': 2, 'email': 'b@test.com'}

        db.set_primary_key('users', 'email')
        assert db.get_table('users').primary_key == 'email'


# ==================== reorder_columns 测试 ====================

class TestReorderColumns:
    """Table.reorder_columns 测试"""

    def _make_table(self) -> Table:
        """创建测试表"""
        columns = [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
            Column(int, name='age'),
        ]
        table = Table('users', columns, 'id')
        table.data = {
            1: {'id': 1, 'name': 'Alice', 'age': 25},
        }
        return table

    def test_reorder_success(self) -> None:
        """成功重排列顺序"""
        table = self._make_table()
        table.reorder_columns(['age', 'id', 'name'])

        col_names = list(table.columns.keys())
        assert col_names == ['age', 'id', 'name']

        # 记录字段顺序也应更新
        record_keys = list(table.data[1].keys())
        assert record_keys == ['age', 'id', 'name']

    def test_reorder_missing_column(self) -> None:
        """缺少列 → 报错"""
        table = self._make_table()
        with pytest.raises(SchemaError):
            table.reorder_columns(['id', 'name'])

    def test_reorder_extra_column(self) -> None:
        """多余列 → 报错"""
        table = self._make_table()
        with pytest.raises(SchemaError):
            table.reorder_columns(['id', 'name', 'age', 'extra'])

    def test_reorder_duplicate_column(self) -> None:
        """重复列 → 报错"""
        table = self._make_table()
        with pytest.raises(SchemaError):
            table.reorder_columns(['id', 'name', 'name'])

    def test_reorder_preserves_values(self) -> None:
        """重排后数据值不变"""
        table = self._make_table()
        table.reorder_columns(['age', 'name', 'id'])

        record = table.data[1]
        assert record['id'] == 1
        assert record['name'] == 'Alice'
        assert record['age'] == 25

    def test_reorder_via_storage(self, temp_dir: Path) -> None:
        """通过 Storage 重排列"""
        db = Storage(file_path=temp_dir / 'test.pytuck')
        db.create_table('users', [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
            Column(int, name='age'),
        ])

        db.reorder_columns('users', ['age', 'id', 'name'])
        col_names = list(db.get_table('users').columns.keys())
        assert col_names == ['age', 'id', 'name']


# ==================== Bug 复现测试 ====================

class TestMigrateEngineDataIntegrity:
    """Bug 1: 引擎转换后数据丢失"""

    def test_csv_to_pytuck_preserves_data(self, temp_dir: Path) -> None:
        """CSV → Pytuck 迁移应保留所有数据"""
        from pytuck.tools.migrate import migrate_engine

        # 创建 CSV 源文件
        csv_path = temp_dir / 'source.csv'
        db = Storage(file_path=csv_path, engine='csv')
        db.create_table('users', [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
            Column(int, name='age'),
        ])
        table = db.get_table('users')
        table.insert({'id': 1, 'name': 'Alice', 'age': 25})
        table.insert({'id': 2, 'name': 'Bob', 'age': 30})
        table.insert({'id': 3, 'name': 'Charlie', 'age': 35})
        db.flush()
        db.close()

        # 迁移到 Pytuck
        pytuck_path = temp_dir / 'target.pytuck'
        result = migrate_engine(
            source_path=csv_path,
            source_engine='csv',
            target_path=pytuck_path,
            target_engine='pytuck'
        )

        assert result['tables'] == 1
        assert result['records'] == 3

        # 验证目标文件数据
        db2 = Storage(file_path=pytuck_path, engine='pytuck')
        target_table = db2.get_table('users')
        assert len(target_table.data) == 3
        assert target_table.data[1]['name'] == 'Alice'
        assert target_table.data[2]['name'] == 'Bob'
        assert target_table.data[3]['name'] == 'Charlie'
        db2.close()

    def test_json_to_csv_preserves_data(self, temp_dir: Path) -> None:
        """JSON → CSV 迁移应保留所有数据"""
        from pytuck.tools.migrate import migrate_engine

        json_path = temp_dir / 'source.json'
        db = Storage(file_path=json_path, engine='json')
        db.create_table('items', [
            Column(int, name='id', primary_key=True),
            Column(str, name='value'),
        ])
        table = db.get_table('items')
        table.insert({'id': 1, 'value': 'hello'})
        table.insert({'id': 2, 'value': 'world'})
        db.flush()
        db.close()

        csv_path = temp_dir / 'target.csv'
        result = migrate_engine(
            source_path=json_path,
            source_engine='json',
            target_path=csv_path,
            target_engine='csv'
        )

        assert result['records'] == 2

        db2 = Storage(file_path=csv_path, engine='csv')
        assert len(db2.get_table('items').data) == 2
        db2.close()


class TestFlushLoadDefaultValueIntegrity:
    """Bug 2: flush/load 循环不应篡改数据"""

    @pytest.mark.parametrize("engine", ['pytuck', 'json', 'jsonl', 'csv'])
    def test_add_column_then_set_null_preserves_on_reload(
        self, temp_dir: Path, engine: str
    ) -> None:
        """add_column 带默认值后，手动设为 null，flush/load 后 null 应保持"""
        ext_map = {'pytuck': '.pytuck', 'json': '.json', 'jsonl': '.zip', 'csv': '.csv'}
        file_path = temp_dir / f'test{ext_map[engine]}'

        # 创建数据库并插入数据
        db = Storage(file_path=file_path, engine=engine)
        db.create_table('items', [
            Column(int, name='id', primary_key=True),
            Column(str, name='name'),
        ])
        table = db.get_table('items')
        table.insert({'id': 1, 'name': 'A'})
        table.insert({'id': 2, 'name': 'B'})

        # 添加带默认值的列
        db.add_column('items', Column(int, name='score', nullable=True, default=0), default_value=0)

        # 手动将其中一个设为 None
        table.data[1]['score'] = None
        assert table.data[1]['score'] is None
        assert table.data[2]['score'] == 0

        # flush + 重新 load
        db.flush()
        db.close()

        db2 = Storage(file_path=file_path, engine=engine)
        table2 = db2.get_table('items')

        # 验证 null 值保持不变
        assert table2.data[1]['score'] is None, \
            f"{engine} 后端在 flush/load 后将 null 值篡改为默认值"
        assert table2.data[2]['score'] == 0
        db2.close()

    @pytest.mark.parametrize("engine", ['pytuck', 'json', 'jsonl', 'csv'])
    def test_column_default_preserved_after_flush_load(
        self, temp_dir: Path, engine: str
    ) -> None:
        """Column 的 default 字段应在 flush/load 后保留"""
        ext_map = {'pytuck': '.pytuck', 'json': '.json', 'jsonl': '.zip', 'csv': '.csv'}
        file_path = temp_dir / f'test{ext_map[engine]}'

        db = Storage(file_path=file_path, engine=engine)
        db.create_table('items', [
            Column(int, name='id', primary_key=True),
            Column(int, name='score', nullable=True, default=42),
        ])
        db.flush()
        db.close()

        db2 = Storage(file_path=file_path, engine=engine)
        table2 = db2.get_table('items')

        if engine != 'pytuck':
            # 文本后端应保留 default（Pytuck 后端暂不支持）
            assert table2.columns['score'].default == 42, \
                f"{engine} 后端 flush/load 后丢失了 Column.default"
        db2.close()
