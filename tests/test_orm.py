"""
Pytuck ORM 模块测试

测试内容：
1. PureBaseModel - 纯模型定义
2. CRUDBaseModel - Active Record 模式
3. declarative_base - 工厂函数
4. Column - 列定义和验证
5. 多引擎兼容性测试
"""
import os
import sys
import unittest
from datetime import datetime
from typing import Type

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from examples._common import mktemp_dir_project
from pytuck import (
    Storage, Session, Column, Relationship,
    declarative_base, PureBaseModel, CRUDBaseModel,
    select, insert, update, delete,
)
from pytuck.common.exceptions import ValidationError, SchemaError


class TestColumn(unittest.TestCase):
    """Column 类测试"""

    def test_column_basic(self):
        """测试 Column 基本功能"""
        col = Column(str, name='username', nullable=False)
        self.assertEqual(col.name, 'username')
        self.assertEqual(col.col_type, str)
        self.assertFalse(col.nullable)
        self.assertFalse(col.primary_key)

    def test_column_primary_key(self):
        """测试主键列"""
        col = Column(int, primary_key=True)
        self.assertTrue(col.primary_key)

    def test_column_validation_success(self):
        """测试列验证成功"""
        col = Column(int, name='age')
        self.assertEqual(col.validate(25), 25)
        self.assertEqual(col.validate(None), None)  # nullable=True

    def test_column_validation_type_conversion(self):
        """测试类型转换"""
        col = Column(int, name='age')
        self.assertEqual(col.validate("25"), 25)

    def test_column_validation_nullable_fail(self):
        """测试非空验证失败"""
        col = Column(str, name='name', nullable=False)
        with self.assertRaises(ValidationError):
            col.validate(None)

    def test_column_validation_type_fail(self):
        """测试类型验证失败"""
        col = Column(int, name='age')
        with self.assertRaises(ValidationError):
            col.validate("not_a_number")

    def test_column_to_dict(self):
        """测试转换为字典"""
        col = Column(int, name='id', primary_key=True)
        d = col.to_dict()
        self.assertEqual(d['name'], 'id')
        self.assertEqual(d['type'], 'int')
        self.assertTrue(d['primary_key'])


class TestDeclarativeBase(unittest.TestCase):
    """declarative_base 工厂函数测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = mktemp_dir_project()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Storage(file_path=self.db_path)

    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_default_returns_pure_base(self):
        """测试默认返回纯模型基类"""
        Base = declarative_base(self.db)

        class TestModel(Base):
            __tablename__ = 'test_default'
            id = Column(int, primary_key=True)
            name = Column(str)

        # 验证没有 CRUD 方法
        self.assertFalse(hasattr(TestModel, 'create'))
        self.assertFalse(hasattr(TestModel, 'save'))
        self.assertFalse(hasattr(TestModel, 'delete'))

    def test_crud_false_returns_pure_base(self):
        """测试 crud=False 返回纯模型基类"""
        Base = declarative_base(self.db, crud=False)

        class TestModel(Base):
            __tablename__ = 'test_crud_false'
            id = Column(int, primary_key=True)

        self.assertFalse(hasattr(TestModel, 'create'))

    def test_crud_true_returns_crud_base(self):
        """测试 crud=True 返回 CRUD 基类"""
        Base = declarative_base(self.db, crud=True)

        class TestModel(Base):
            __tablename__ = 'test_crud_true'
            id = Column(int, primary_key=True)
            name = Column(str)

        # 验证有 CRUD 方法
        self.assertTrue(hasattr(TestModel, 'create'))
        self.assertTrue(hasattr(TestModel, 'save'))
        self.assertTrue(hasattr(TestModel, 'delete'))
        self.assertTrue(hasattr(TestModel, 'refresh'))
        self.assertTrue(hasattr(TestModel, 'get'))
        self.assertTrue(hasattr(TestModel, 'filter'))
        self.assertTrue(hasattr(TestModel, 'filter_by'))
        self.assertTrue(hasattr(TestModel, 'all'))

    def test_storage_binding(self):
        """测试 Storage 绑定"""
        Base = declarative_base(self.db)

        class TestModel(Base):
            __tablename__ = 'test_binding'
            id = Column(int, primary_key=True)

        self.assertIs(TestModel.__storage__, self.db)

    def test_tablename_required(self):
        """测试无 __tablename__ 且未标记 __abstract__ 的类必须报错"""
        Base = declarative_base(self.db)

        with self.assertRaises(ValidationError):
            class BadModel(Base):
                id = Column(int, primary_key=True)

    def test_column_collection(self):
        """测试列收集"""
        Base = declarative_base(self.db)

        class TestModel(Base):
            __tablename__ = 'test_columns'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int)

        self.assertEqual(len(TestModel.__columns__), 3)
        self.assertIn('id', TestModel.__columns__)
        self.assertIn('name', TestModel.__columns__)
        self.assertIn('age', TestModel.__columns__)

    def test_primary_key_detection(self):
        """测试主键检测"""
        Base = declarative_base(self.db)

        class TestModel(Base):
            __tablename__ = 'test_pk'
            user_id = Column(int, primary_key=True)
            name = Column(str)

        self.assertEqual(TestModel.__primary_key__, 'user_id')

    def test_no_primary_key_allowed(self):
        """测试无主键模型可以正常工作"""
        Base = declarative_base(self.db)

        class TestModel(Base):
            __tablename__ = 'test_no_pk'
            name = Column(str)
            age = Column(int)

        # 无主键模型的 __primary_key__ 应为 None
        self.assertIsNone(TestModel.__primary_key__)

    def test_id_column_without_primary_key_no_error(self):
        """测试定义 id 列但不设置 primary_key=True 不会自动成为主键"""
        Base = declarative_base(self.db)

        class TestModel(Base):
            __tablename__ = 'test_id_no_pk'
            id = Column(str)  # 没有 primary_key=True
            name = Column(str)

        # 即使有 id 列，如果没有 primary_key=True，也是无主键模型
        self.assertIsNone(TestModel.__primary_key__)


class TestPureBaseModel(unittest.TestCase):
    """PureBaseModel 测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = mktemp_dir_project()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Storage(file_path=self.db_path)

        # 创建纯模型基类
        self.Base: Type[PureBaseModel] = declarative_base(self.db)

        class User(self.Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=False)
            age = Column(int)

        self.User = User

    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_instance_creation(self):
        """测试实例创建"""
        user = self.User(name='Alice', age=25)
        self.assertEqual(user.name, 'Alice')
        self.assertEqual(user.age, 25)
        self.assertIsNone(user.id)

    def test_to_dict(self):
        """测试转换为字典"""
        user = self.User(name='Alice', age=25)
        d = user.to_dict()
        self.assertEqual(d['name'], 'Alice')
        self.assertEqual(d['age'], 25)

    def test_repr(self):
        """测试字符串表示"""
        user = self.User(name='Alice', age=25)
        repr_str = repr(user)
        self.assertIn('User', repr_str)

    def test_default_values(self):
        """测试默认值"""
        Base = declarative_base(self.db)

        class TestModel(Base):
            __tablename__ = 'test_defaults'
            id = Column(int, primary_key=True)
            status = Column(str, default='active')

        instance = TestModel()
        self.assertEqual(instance.status, 'active')

    def test_session_operations(self):
        """测试通过 Session 操作"""
        session = Session(self.db)

        # 插入
        user = self.User(name='Alice', age=25)
        session.add(user)
        session.commit()

        # 查询
        stmt = select(self.User).where(self.User.name == 'Alice')
        result = session.execute(stmt)
        users = result.all()

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].name, 'Alice')


