"""
Pytuck 泛型类型提示演示

这个示例演示了 Pytuck ORM 的泛型类型系统如何改善 IDE 支持和开发体验。

在支持类型提示的 IDE 中（如 PyCharm、VSCode），您将看到：
1. 精确的类型推断：select(User) → Select[User]
2. 智能代码补全：result.all() → list[User]
3. 属性访问提示：user.name, user.age 等
4. 类型错误检测：编译时发现类型不匹配
"""

import os
from pytuck import Storage, declarative_base, Session, Column
from pytuck import select, insert, update, delete

def main() -> None:
    """演示泛型类型系统的各种用法"""

    # 设置数据库
    db = Storage('typing_demo.db', auto_flush=True)
    Base = declarative_base(db)

    class User(Base):
        __tablename__ = 'users'
        id = Column(int, primary_key=True)
        name = Column(str)
        age = Column(int)
        email = Column(str)

    # 创建会话
    session = Session(db)

    print("=== Pytuck 泛型类型提示演示 ===\n")

    # 1. 语句构建阶段的类型推断
    print("1. 语句构建阶段")
    select_stmt = select(User)  # IDE 推断：Select[User] ✅
    print(f"   select(User) → {type(select_stmt)}")

    insert_stmt = insert(User).values(
        name='Alice',
        age=25,
        email='alice@example.com'
    )  # IDE 推断：Insert[User] ✅
    print(f"   insert(User) → {type(insert_stmt)}")

    # 2. 链式调用保持类型
    print("\n2. 链式调用类型保持")
    chained_stmt = (select_stmt
                    .where(User.age >= 18)  # Select[User]
                    .order_by('name')       # Select[User]
                    .limit(10))            # Select[User]
    print(f"   链式调用结果 → {type(chained_stmt)}")

    # 3. 会话执行的精确类型推断
    print("\n3. 会话执行类型推断")

    # 插入数据
    insert_result = session.execute(insert_stmt)  # IDE 推断：CursorResult[User] ✅
    print(f"   session.execute(insert) → {type(insert_result)}")
    print(f"   插入的主键: {insert_result.inserted_primary_key}")

    # 再插入几条数据用于演示
    for name, age in [('Bob', 30), ('Charlie', 22), ('Diana', 27)]:
        session.execute(insert(User).values(name=name, age=age, email=f'{name.lower()}@example.com'))

    # 查询数据
    result = session.execute(chained_stmt)  # IDE 推断：Result[User] ✅
    print(f"   session.execute(select) → {type(result)}")

    # 4. 结果处理的精确类型
    print("\n4. 结果处理精确类型")

    # 直接从 Result 提取模型列表或单个模型（不再使用 Result）
    users = result.all()  # IDE 推断：list[User] ✅
    print(f"   result.all() → {type(users)} (元素类型: {type(users[0]) if users else 'N/A'})")

    first_user = result.first()  # IDE 推断：User | None ✅
    print(f"   result.first() → 类型是 User | None")

    # 5. 类型安全的属性访问
    print("\n5. 类型安全的属性访问")
    print("   用户列表:")
    for user in users:
        # IDE 知道 user 是 User 类型，提供精确的属性提示
        user_name: str = user.name  # ✅ IDE 知道这是 str
        user_age: int = user.age    # ✅ IDE 知道这是 int
        user_email: str = user.email  # ✅ IDE 知道这是 str
        print(f"     - {user_name} (年龄: {user_age}, 邮箱: {user_email})")

    # 6. Session.get 的类型推断
    print("\n6. Session.get 类型推断")
    if users:
        found_user = session.get(User, users[0].id)  # IDE 推断：User | None ✅
        if found_user:
            print(f"   通过主键找到用户: {found_user.name}")

    # 7. 更新和删除的类型推断
    print("\n7. 更新和删除操作")

    if users:
        # 更新操作
        update_stmt = update(User).where(User.name == 'Alice').values(age=26)  # Update[User]
        update_result = session.execute(update_stmt)  # CursorResult[User]
        print(f"   更新了 {update_result.rowcount()} 条记录")

        # 删除操作
        delete_stmt = delete(User).where(User.age < 20)  # Delete[User]
        delete_result = session.execute(delete_stmt)  # CursorResult[User]
        print(f"   删除了 {delete_result.rowcount()} 条记录")

    # 8. 复杂查询的类型保持
    print("\n8. 复杂查询类型保持")

    complex_users = (session
                     .execute(
                         select(User)
                         .where(User.age >= 25)
                         .order_by('name', desc=True)
                         .limit(5)
                     )
                     .all())  # IDE 推断：list[User] ✅

    print(f"   复杂查询结果: {len(complex_users)} 个用户")

    # 9. 类型错误示例（这些在 IDE 中会显示错误）
    print("\n9. 类型检查能力演示")
    print("   以下代码在 IDE 中会显示类型错误:")
    print("   # user_direct: User = result.first()  # ❌ 可能是 None")
    print("   # wrong_type: str = result.all()      # ❌ 类型不匹配")
    print("   # user.nonexistent_field                         # ❌ 属性不存在")

    print("\n=== 演示完成 ===")
    print("\n🎉 现在您可以享受到:")
    print("   ✅ 精确的类型推断 (Select[User], Result[User], list[User])")
    print("   ✅ 智能代码补全 (IDE 知道所有属性和方法)")
    print("   ✅ 编译时类型检查 (mypy 可以发现类型错误)")
    print("   ✅ 更好的开发体验 (清晰的 API 文档)")

    # 清理数据库
    db.close()

def demonstrate_type_inference() -> None:
    """演示类型推断的具体效果"""

    db = Storage('type_inference_demo.db')
    Base = declarative_base(db)

    class Product(Base):
        __tablename__ = 'products'
        id = Column(int, primary_key=True)
        name = Column(str)
        price = Column(float)
        in_stock = Column(bool)

    session = Session(db)

    print("\n=== 类型推断详细演示 ===")

    # 语句构建器的类型推断
    stmt = select(Product)  # Select[Product]
    filtered = stmt.where(Product.price > 100.0)  # Select[Product]
    ordered = filtered.order_by('name')  # Select[Product]

    print("语句构建器类型链:")
    print(f"  select(Product) → 推断类型: Select[Product]")
    print(f"  .where(...)     → 推断类型: Select[Product]")
    print(f"  .order_by(...)  → 推断类型: Select[Product]")

    # 执行和结果的类型推断
    result = session.execute(ordered)  # Result[Product]
    # 直接从 Result 提取产品列表
    products = result.all()  # list[Product]

    print("\n结果处理类型链:")
    print(f"  session.execute(stmt) → 推断类型: Result[Product]")
    print(f"  result.all()          → 推断类型: list[Product] ✅")

    print("\n这意味着:")
    print("  - IDE 自动完成会显示 Product 的所有属性")
    print("  - mypy 会检查类型错误")
    print("  - 代码更安全，bug 更少")

    # 清理数据库
    db.close()

def cleanup_demo_files() -> None:
    """清理演示文件"""
    files_to_remove = ['typing_demo.db', 'type_inference_demo.db']
    for filename in files_to_remove:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"✓ 已清理: {filename}")

if __name__ == '__main__':
    try:
        main()
        demonstrate_type_inference()
    finally:
        cleanup_demo_files()