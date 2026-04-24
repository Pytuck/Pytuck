"""
Pytuck - JSON后端实现选择演示

演示Pytuck 0.3.0版本的新特性：
- 支持标准库 json、orjson 和自定义 JSON 实现
- 用户指定库优先，参数智能适配
- 自定义JSON实现扩展机制
"""

import sys
import time
from pathlib import Path
from typing import Type

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples._common import get_project_temp_dir

from pytuck import Storage, declarative_base, Session, Column, PureBaseModel
from pytuck import select, insert
from pytuck.common.options import JsonBackendOptions
from pytuck.common.exceptions import ConfigurationError
from pytuck.backends.backend_json import JSONBackend

def demo_performance_comparison():
    """演示不同JSON实现的性能对比"""
    print("=" * 60)
    print("JSON实现性能对比演示")
    print("=" * 60)

    # 创建临时目录
    temp_dir = get_project_temp_dir()

    try:
        # 准备测试数据
        test_data = [
            {'name': f'用户{i}', 'description': '这是一个测试用户的详细描述信息' * 10}
            for i in range(1000)
        ]

        print(f"测试数据：{len(test_data)} 条记录")
        print("-" * 50)

        # 测试标准库json
        print("1. 标准库 json 性能测试")
        json_file = os.path.join(temp_dir, 'perf_json.json')
        json_opts = JsonBackendOptions(impl='json', indent=2)

        start_time = time.time()
        db_json = Storage(file_path=json_file, engine='json', backend_options=json_opts)
        Base: Type[PureBaseModel] = declarative_base(db_json)

        class JsonUser(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            description = Column(str)

        session_json = Session(db_json)
        for data in test_data:
            stmt = insert(JsonUser).values(**data)
            session_json.execute(stmt)
        session_json.commit()
        db_json.flush()  # 强制写入磁盘

        json_write_time = time.time() - start_time
        file_size_json = os.path.getsize(json_file)

        print(f"   写入时间: {json_write_time:.3f}s")
        print(f"   文件大小: {file_size_json:,} bytes")
        print(f"   JSON实现: {db_json.backend._impl_name}")

        session_json.close()
        db_json.close()

        # 测试orjson（如果可用）
        try:
            import orjson
            print("\n2. orjson 性能测试")
            orjson_file = os.path.join(temp_dir, 'perf_orjson.json')
            orjson_opts = JsonBackendOptions(impl='orjson', indent=2)  # indent会被舍弃

            start_time = time.time()
            db_orjson = Storage(file_path=orjson_file, engine='json', backend_options=orjson_opts)
            Base_orjson: Type[PureBaseModel] = declarative_base(db_orjson)

            class OrjsonUser(Base_orjson):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)
                description = Column(str)

            session_orjson = Session(db_orjson)
            for data in test_data:
                stmt = insert(OrjsonUser).values(**data)
                session_orjson.execute(stmt)
            session_orjson.commit()
            db_orjson.flush()  # 强制写入磁盘

            orjson_write_time = time.time() - start_time
            file_size_orjson = os.path.getsize(orjson_file)

            print(f"   写入时间: {orjson_write_time:.3f}s")
            print(f"   文件大小: {file_size_orjson:,} bytes")
            print(f"   JSON实现: {db_orjson.backend._impl_name}")
            print(f"   性能提升: {json_write_time/orjson_write_time:.1f}x 更快")

            session_orjson.close()
            db_orjson.close()

        except ImportError:
            print("\n2. orjson 未安装，跳过性能测试")
            print("   安装方法: pip install pytuck[orjson]")


    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def demo_parameter_handling():
    """演示参数处理机制"""
    print("\n" + "=" * 60)
    print("JSON参数处理演示")
    print("=" * 60)

    temp_dir = get_project_temp_dir()

    try:
        print("1. 标准库json - 完整参数支持")
        json_opts = JsonBackendOptions(impl='json', indent=4, ensure_ascii=True)
        json_file = os.path.join(temp_dir, 'param_json.json')

        db = Storage(file_path=json_file, engine='json', backend_options=json_opts)
        Base: Type[PureBaseModel] = declarative_base(db)

        class User(Base):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            unicode_text = Column(str)

        session = Session(db)
        stmt = insert(User).values(name='测试', unicode_text='中文测试 🎉')
        session.execute(stmt)
        session.commit()

        backend = db.backend
        print(f"   JSON实现: {backend._impl_name}")
        print(f"   indent参数: {json_opts.indent} (已应用)")
        print(f"   ensure_ascii参数: {json_opts.ensure_ascii} (已应用)")
        print("   ✓ 所有参数均被标准库json支持")

        session.close()
        db.close()

        # 测试orjson参数舍弃
        try:
            import orjson
            print("\n2. orjson - 参数自动舍弃")
            orjson_opts = JsonBackendOptions(impl='orjson', indent=4, ensure_ascii=True)
            orjson_file = os.path.join(temp_dir, 'param_orjson.json')

            db_orjson = Storage(file_path=orjson_file, engine='json', backend_options=orjson_opts)
            Base_orjson: Type[PureBaseModel] = declarative_base(db_orjson)

            class OrjsonUser(Base_orjson):
                __tablename__ = 'users'
                id = Column(int, primary_key=True)
                name = Column(str)
                unicode_text = Column(str)

            session_orjson = Session(db_orjson)
            stmt = insert(OrjsonUser).values(name='测试', unicode_text='中文测试 🎉')
            session_orjson.execute(stmt)
            session_orjson.commit()
            db_orjson.flush()  # 强制写入磁盘

            backend_orjson = db_orjson.backend
            print(f"   JSON实现: {backend_orjson._impl_name}")
            print(f"   indent参数: {orjson_opts.indent} (被舍弃，不影响功能)")
            print(f"   ensure_ascii参数: {orjson_opts.ensure_ascii} (被舍弃，不影响功能)")
            print("   ✓ 参数舍弃后仍正常工作，获得最佳性能")

            session_orjson.close()
            db_orjson.close()

        except ImportError:
            print("\n2. orjson 未安装，跳过参数处理演示")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def demo_custom_implementation():
    """演示自定义JSON实现"""
    print("\n" + "=" * 60)
    print("自定义JSON实现演示")
    print("=" * 60)

    temp_dir = get_project_temp_dir()

    try:
        # 保存原始方法
        original_setup_custom = JSONBackend._setup_custom_json

        def setup_compact_json(self, impl):
            """自定义紧凑JSON实现（无缩进，紧凑分隔符）"""
            import json

            def dumps_func(obj):
                return json.dumps(obj, separators=(',', ':'), ensure_ascii=False)

            self._dumps_func = dumps_func
            self._loads_func = json.loads
            self._impl_name = f'compact_{impl}'

        def setup_pretty_json(self, impl):
            """自定义美化JSON实现（大缩进，彩色输出模拟）"""
            import json

            def dumps_func(obj):
                return json.dumps(obj, indent=6, separators=(', ', ': '), ensure_ascii=False)

            self._dumps_func = dumps_func
            self._loads_func = json.loads
            self._impl_name = f'pretty_{impl}'

        # 演示1：紧凑JSON
        print("1. 自定义紧凑JSON实现")
        JSONBackend._setup_custom_json = setup_compact_json

        compact_opts = JsonBackendOptions(impl='compact')
        compact_file = os.path.join(temp_dir, 'custom_compact.json')

        db_compact = Storage(file_path=compact_file, engine='json', backend_options=compact_opts)
        Base_compact: Type[PureBaseModel] = declarative_base(db_compact)

        class CompactUser(Base_compact):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            data = Column(str)

        session_compact = Session(db_compact)
        stmt = insert(CompactUser).values(name='紧凑用户', data='紧凑数据存储')
        session_compact.execute(stmt)
        session_compact.commit()
        db_compact.flush()  # 确保数据写入磁盘

        backend_compact = db_compact.backend
        print(f"   JSON实现: {backend_compact._impl_name}")
        print(f"   特点: 无缩进、紧凑分隔符、文件最小化")

        file_size = os.path.getsize(compact_file)
        print(f"   文件大小: {file_size} bytes")

        session_compact.close()
        db_compact.close()

        # 演示2：美化JSON
        print("\n2. 自定义美化JSON实现")
        JSONBackend._setup_custom_json = setup_pretty_json

        pretty_opts = JsonBackendOptions(impl='pretty')
        pretty_file = os.path.join(temp_dir, 'custom_pretty.json')

        db_pretty = Storage(file_path=pretty_file, engine='json', backend_options=pretty_opts)
        Base_pretty: Type[PureBaseModel] = declarative_base(db_pretty)

        class PrettyUser(Base_pretty):
            __tablename__ = 'users'
            id = Column(int, primary_key=True)
            name = Column(str)
            data = Column(str)

        session_pretty = Session(db_pretty)
        stmt = insert(PrettyUser).values(name='美化用户', data='美化数据存储')
        session_pretty.execute(stmt)
        session_pretty.commit()
        db_pretty.flush()  # 确保数据写入磁盘

        backend_pretty = db_pretty.backend
        print(f"   JSON实现: {backend_pretty._impl_name}")
        print(f"   特点: 6空格缩进、美化分隔符、可读性强")

        file_size = os.path.getsize(pretty_file)
        print(f"   文件大小: {file_size} bytes")

        session_pretty.close()
        db_pretty.close()

        # 显示文件内容对比
        print("\n3. 文件内容对比")
        print("紧凑格式预览:")
        with open(compact_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')[:3]
            for line in lines:
                print(f"   {line[:60]}...")

        print("\n美化格式预览:")
        with open(pretty_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')[:6]
            for line in lines:
                print(f"   {line}")

    finally:
        # 恢复原始方法
        JSONBackend._setup_custom_json = original_setup_custom
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def demo_error_handling():
    """演示错误处理机制"""
    print("\n" + "=" * 60)
    print("错误处理演示")
    print("=" * 60)

    temp_dir = get_project_temp_dir()

    try:
        # 1. 测试不存在的库
        print("1. 不存在的JSON库处理")
        try:
            opts = JsonBackendOptions(impl='nonexistent_lib')
            db = Storage(file_path=os.path.join(temp_dir, 'error.json'),
                        engine='json', backend_options=opts)
            print("   ❌ 应该抛出错误")
        except NotImplementedError as e:
            print(f"   ✓ 正确抛出 NotImplementedError")
            print(f"   错误信息: {str(e)[:80]}...")

        # 2. 测试缺少可选依赖
        print("\n2. 缺少可选依赖处理")

        # 模拟orjson不可用的情况
        import sys
        original_modules = sys.modules.copy()
        if 'orjson' in sys.modules:
            del sys.modules['orjson']

        # 临时替换__import__来模拟ImportError
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'orjson':
                raise ImportError("No module named 'orjson'")
            return original_import(name, *args, **kwargs)

        try:
            builtins.__import__ = mock_import

            opts = JsonBackendOptions(impl='orjson')
            db = Storage(file_path=os.path.join(temp_dir, 'error2.json'),
                        engine='json', backend_options=opts)
            print("   ❌ 应该抛出 ImportError")
        except ImportError as e:
            print(f"   ✓ 正确抛出 ImportError")
            print(f"   错误信息: {str(e)}")
            if "pip install" in str(e):
                print("   ✓ 包含安装指导信息")
        finally:
            # 恢复
            builtins.__import__ = original_import
            sys.modules.update(original_modules)

        # 3. 测试自定义实现错误
        print("\n3. 自定义实现错误处理")

        def faulty_custom_setup(self, impl):
            """错误的自定义设置，缺少必要属性"""
            self._dumps_func = lambda x: "test"
            # 故意不设置 _loads_func 和 _impl_name

        original_setup = JSONBackend._setup_custom_json
        JSONBackend._setup_custom_json = faulty_custom_setup

        try:
            opts = JsonBackendOptions(impl='faulty')
            db = Storage(file_path=os.path.join(temp_dir, 'error3.json'),
                        engine='json', backend_options=opts)
            print("   ❌ 应该抛出验证错误")
        except (ValueError, ConfigurationError) as e:
            print(f"   ✓ 正确检测到属性缺失")
            print(f"   错误信息: {str(e)}")
        finally:
            JSONBackend._setup_custom_json = original_setup

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    """主演示函数"""
    print("Pytuck JSON后端实现选择演示")
    print("支持标准库 json、orjson 和自定义实现")
    print()

    # 运行所有演示
    demo_performance_comparison()
    demo_parameter_handling()
    demo_custom_implementation()
    demo_error_handling()

    print("\n" + "=" * 60)
    print("演示总结")
    print("=" * 60)
    print("✅ 多种JSON实现支持：orjson (高性能)、json (标准)")
    print("✅ 用户指定库优先：指定什么库就用什么库，不自动回退")
    print("✅ 智能参数处理：不兼容的参数自动舍弃，不影响功能")
    print("✅ 自定义实现扩展：通过覆盖方法支持任意JSON库")
    print("✅ 完整错误处理：清晰的错误信息和安装指导")

    print("\n使用建议:")
    print("🚀 高性能场景: JsonBackendOptions(impl='orjson')")
    print("🔧 调试友好: JsonBackendOptions(impl='json', indent=4)")
    print("🎨 自定义需求: 覆盖 JSONBackend._setup_custom_json 方法")

    print(f"\n安装方法:")
    print("pip install pytuck[orjson]  # 安装orjson支持")

if __name__ == '__main__':
    main()