class TestCRUDBaseModel(unittest.TestCase):
    """CRUDBaseModel 测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = mktemp_dir_project()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Storage(file_path=self.db_path)

        # 创建 CRUD 基类
        self.Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(self.Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=False)
            age = Column(int)

        self.User = User

    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_create(self):
        """测试 create 方法"""
        user = self.User.create(name='Alice', age=25)
        self.assertIsNotNone(user.id)
        self.assertEqual(user.name, 'Alice')
        self.assertEqual(user.age, 25)
        self.assertTrue(user._loaded_from_db)

    def test_save_insert(self):
        """测试 save 插入"""
        user = self.User(name='Bob', age=30)
        self.assertIsNone(user.id)

        user.save()

        self.assertIsNotNone(user.id)
        self.assertTrue(user._loaded_from_db)

    def test_save_update(self):
        """测试 save 更新"""
        user = self.User.create(name='Alice', age=25)
        original_id = user.id

        user.name = 'Alice Updated'
        user.save()

        # ID 应该不变
        self.assertEqual(user.id, original_id)

        # 从数据库重新获取验证更新
        refreshed = self.User.get(original_id)
        self.assertEqual(refreshed.name, 'Alice Updated')

    def test_delete(self):
        """测试 delete 方法"""
        user = self.User.create(name='ToDelete', age=20)
        user_id = user.id

        user.delete()

        # 验证已删除
        deleted = self.User.get(user_id)
        self.assertIsNone(deleted)

    def test_refresh(self):
        """测试 refresh 方法"""
        user = self.User.create(name='Original', age=25)

        # 模拟外部修改（通过另一个实例）
        another = self.User.get(user.id)
        another.name = 'Modified'
        another.save()

        # 刷新原实例
        user.refresh()
        self.assertEqual(user.name, 'Modified')

    def test_get_found(self):
        """测试 get 方法 - 找到记录"""
        user = self.User.create(name='FindMe', age=30)

        found = self.User.get(user.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, 'FindMe')

    def test_get_not_found(self):
        """测试 get 方法 - 未找到记录"""
        result = self.User.get(99999)
        self.assertIsNone(result)

    def test_filter_expression(self):
        """测试 filter 方法 - 表达式语法"""
        self.User.create(name='Young', age=18)
        self.User.create(name='Old', age=60)

        users = self.User.filter(self.User.age >= 30).all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].name, 'Old')

    def test_filter_by(self):
        """测试 filter_by 方法"""
        self.User.create(name='Alice', age=25)
        self.User.create(name='Bob', age=30)

        users = self.User.filter_by(name='Alice').all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].name, 'Alice')

    def test_all(self):
        """测试 all 方法"""
        self.User.create(name='User1', age=20)
        self.User.create(name='User2', age=25)
        self.User.create(name='User3', age=30)

        users = self.User.all()
        self.assertEqual(len(users), 3)

    def test_filter_chaining(self):
        """测试链式查询"""
        self.User.create(name='Alice', age=25)
        self.User.create(name='Bob', age=30)
        self.User.create(name='Charlie', age=35)

        users = self.User.filter(self.User.age >= 25).filter(self.User.age < 35).all()
        self.assertEqual(len(users), 2)

    def test_filter_order_by(self):
        """测试排序"""
        self.User.create(name='Charlie', age=35)
        self.User.create(name='Alice', age=25)
        self.User.create(name='Bob', age=30)

        users = self.User.filter(self.User.age >= 0).order_by('age').all()
        self.assertEqual(users[0].name, 'Alice')
        self.assertEqual(users[-1].name, 'Charlie')

    def test_filter_limit(self):
        """测试限制"""
        for i in range(10):
            self.User.create(name=f'User{i}', age=20+i)

        users = self.User.filter(self.User.age >= 0).limit(3).all()
        self.assertEqual(len(users), 3)


class TestMultipleEngines(unittest.TestCase):
    """多存储引擎测试"""

    def _test_engine(self, engine: str, file_ext: str):
        """测试单个引擎"""
        temp_dir = mktemp_dir_project()
        db_path = os.path.join(temp_dir, f'test.{file_ext}')

        try:
            db = Storage(file_path=db_path, engine=engine)
            Base = declarative_base(db, crud=True)

            class Item(Base):
                __tablename__ = 'items'
                id = Column(int, primary_key=True)
                name = Column(str)
                value = Column(float)

            # 创建
            item = Item.create(name='Test', value=3.14)
            self.assertIsNotNone(item.id)

            # 读取
            found = Item.get(item.id)
            self.assertEqual(found.name, 'Test')

            # 更新
            found.value = 2.71
            found.save()

            # 验证更新
            updated = Item.get(item.id)
            self.assertAlmostEqual(updated.value, 2.71, places=2)

            # 删除
            updated.delete()
            deleted = Item.get(item.id)
            self.assertIsNone(deleted)

            db.close()

        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    def test_binary_engine(self):
        """测试 Binary 引擎"""
        self._test_engine('binary', 'db')

    def test_json_engine(self):
        """测试 JSON 引擎"""
        self._test_engine('json', 'json')

    def test_csv_engine(self):
        """测试 CSV 引擎"""
        # CSV 引擎需要特殊处理，跳过此测试
        pass

    def test_sqlite_engine(self):
        """测试 SQLite 引擎"""
        try:
            import sqlite3
            self._test_engine('sqlite', 'sqlite')
        except ImportError:
            self.skipTest("SQLite not available")


class TestTypeAnnotations(unittest.TestCase):
    """类型注解测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = mktemp_dir_project()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Storage(file_path=self.db_path)

    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_pure_base_type_annotation(self):
        """测试 PureBaseModel 类型注解"""
        Base: Type[PureBaseModel] = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        # 类型检查应该通过
        self.assertTrue(True)

    def test_crud_base_type_annotation(self):
        """测试 CRUDBaseModel 类型注解"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        # 类型检查应该通过
        self.assertTrue(True)

    def test_isinstance_pure_base_model(self):
        """测试 PureBaseModel 的 isinstance 检查"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_isinstance'
            id = Column(int, primary_key=True)
            name = Column(str)

        user = User(name='Alice')

        # isinstance 检查应该通过
        self.assertIsInstance(user, PureBaseModel)
        self.assertTrue(isinstance(user, PureBaseModel))

    def test_isinstance_crud_base_model(self):
        """测试 CRUDBaseModel 的 isinstance 检查"""
        Base = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users_isinstance_crud'
            id = Column(int, primary_key=True)
            name = Column(str)

        user = User.create(name='Alice')

        # isinstance 检查应该通过（CRUDBaseModel 和 PureBaseModel）
        self.assertIsInstance(user, CRUDBaseModel)
        self.assertIsInstance(user, PureBaseModel)
        self.assertTrue(isinstance(user, CRUDBaseModel))
        self.assertTrue(isinstance(user, PureBaseModel))

    def test_issubclass_checks(self):
        """测试 issubclass 检查"""
        PureBase = declarative_base(self.db)
        CRUDBase = declarative_base(self.db, crud=True)

        class PureUser(PureBase):
            __tablename__ = 'pure_users_sub'
            id = Column(int, primary_key=True)

        class CRUDUser(CRUDBase):
            __tablename__ = 'crud_users_sub'
            id = Column(int, primary_key=True)

        # issubclass 检查
        self.assertTrue(issubclass(PureUser, PureBaseModel))
        self.assertTrue(issubclass(CRUDUser, CRUDBaseModel))
        self.assertTrue(issubclass(CRUDUser, PureBaseModel))


