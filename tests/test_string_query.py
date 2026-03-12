"""
字符串匹配查询测试

测试 contains/startswith/endswith 操作符在以下场景的正确性：
- Column 方法生成 BinaryExpression
- _OPERATOR_EVAL 内存评估（大小写不敏感、None 安全）
- Query.filter() 查询
- select().where() 查询
- query_table_data list 格式 filters
"""
from pathlib import Path
from typing import Type

import pytest

from pytuck import Storage, declarative_base, Session, Column, PureBaseModel
from pytuck import select, insert
from pytuck.query.builder import _OPERATOR_EVAL, BinaryExpression, Condition


# ==================== Fixtures ====================

@pytest.fixture
def db_with_users(temp_file: Path):
    """创建包含测试用户数据的数据库"""
    db = Storage(file_path=str(temp_file))
    Base: Type[PureBaseModel] = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str)
        email = Column(str)

    session = Session(db)

    users = [
        {'name': 'Alice', 'email': 'alice@example.com'},
        {'name': 'Bob', 'email': 'bob@test.org'},
        {'name': 'Charlie', 'email': 'charlie@example.com'},
        {'name': 'alice_lower', 'email': 'ALICE@UPPER.COM'},
        {'name': 'David', 'email': 'david@test.org'},
    ]
    for u in users:
        session.execute(insert(User).values(**u))
    session.commit()

    return db, User, session


# ==================== _OPERATOR_EVAL 单元测试 ====================

class TestOperatorEval:
    """测试 _OPERATOR_EVAL 中的字符串匹配操作符"""

    def test_like_match(self) -> None:
        """LIKE: 包含匹配"""
        assert _OPERATOR_EVAL['LIKE']('Hello World', 'world') is True
        assert _OPERATOR_EVAL['LIKE']('Hello World', 'hello') is True
        assert _OPERATOR_EVAL['LIKE']('Hello World', 'xyz') is False

    def test_like_case_insensitive(self) -> None:
        """LIKE: 大小写不敏感"""
        assert _OPERATOR_EVAL['LIKE']('Alice', 'alice') is True
        assert _OPERATOR_EVAL['LIKE']('Alice', 'ALICE') is True
        assert _OPERATOR_EVAL['LIKE']('alice', 'Alice') is True

    def test_like_none_safe(self) -> None:
        """LIKE: None 值安全"""
        assert _OPERATOR_EVAL['LIKE'](None, 'test') is False
        assert _OPERATOR_EVAL['LIKE']('test', None) is False
        assert _OPERATOR_EVAL['LIKE'](None, None) is False

    def test_like_non_string(self) -> None:
        """LIKE: 非字符串值返回 False"""
        assert _OPERATOR_EVAL['LIKE'](123, 'test') is False
        assert _OPERATOR_EVAL['LIKE']('test', 123) is False

    def test_startswith_match(self) -> None:
        """STARTSWITH: 前缀匹配"""
        assert _OPERATOR_EVAL['STARTSWITH']('Hello World', 'hello') is True
        assert _OPERATOR_EVAL['STARTSWITH']('Hello World', 'world') is False

    def test_startswith_case_insensitive(self) -> None:
        """STARTSWITH: 大小写不敏感"""
        assert _OPERATOR_EVAL['STARTSWITH']('Alice', 'ali') is True
        assert _OPERATOR_EVAL['STARTSWITH']('Alice', 'ALI') is True

    def test_startswith_none_safe(self) -> None:
        """STARTSWITH: None 值安全"""
        assert _OPERATOR_EVAL['STARTSWITH'](None, 'test') is False
        assert _OPERATOR_EVAL['STARTSWITH']('test', None) is False

    def test_endswith_match(self) -> None:
        """ENDSWITH: 后缀匹配"""
        assert _OPERATOR_EVAL['ENDSWITH']('Hello World', 'world') is True
        assert _OPERATOR_EVAL['ENDSWITH']('Hello World', 'hello') is False

    def test_endswith_case_insensitive(self) -> None:
        """ENDSWITH: 大小写不敏感"""
        assert _OPERATOR_EVAL['ENDSWITH']('Alice', 'ICE') is True
        assert _OPERATOR_EVAL['ENDSWITH']('Alice', 'ice') is True

    def test_endswith_none_safe(self) -> None:
        """ENDSWITH: None 值安全"""
        assert _OPERATOR_EVAL['ENDSWITH'](None, 'test') is False
        assert _OPERATOR_EVAL['ENDSWITH']('test', None) is False