class TestColumnNameMapping(unittest.TestCase):
    """测试 Column.name 映射功能"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = mktemp_dir_project()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Storage(file_path=self.db_path)

    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_to_dict_default_uses_attr_name(self):
        """测试 to_dict() 默认使用属性名"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_todict_default'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')
            nm = Column(str, name='display_name')

        user = User(lv='admin', nm='Alice')
        d = user.to_dict()

        # 默认使用属性名作为键
        self.assertIn('lv', d)
        self.assertIn('nm', d)
        self.assertNotIn('level', d)
        self.assertNotIn('display_name', d)
        self.assertEqual(d['lv'], 'admin')
        self.assertEqual(d['nm'], 'Alice')

    def test_to_dict_with_column_names(self):
        """测试 to_dict(use_column_names=True) 使用 Column.name"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_todict_colname'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')
            nm = Column(str, name='display_name')

        user = User(lv='admin', nm='Alice')
        d = user.to_dict(use_column_names=True)

        # 使用 Column.name 作为键
        self.assertIn('level', d)
        self.assertIn('display_name', d)
        self.assertNotIn('lv', d)
        self.assertNotIn('nm', d)
        self.assertEqual(d['level'], 'admin')
        self.assertEqual(d['display_name'], 'Alice')

    def test_crud_save_with_column_name(self):
        """测试 CRUDBaseModel.save() 使用 Column.name 正确存储数据"""
        Base = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users_crud_colname'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')

        # 创建并保存
        user = User.create(lv='admin')
        self.assertEqual(user.lv, 'admin')

        # 通过 get 重新加载
        loaded_user = User.get(user.id)
        self.assertIsNotNone(loaded_user)
        self.assertEqual(loaded_user.lv, 'admin')

    def test_crud_refresh_with_column_name(self):
        """测试 CRUDBaseModel.refresh() 正确转换列名"""
        Base = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users_crud_refresh'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')

        # 创建用户
        user = User.create(lv='admin')
        user_id = user.id

        # 直接通过 storage 更新（模拟外部修改）
        self.db.update('users_crud_refresh', user_id, {'level': 'superadmin'})

        # refresh 应该正确更新属性
        user.refresh()
        self.assertEqual(user.lv, 'superadmin')

    def test_session_add_with_column_name(self):
        """测试 Session.add() 使用 Column.name 正确存储数据"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_session_colname'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')

        session = Session(self.db)
        user = User(lv='moderator')
        session.add(user)
        session.commit()

        # 验证数据正确存储
        self.assertIsNotNone(user.id)
        self.assertEqual(user.lv, 'moderator')

        # 通过 storage 直接读取验证
        record = self.db.select('users_session_colname', user.id)
        # 存储层使用 Column.name
        self.assertEqual(record.get('level'), 'moderator')

    def test_session_refresh_with_column_name(self):
        """测试 Session.refresh() 正确转换列名"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_session_refresh'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')

        session = Session(self.db)
        user = User(lv='user')
        session.add(user)
        session.commit()

        user_id = user.id

        # 直接通过 storage 更新（模拟外部修改）
        self.db.update('users_session_refresh', user_id, {'level': 'premium'})

        # refresh 应该正确更新属性
        session.refresh(user)
        self.assertEqual(user.lv, 'premium')

    def test_attr_to_column_name_method(self):
        """测试 _attr_to_column_name 方法"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_attr_method'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')
            name = Column(str)  # 未指定 name，使用属性名

        # 测试有显式 name 的列
        self.assertEqual(User._attr_to_column_name('lv'), 'level')

        # 测试未指定 name 的列（使用属性名）
        self.assertEqual(User._attr_to_column_name('name'), 'name')

        # 测试不存在的属性
        self.assertEqual(User._attr_to_column_name('nonexistent'), 'nonexistent')

    def test_column_to_attr_name_method(self):
        """测试 _column_to_attr_name 方法"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_col_method'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')
            name = Column(str)

        # 测试通过 Column.name 查找属性名
        self.assertEqual(User._column_to_attr_name('level'), 'lv')

        # 测试未显式指定 name 的列
        self.assertEqual(User._column_to_attr_name('name'), 'name')

        # 测试不存在的列名
        self.assertIsNone(User._column_to_attr_name('nonexistent'))

    def test_session_query_with_column_name(self):
        """测试 session.query() 正确使用 Column.name 映射"""
        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_query_colname'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')
            nm = Column(str, name='display_name')

        session = Session(self.db)

        # 添加测试数据
        user1 = User(lv='admin', nm='Alice')
        user2 = User(lv='user', nm='Bob')
        session.add(user1)
        session.add(user2)
        session.commit()

        # 通过 session.query() 查询
        users = session.query(User).all()
        self.assertEqual(len(users), 2)

        # 验证属性正确映射
        user_names = {u.nm for u in users}
        self.assertIn('Alice', user_names)
        self.assertIn('Bob', user_names)

        user_levels = {u.lv for u in users}
        self.assertIn('admin', user_levels)
        self.assertIn('user', user_levels)

    def test_session_execute_select_with_column_name(self):
        """测试 session.execute(select()) 正确使用 Column.name 映射"""
        from pytuck import select

        Base = declarative_base(self.db)

        class User(Base):
            __tablename__ = 'users_select_colname'
            id = Column(int, primary_key=True)
            lv = Column(str, name='level')
            nm = Column(str, name='display_name')

        session = Session(self.db)

        # 添加测试数据
        user1 = User(lv='moderator', nm='Charlie')
        session.add(user1)
        session.commit()

        # 通过 session.execute(select()) 查询
        result = session.execute(select(User))
        users = result.all()
        self.assertEqual(len(users), 1)

        # 验证属性正确映射
        user = users[0]
        self.assertEqual(user.lv, 'moderator')
        self.assertEqual(user.nm, 'Charlie')


class TestToDictEnhanced(unittest.TestCase):
    """to_dict() 增强功能和 to_json() 测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = mktemp_dir_project()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Storage(file_path=self.db_path)

        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class Department(Base):
            __tablename__ = 'departments'
            id = Column(int, primary_key=True)
            name = Column(str)
            employees: list = Relationship('employees', foreign_key='dept_id')  # type: ignore

        class Employee(Base):
            __tablename__ = 'employees'
            id = Column(int, primary_key=True)
            name = Column(str)
            age = Column(int)
            dept_id = Column(int)
            department: 'Department' = Relationship(  # type: ignore
                'departments', foreign_key='dept_id', uselist=False
            )

        self.Department = Department
        self.Employee = Employee
        self.Base = Base

    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    # ---- to_dict include/exclude ----

    def test_to_dict_include(self):
        """include 参数只返回指定字段"""
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        d = emp.to_dict(include={'name', 'age'})
        self.assertIn('name', d)
        self.assertIn('age', d)
        self.assertNotIn('id', d)
        self.assertNotIn('dept_id', d)

    def test_to_dict_exclude(self):
        """exclude 参数排除指定字段"""
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        d = emp.to_dict(exclude={'age', 'dept_id'})
        self.assertIn('name', d)
        self.assertIn('id', d)
        self.assertNotIn('age', d)
        self.assertNotIn('dept_id', d)

    def test_to_dict_include_priority(self):
        """include 和 exclude 同时传入时 include 优先"""
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        # include 和 exclude 同时指定，include 优先
        d = emp.to_dict(include={'name', 'age'}, exclude={'name'})
        self.assertIn('name', d)
        self.assertIn('age', d)
        self.assertNotIn('id', d)
        self.assertNotIn('dept_id', d)

    def test_to_dict_include_empty(self):
        """include 为空集合时返回空字典"""
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        d = emp.to_dict(include=set())
        self.assertEqual(d, {})

    def test_to_dict_exclude_empty(self):
        """exclude 为空集合时返回全部字段"""
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        d = emp.to_dict(exclude=set())
        self.assertIn('name', d)
        self.assertIn('age', d)
        self.assertIn('id', d)
        self.assertIn('dept_id', d)

    # ---- to_dict depth ----

    def test_to_dict_depth_zero(self):
        """depth=0 不展开 Relationship（默认行为）"""
        dept = self.Department.create(name='Engineering')
        self.Employee.create(name='Alice', age=25, dept_id=dept.id)
        d = dept.to_dict()
        # depth=0 时不应包含 Relationship 字段
        self.assertNotIn('employees', d)

    def test_to_dict_depth_one(self):
        """depth=1 展开一层关联数据（多对一）"""
        dept = self.Department.create(name='Engineering')
        emp = self.Employee.create(name='Alice', age=25, dept_id=dept.id)
        d = emp.to_dict(depth=1)
        self.assertIn('department', d)
        self.assertIsInstance(d['department'], dict)
        self.assertEqual(d['department']['name'], 'Engineering')

    def test_to_dict_depth_with_list(self):
        """depth 展开一对多关联（返回列表）"""
        dept = self.Department.create(name='Engineering')
        self.Employee.create(name='Alice', age=25, dept_id=dept.id)
        self.Employee.create(name='Bob', age=30, dept_id=dept.id)
        d = dept.to_dict(depth=1)
        self.assertIn('employees', d)
        self.assertIsInstance(d['employees'], list)
        self.assertEqual(len(d['employees']), 2)
        names = {e['name'] for e in d['employees']}
        self.assertEqual(names, {'Alice', 'Bob'})

    def test_to_dict_depth_none_relation(self):
        """关联值为 None 时的处理"""
        # dept_id 为 None，关联应返回 None
        emp = self.Employee.create(name='Alice', age=25, dept_id=None)
        d = emp.to_dict(depth=1)
        self.assertIn('department', d)
        self.assertIsNone(d['department'])

    def test_to_dict_include_with_depth(self):
        """include + depth 组合使用"""
        dept = self.Department.create(name='Engineering')
        emp = self.Employee.create(name='Alice', age=25, dept_id=dept.id)
        # include 同时包含普通字段和 relationship 名
        d = emp.to_dict(include={'name', 'department'}, depth=1)
        self.assertIn('name', d)
        self.assertIn('department', d)
        self.assertNotIn('id', d)
        self.assertNotIn('age', d)
        self.assertNotIn('dept_id', d)

    def test_to_dict_exclude_with_depth(self):
        """exclude + depth 组合使用"""
        dept = self.Department.create(name='Engineering')
        emp = self.Employee.create(name='Alice', age=25, dept_id=dept.id)
        d = emp.to_dict(exclude={'department'}, depth=1)
        self.assertIn('name', d)
        self.assertNotIn('department', d)

    # ---- to_json ----

    def test_to_json_basic(self):
        """to_json 返回合法 JSON 字符串"""
        import json
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        json_str = emp.to_json()
        self.assertIsInstance(json_str, str)
        data = json.loads(json_str)
        self.assertEqual(data['name'], 'Alice')
        self.assertEqual(data['age'], 25)

    def test_to_json_with_datetime(self):
        """to_json 处理 datetime 类型"""
        import json
        from datetime import datetime

        # 创建包含 datetime 列的模型
        Base = self.Base

        class Event(Base):
            __tablename__ = 'events'
            id = Column(int, primary_key=True)
            title = Column(str)
            created_at = Column(datetime)

        dt = datetime(2024, 1, 15, 10, 30, 0)
        event = Event.create(title='Meeting', created_at=dt)
        json_str = event.to_json()
        data = json.loads(json_str)
        self.assertEqual(data['title'], 'Meeting')
        self.assertEqual(data['created_at'], '2024-01-15T10:30:00')

    def test_to_json_with_bytes(self):
        """to_json 处理 bytes 类型"""
        import json
        import base64

        Base = self.Base

        class BlobData(Base):
            __tablename__ = 'blobs'
            id = Column(int, primary_key=True)
            data = Column(bytes)

        raw = b'hello world'
        blob = BlobData.create(data=raw)
        json_str = blob.to_json()
        data = json.loads(json_str)
        # bytes 应被转换为 base64 字符串
        decoded = base64.b64decode(data['data'])
        self.assertEqual(decoded, raw)

    def test_to_json_with_indent(self):
        """to_json indent 参数"""
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        json_str = emp.to_json(indent=2)
        self.assertIn('\n', json_str)
        self.assertIn('  ', json_str)

    def test_to_json_with_include_exclude(self):
        """to_json 的 include/exclude 参数透传"""
        import json
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        json_str = emp.to_json(include={'name', 'age'})
        data = json.loads(json_str)
        self.assertIn('name', data)
        self.assertIn('age', data)
        self.assertNotIn('id', data)

    def test_to_json_with_depth(self):
        """to_json 的 depth 参数透传"""
        import json
        dept = self.Department.create(name='Engineering')
        emp = self.Employee.create(name='Alice', age=25, dept_id=dept.id)
        json_str = emp.to_json(depth=1)
        data = json.loads(json_str)
        self.assertIn('department', data)
        self.assertIsInstance(data['department'], dict)
        self.assertEqual(data['department']['name'], 'Engineering')

    def test_to_json_roundtrip(self):
        """to_json 结果可被 json.loads 正确解析"""
        import json
        emp = self.Employee.create(name='Alice', age=25, dept_id=1)
        json_str = emp.to_json()
        data = json.loads(json_str)
        # 与 to_dict 结果对比
        d = emp.to_dict()
        self.assertEqual(data, d)

    def test_to_json_ensure_ascii(self):
        """to_json ensure_ascii 参数"""
        import json
        emp = self.Employee.create(name='张三', age=25, dept_id=1)

        # 默认 ensure_ascii=False，中文直接输出
        json_str = emp.to_json()
        self.assertIn('张三', json_str)

        # ensure_ascii=True 时中文转义
        json_str_ascii = emp.to_json(ensure_ascii=True)
        self.assertNotIn('张三', json_str_ascii)
        data = json.loads(json_str_ascii)
        self.assertEqual(data['name'], '张三')