# ==================== Column 方法测试 ====================

class TestColumnStringMethods:
    """测试 Column 类的字符串匹配方法"""

    def test_contains_returns_binary_expression(self) -> None:
        """contains() 返回正确的 BinaryExpression"""
        col = Column(str)
        col.name = 'name'
        expr = col.contains('ali')
        assert isinstance(expr, BinaryExpression)
        assert expr.operator == 'LIKE'
        assert expr.value == 'ali'

    def test_startswith_returns_binary_expression(self) -> None:
        """startswith() 返回正确的 BinaryExpression"""
        col = Column(str)
        col.name = 'name'
        expr = col.startswith('Al')
        assert isinstance(expr, BinaryExpression)
        assert expr.operator == 'STARTSWITH'
        assert expr.value == 'Al'

    def test_endswith_returns_binary_expression(self) -> None:
        """endswith() 返回正确的 BinaryExpression"""
        col = Column(str)
        col.name = 'name'
        expr = col.endswith('ce')
        assert isinstance(expr, BinaryExpression)
        assert expr.operator == 'ENDSWITH'
        assert expr.value == 'ce'

    def test_contains_to_condition(self) -> None:
        """contains() 生成的表达式可转换为 Condition"""
        col = Column(str)
        col.name = 'email'
        expr = col.contains('example')
        cond = expr.to_condition()
        assert isinstance(cond, Condition)
        assert cond.field == 'email'
        assert cond.operator == 'LIKE'
        assert cond.value == 'example'


# ==================== Query.filter() 集成测试 ====================

class TestQueryFilterStringMatch:
    """测试通过 Query.filter() 使用字符串匹配"""

    def test_contains_filter(self, db_with_users) -> None:
        """Query.filter(User.name.contains(...)) 返回正确结果"""
        db, User, session = db_with_users
        from pytuck.query.builder import Query
        results = Query(User, db).filter(User.name.contains('ali')).all()
        names = [u.name for u in results]
        assert 'Alice' in names
        assert 'alice_lower' in names
        assert 'Bob' not in names

    def test_startswith_filter(self, db_with_users) -> None:
        """Query.filter(User.name.startswith(...)) 返回正确结果"""
        db, User, session = db_with_users
        from pytuck.query.builder import Query
        results = Query(User, db).filter(User.name.startswith('ali')).all()
        names = [u.name for u in results]
        assert 'Alice' in names
        assert 'alice_lower' in names
        assert 'Charlie' not in names

    def test_endswith_filter(self, db_with_users) -> None:
        """Query.filter(User.email.endswith(...)) 返回正确结果"""
        db, User, session = db_with_users
        from pytuck.query.builder import Query
        results = Query(User, db).filter(User.email.endswith('example.com')).all()
        names = [u.name for u in results]
        assert 'Alice' in names
        assert 'Charlie' in names
        assert 'Bob' not in names

    def test_contains_no_match(self, db_with_users) -> None:
        """contains 没有匹配时返回空列表"""
        db, User, session = db_with_users
        from pytuck.query.builder import Query
        results = Query(User, db).filter(User.name.contains('xyz')).all()
        assert results == []


# ==================== select().where() 集成测试 ====================

class TestSelectWhereStringMatch:
    """测试通过 select().where() 使用字符串匹配"""

    def test_select_where_contains(self, db_with_users) -> None:
        """select(User).where(User.name.contains(...))"""
        db, User, session = db_with_users
        stmt = select(User).where(User.name.contains('ali'))
        result = session.execute(stmt)
        users = result.all()
        names = [u.name for u in users]
        assert 'Alice' in names
        assert 'alice_lower' in names

    def test_select_where_startswith(self, db_with_users) -> None:
        """select(User).where(User.name.startswith(...))"""
        db, User, session = db_with_users
        stmt = select(User).where(User.name.startswith('Ch'))
        result = session.execute(stmt)
        users = result.all()
        names = [u.name for u in users]
        assert 'Charlie' in names
        assert len(names) == 1

    def test_select_where_endswith(self, db_with_users) -> None:
        """select(User).where(User.email.endswith('.org'))"""
        db, User, session = db_with_users
        stmt = select(User).where(User.email.endswith('.org'))
        result = session.execute(stmt)
        users = result.all()
        names = [u.name for u in users]
        assert 'Bob' in names
        assert 'David' in names
        assert 'Alice' not in names

    def test_select_where_combined(self, db_with_users) -> None:
        """字符串匹配与其他条件组合"""
        db, User, session = db_with_users
        stmt = select(User).where(
            User.email.contains('example'),
            User.name.startswith('A')
        )
        result = session.execute(stmt)
        users = result.all()
        assert len(users) == 1
        assert users[0].name == 'Alice'


# ==================== query_table_data 测试 ====================

class TestQueryTableDataFilters:
    """测试 query_table_data 的 filters 参数扩展"""

    def test_dict_filters_backward_compatible(self, db_with_users) -> None:
        """dict 格式 filters 向后兼容"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters={'name': 'Alice'})
        assert result['total_count'] == 1
        assert result['records'][0]['name'] == 'Alice'

    def test_list_filters_equal(self, db_with_users) -> None:
        """list 格式 filters 等值过滤"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters=[
            {'field': 'name', 'operator': '=', 'value': 'Bob'}
        ])
        assert result['total_count'] == 1
        assert result['records'][0]['name'] == 'Bob'

    def test_list_filters_like(self, db_with_users) -> None:
        """list 格式 filters LIKE 操作符"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters=[
            {'field': 'name', 'operator': 'LIKE', 'value': 'ali'}
        ])
        names = [r['name'] for r in result['records']]
        assert 'Alice' in names
        assert 'alice_lower' in names
        assert result['total_count'] == 2

    def test_list_filters_startswith(self, db_with_users) -> None:
        """list 格式 filters STARTSWITH 操作符"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters=[
            {'field': 'email', 'operator': 'STARTSWITH', 'value': 'alice'}
        ])
        names = [r['name'] for r in result['records']]
        assert 'Alice' in names
        assert 'alice_lower' in names

    def test_list_filters_endswith(self, db_with_users) -> None:
        """list 格式 filters ENDSWITH 操作符"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters=[
            {'field': 'email', 'operator': 'ENDSWITH', 'value': '.org'}
        ])
        names = [r['name'] for r in result['records']]
        assert 'Bob' in names
        assert 'David' in names
        assert 'Alice' not in names

    def test_list_filters_multiple(self, db_with_users) -> None:
        """list 格式 filters 多条件组合"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters=[
            {'field': 'email', 'operator': 'ENDSWITH', 'value': '.com'},
            {'field': 'name', 'operator': 'STARTSWITH', 'value': 'a'}
        ])
        names = [r['name'] for r in result['records']]
        assert 'Alice' in names
        assert 'alice_lower' in names
        assert 'Charlie' not in names

    def test_list_filters_ignore_invalid_field(self, db_with_users) -> None:
        """list 格式 filters 忽略不存在的字段"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters=[
            {'field': 'nonexistent', 'operator': '=', 'value': 'test'}
        ])
        # 不存在的字段被忽略，返回所有记录
        assert result['total_count'] == 5

    def test_none_filters(self, db_with_users) -> None:
        """filters=None 返回所有记录"""
        db, User, session = db_with_users
        result = db.query_table_data('users', filters=None)
        assert result['total_count'] == 5