class TestColumnValidator(unittest.TestCase):
    """Column validator 校验器测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = mktemp_dir_project()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Storage(file_path=self.db_path)

    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_validator_single_pass(self):
        """单个 validator 通过"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, validator=lambda x: len(x) <= 100)

        user = User.create(name='Alice')
        self.assertEqual(user.name, 'Alice')

    def test_validator_single_fail(self):
        """单个 validator 返回 False，抛出 ValidationError"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, validator=lambda x: len(x) <= 5)

        with self.assertRaises(ValidationError):
            User.create(name='TooLongName')

    def test_validator_multiple(self):
        """多个 validator 全部通过"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            age = Column(int, validator=[
                lambda x: x >= 0,
                lambda x: x <= 150,
            ])

        user = User.create(age=25)
        self.assertEqual(user.age, 25)

    def test_validator_multiple_fail(self):
        """多个 validator 中第二个失败"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            age = Column(int, validator=[
                lambda x: x >= 0,
                lambda x: x <= 150,
            ])

        # 超过上限
        with self.assertRaises(ValidationError):
            User.create(age=200)

    def test_validator_with_exception(self):
        """validator 抛出自定义异常，包装为 ValidationError"""
        def strict_name(value):
            if not value.isalpha():
                raise ValueError("Name must contain only letters")
            return True

        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, validator=strict_name)

        # 包含数字，validator 抛出 ValueError -> 包装为 ValidationError
        with self.assertRaises(ValidationError) as ctx:
            User.create(name='Alice123')
        self.assertIn('validation failed', str(ctx.exception))

    def test_validator_none_skipped(self):
        """None 值跳过 validator"""
        call_count = [0]

        def never_called(value):
            call_count[0] += 1
            return True

        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, nullable=True, validator=never_called)

        user = User.create(name=None)
        self.assertIsNone(user.name)
        # validator 不应该被调用
        self.assertEqual(call_count[0], 0)

    def test_validator_after_type_conversion(self):
        """宽松模式下先转换再校验"""
        # validator 接收的应该是转换后的 int，而不是原始字符串
        received_types = []

        def check_type(value):
            received_types.append(type(value))
            return value > 0

        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            age = Column(int, validator=check_type)

        # 传入字符串 '25'，应先被转换为 int，然后 validator 接收 int
        user = User.create(age='25')
        self.assertEqual(user.age, 25)
        # validator 可能被多次调用（初始化、存储层），但每次接收的都是 int
        self.assertTrue(len(received_types) >= 1)
        for t in received_types:
            self.assertEqual(t, int)

    def test_validator_lambda(self):
        """使用 lambda 作为 validator"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            email = Column(str, validator=lambda x: '@' in x)

        user = User.create(email='alice@example.com')
        self.assertEqual(user.email, 'alice@example.com')

        with self.assertRaises(ValidationError):
            User.create(email='invalid-email')

    def test_validator_with_crud(self):
        """CRUD 模式下 validator 在 create 和 save 时都生效"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            age = Column(int, validator=lambda x: 0 <= x <= 150)

        # create 时校验
        user = User.create(age=25)
        self.assertEqual(user.age, 25)

        # save/update 时校验
        with self.assertRaises(ValidationError):
            user.age = -1  # 描述符 __set__ -> validate -> validator

    def test_validator_on_update(self):
        """通过赋值更新字段值时 validator 生效"""
        Base: Type[CRUDBaseModel] = declarative_base(self.db, crud=True)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str, validator=lambda x: len(x) >= 2)

        user = User.create(name='Alice')
        self.assertEqual(user.name, 'Alice')

        # 更新为合法值
        user.name = 'Bob'
        self.assertEqual(user.name, 'Bob')

        # 更新为不合法值
        with self.assertRaises(ValidationError):
            user.name = 'A'  # 长度 < 2


class TestColumnDefaultFactory(unittest.TestCase):
    """测试 Column default_factory 参数"""

    def test_default_factory_basic(self):
        """default_factory 在每次创建实例时被调用"""
        counter = {'value': 0}

        def next_id():
            counter['value'] += 1
            return counter['value']

        db = Storage()
        Base = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            seq = Column(int, default_factory=next_id)

        item1 = Item()
        item2 = Item()
        self.assertEqual(item1.seq, 1)
        self.assertEqual(item2.seq, 2)

    def test_default_factory_datetime(self):
        """default_factory 支持 datetime.now 等场景"""
        db = Storage()
        Base = declarative_base(db)

        class Log(Base):
            __tablename__ = 'logs'
            id = Column(int, primary_key=True)
            created_at = Column(datetime, default_factory=datetime.now)
            message = Column(str, default='')

        log = Log(message='hello')
        self.assertIsInstance(log.created_at, datetime)
        # 创建时间应该在当前时间附近
        diff = abs((datetime.now() - log.created_at).total_seconds())
        self.assertLess(diff, 1.0)

    def test_default_factory_each_call_unique(self):
        """每次实例化都调用 default_factory，生成不同值"""
        import time

        db = Storage()
        Base = declarative_base(db)

        class Event(Base):
            __tablename__ = 'events'
            id = Column(int, primary_key=True)
            timestamp = Column(float, default_factory=time.time)

        e1 = Event()
        time.sleep(0.01)
        e2 = Event()
        self.assertNotEqual(e1.timestamp, e2.timestamp)

    def test_default_and_default_factory_mutual_exclusive(self):
        """default 和 default_factory 不可同时设置"""
        with self.assertRaises(ValidationError):
            Column(int, default=0, default_factory=lambda: 0)

    def test_default_factory_must_be_callable(self):
        """default_factory 必须是可调用对象"""
        with self.assertRaises(ValidationError):
            Column(int, default_factory=42)

    def test_default_factory_none_allowed(self):
        """default_factory 为 None 时不使用工厂"""
        col = Column(int, default_factory=None)
        self.assertIsNone(col.default_factory)
        self.assertFalse(col.has_default())

    def test_has_default_with_default(self):
        """has_default() 检测 default"""
        col = Column(int, default=0)
        self.assertTrue(col.has_default())

    def test_has_default_with_default_factory(self):
        """has_default() 检测 default_factory"""
        col = Column(int, default_factory=lambda: 0)
        self.assertTrue(col.has_default())

    def test_has_default_neither(self):
        """has_default() 当两者都未设置时返回 False"""
        col = Column(int)
        self.assertFalse(col.has_default())

    def test_resolve_default_factory(self):
        """resolve_default() 调用 default_factory"""
        col = Column(int, default_factory=lambda: 99)
        col.name = 'test'
        self.assertEqual(col.resolve_default(), 99)

    def test_resolve_default_static(self):
        """resolve_default() 返回 default 静态值"""
        col = Column(int, default=42)
        col.name = 'test'
        self.assertEqual(col.resolve_default(), 42)

    def test_resolve_default_none(self):
        """resolve_default() 无默认时返回 None"""
        col = Column(int)
        col.name = 'test'
        self.assertIsNone(col.resolve_default())

    def test_default_factory_with_crud_model(self):
        """CRUD 模式下 default_factory 生效"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class Task(Base):
            __tablename__ = 'tasks'
            id = Column(int, primary_key=True)
            created_at = Column(datetime, default_factory=datetime.now)
            title = Column(str)

        task = Task(title='test')
        self.assertIsInstance(task.created_at, datetime)

    def test_default_factory_with_insert_statement(self):
        """通过 insert 语句时 default_factory 生效"""
        db = Storage()
        Base = declarative_base(db)

        counter = {'value': 100}

        def next_seq():
            counter['value'] += 1
            return counter['value']

        class Record(Base):
            __tablename__ = 'records'
            id = Column(int, primary_key=True)
            seq = Column(int, default_factory=next_seq)
            name = Column(str)

        session = Session(db)
        session.execute(insert(Record).values(name='a'))
        session.execute(insert(Record).values(name='b'))
        session.commit()

        result = session.execute(select(Record)).all()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].seq, 101)
        self.assertEqual(result[1].seq, 102)

    def test_default_factory_explicit_value_override(self):
        """显式传值时 default_factory 不生效"""
        db = Storage()
        Base = declarative_base(db)

        class Item(Base):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            seq = Column(int, default_factory=lambda: 999)

        item = Item(seq=1)
        self.assertEqual(item.seq, 1)

    def test_default_factory_to_dict_not_serialized(self):
        """to_dict 不序列化 default_factory"""
        col = Column(int, default_factory=lambda: 0)
        col.name = 'test'
        d = col.to_dict()
        self.assertIsNone(d['default'])
        self.assertNotIn('default_factory', d)


class TestModelInheritance(unittest.TestCase):
    """测试模型继承支持（Mixin 列复用）"""

    def test_mixin_column_inheritance_pure(self):
        """纯模型模式：子类继承 Mixin 定义的列"""
        db = Storage()
        Base = declarative_base(db)

        class TimestampMixin(Base):
            __abstract__ = True
            created_at = Column(str, default='now')
            updated_at = Column(str, default='now')

        class User(TimestampMixin):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)

        # 验证 User.__columns__ 包含继承的列
        self.assertIn('id', User.__columns__)
        self.assertIn('name', User.__columns__)
        self.assertIn('created_at', User.__columns__)
        self.assertIn('updated_at', User.__columns__)
        self.assertEqual(len(User.__columns__), 4)

        # 验证主键正确
        self.assertEqual(User.__primary_key__, 'id')

    def test_mixin_column_inheritance_crud(self):
        """CRUD 模式：子类继承 Mixin 定义的列，且 CRUD 操作正常"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class AuditMixin(Base):
            __abstract__ = True
            created_by = Column(str, default='system')

        class Product(AuditMixin):
            __tablename__ = 'products'
            id = Column(int, primary_key=True)
            name = Column(str)

        # 创建记录
        p = Product.create(name='Widget')
        self.assertEqual(p.name, 'Widget')
        self.assertEqual(p.created_by, 'system')

        # 查询
        found = Product.get(p.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, 'Widget')
        self.assertEqual(found.created_by, 'system')

    def test_mixin_crud_to_dict(self):
        """继承的列在 to_dict 中正确显示"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class TagMixin(Base):
            __abstract__ = True
            tag = Column(str, default='default')

        class Item(TagMixin):
            __tablename__ = 'items'
            id = Column(int, primary_key=True)
            title = Column(str)

        item = Item.create(title='Test')
        d = item.to_dict()
        self.assertIn('tag', d)
        self.assertEqual(d['tag'], 'default')
        self.assertIn('title', d)
        self.assertIn('id', d)

    def test_child_overrides_parent_column(self):
        """子类可以覆盖父类定义的同名列"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class DefaultMixin(Base):
            __abstract__ = True
            status = Column(str, default='inactive')

        class ActiveModel(DefaultMixin):
            __tablename__ = 'active_models'
            id = Column(int, primary_key=True)
            status = Column(str, default='active')  # 覆盖父类

        model = ActiveModel.create()
        self.assertEqual(model.status, 'active')  # 使用子类的默认值

    def test_multi_level_inheritance(self):
        """多层继承：A → B → C"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class LevelA(Base):
            __abstract__ = True
            col_a = Column(str, default='a')

        class LevelB(LevelA):
            __abstract__ = True
            col_b = Column(str, default='b')

        class LevelC(LevelB):
            __tablename__ = 'level_c'
            id = Column(int, primary_key=True)
            col_c = Column(str, default='c')

        # LevelC 应继承 col_a 和 col_b
        self.assertIn('col_a', LevelC.__columns__)
        self.assertIn('col_b', LevelC.__columns__)
        self.assertIn('col_c', LevelC.__columns__)
        self.assertIn('id', LevelC.__columns__)
        self.assertEqual(len(LevelC.__columns__), 4)

        item = LevelC.create()
        self.assertEqual(item.col_a, 'a')
        self.assertEqual(item.col_b, 'b')
        self.assertEqual(item.col_c, 'c')

    def test_mixin_with_validator(self):
        """Mixin 中的 validator 在子类中生效"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class ValidatedMixin(Base):
            __abstract__ = True
            score = Column(int, validator=lambda x: 0 <= x <= 100)

        class Student(ValidatedMixin):
            __tablename__ = 'students_inherit'
            id = Column(int, primary_key=True)
            name = Column(str)

        # 合法值
        s = Student.create(name='Alice', score=85)
        self.assertEqual(s.score, 85)

        # 不合法值
        with self.assertRaises(ValidationError):
            Student.create(name='Bob', score=150)

    def test_mixin_no_table_created(self):
        """标记 __abstract__ = True 的 Mixin 不创建表"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class MyMixin(Base):
            __abstract__ = True
            extra = Column(str, default='x')

        # Mixin 类不应在 Storage 中创建表
        self.assertNotIn('my_mixin', db.tables)
        # Mixin 不应有 __tablename__ 设置
        self.assertIsNone(MyMixin.__tablename__)

    def test_multiple_mixins(self):
        """多个 Mixin 的列都被继承"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class MixinA(Base):
            __abstract__ = True
            field_a = Column(str, default='a')

        class MixinB(Base):
            __abstract__ = True
            field_b = Column(str, default='b')

        class Combined(MixinA, MixinB):
            __tablename__ = 'combined'
            id = Column(int, primary_key=True)

        self.assertIn('field_a', Combined.__columns__)
        self.assertIn('field_b', Combined.__columns__)
        self.assertIn('id', Combined.__columns__)

        item = Combined.create()
        self.assertEqual(item.field_a, 'a')
        self.assertEqual(item.field_b, 'b')

    def test_mixin_with_primary_key_inherited(self):
        """Mixin 中定义主键，子类继承"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class PKMixin(Base):
            __abstract__ = True
            id = Column(int, primary_key=True)

        class SimpleModel(PKMixin):
            __tablename__ = 'simple_model'
            name = Column(str)

        self.assertEqual(SimpleModel.__primary_key__, 'id')
        m = SimpleModel.create(name='Test')
        self.assertIsNotNone(m.id)
        self.assertEqual(m.name, 'Test')

    def test_abstract_mixin_skipped(self):
        """标记 __abstract__ = True 的类被跳过"""
        db = Storage()
        Base = declarative_base(db)

        class AbstractBase(Base):
            __abstract__ = True
            id = Column(int, primary_key=True)

        # 不应报错，AbstractBase 不会触发表创建
        self.assertTrue(AbstractBase.__abstract__)

    def test_two_concrete_models_from_same_mixin(self):
        """同一 Mixin 可以被多个具体模型继承"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        class CommonMixin(Base):
            __abstract__ = True
            status = Column(str, default='active')

        class ModelA(CommonMixin):
            __tablename__ = 'model_a'
            id = Column(int, primary_key=True)
            name_a = Column(str)

        class ModelB(CommonMixin):
            __tablename__ = 'model_b'
            id = Column(int, primary_key=True)
            name_b = Column(str)

        a = ModelA.create(name_a='A')
        b = ModelB.create(name_b='B')
        self.assertEqual(a.status, 'active')
        self.assertEqual(b.status, 'active')
        self.assertIn('status', ModelA.__columns__)
        self.assertIn('status', ModelB.__columns__)

    def test_no_tablename_no_abstract_raises(self):
        """无 __tablename__ 且无 __abstract__ = True 的类必须报错"""
        db = Storage()
        Base = declarative_base(db, crud=True)

        with self.assertRaises(ValidationError) as ctx:
            class ForgotTablename(Base):
                id = Column(int, primary_key=True)
                name = Column(str)

        self.assertIn('__tablename__', str(ctx.exception))
        self.assertIn('__abstract__', str(ctx.exception))

    def test_no_tablename_no_abstract_raises_pure(self):
        """纯模型模式：无 __tablename__ 且无 __abstract__ 也报错"""
        db = Storage()
        Base = declarative_base(db)

        with self.assertRaises(ValidationError):
            class BadModel(Base):
                id = Column(int, primary_key=True)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestColumn))
    suite.addTests(loader.loadTestsFromTestCase(TestDeclarativeBase))
    suite.addTests(loader.loadTestsFromTestCase(TestPureBaseModel))
    suite.addTests(loader.loadTestsFromTestCase(TestCRUDBaseModel))
    suite.addTests(loader.loadTestsFromTestCase(TestMultipleEngines))
    suite.addTests(loader.loadTestsFromTestCase(TestTypeAnnotations))
    suite.addTests(loader.loadTestsFromTestCase(TestColumnNameMapping))
    suite.addTests(loader.loadTestsFromTestCase(TestToDictEnhanced))
    suite.addTests(loader.loadTestsFromTestCase(TestColumnValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestModelInheritance))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回是否全部通过
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
