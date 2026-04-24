"""
跨 storage Relationship 行为测试

覆盖两类现状：
1. 直接使用模型类作为目标时，跨 storage 懒加载当前可工作
2. 使用字符串表名并显式指定目标 storage 时，当前仍存在支持缺口
"""

from pathlib import Path
from typing import Callable

import pytest

from pytuck import Column, CRUDBaseModel, Session, Storage, ValidationError, declarative_base, prefetch, select
from pytuck.backends import BackendRegistry
from pytuck.core.orm import Relationship


ENGINE_EXTENSIONS = {
    "json": "json",
    "sqlite": "sqlite",
    "duckdb": "duckdb",
    "pytuck": "pytuck",
}

ENGINE_PAIRS = [
    ("sqlite", "json"),
    ("duckdb", "pytuck"),
]


def is_engine_available(engine_name: str) -> bool:
    """检查引擎是否可用。"""
    backend_class = BackendRegistry.get(engine_name)
    return backend_class is not None and backend_class.is_available()


@pytest.fixture(params=ENGINE_PAIRS, ids=lambda pair: f"{pair[0]}-{pair[1]}")
def engine_pair(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[Storage, Storage, tuple[str, str]]:
    """提供一对异构存储。"""
    product_engine, favorite_engine = request.param

    if not is_engine_available(product_engine):
        pytest.skip(f"引擎 {product_engine} 不可用")
    if not is_engine_available(favorite_engine):
        pytest.skip(f"引擎 {favorite_engine} 不可用")

    product_path = tmp_path / f"products.{ENGINE_EXTENSIONS[product_engine]}"
    favorite_path = tmp_path / f"favorites.{ENGINE_EXTENSIONS[favorite_engine]}"

    product_db = Storage(file_path=product_path, engine=product_engine)
    favorite_db = Storage(file_path=favorite_path, engine=favorite_engine)

    try:
        yield product_db, favorite_db, request.param
    finally:
        favorite_db.close()
        product_db.close()


def build_cross_storage_models(
    product_db: Storage,
    favorite_db: Storage,
    *,
    use_string_target: bool = False,
    target_storage: Storage | None = None,
) -> tuple[type[CRUDBaseModel], type[CRUDBaseModel]]:
    """构造跨 storage 的产品与收藏模型。"""
    ProductBase = declarative_base(product_db, crud=True)
    FavoriteBase = declarative_base(favorite_db, crud=True)

    class Product(ProductBase):
        __tablename__ = "products"

        id = Column(int, primary_key=True)
        name = Column(str)

    product_relationship_kwargs: dict[str, object] = {"foreign_key": "product_id"}
    product_relationship_target: str | type[CRUDBaseModel]

    if use_string_target:
        product_relationship_target = "products"
        if target_storage is not None:
            product_relationship_kwargs["storage"] = target_storage
    else:
        product_relationship_target = Product

    class UserFavorite(FavoriteBase):
        __tablename__ = "favorites"

        id = Column(int, primary_key=True)
        user_id = Column(int)
        product_id = Column(int)
        product = Relationship(  # type: ignore[call-arg]
            product_relationship_target,
            **product_relationship_kwargs,
        )

    attach_reverse_relationship_for_test(
        owner_model=Product,
        relationship_name="favorites",
        relationship=Relationship(UserFavorite, foreign_key="product_id", uselist=True),
    )

    return Product, UserFavorite


def attach_reverse_relationship_for_test(
    *,
    owner_model: type[CRUDBaseModel],
    relationship_name: str,
    relationship: Relationship,
) -> None:
    """
    为测试场景挂载反向关系。

    这里封装对 `__relationships__` 和 `__set_name__()` 的直接操作，
    仅用于构造跨 storage 反向懒加载测试场景，便于覆盖当前行为；
    这不是公共 API 的推荐用法。
    """
    owner_model.__relationships__[relationship_name] = relationship
    setattr(owner_model, relationship_name, relationship)
    relationship.__set_name__(owner_model, relationship_name)


def assert_only_missing_storage_parameter_gap(
    build_models: Callable[[], None],
    *,
    source_engine: str,
    target_engine: str,
) -> None:
    """
    只锁定当前已知缺口：`Relationship(..., storage=...)` 尚不被支持。

    如果出现其他 TypeError，应直接抛出，避免把无关错误误判为同一缺口。
    """
    try:
        build_models()
    except TypeError as exc:
        message = str(exc)
        if "unexpected keyword argument 'storage'" not in message:
            raise
        pytest.fail(
            "跨 storage 字符串目标解析尚未支持："
            f"{source_engine} -> {target_engine} 的 Relationship 仍无法接收 storage 参数。"
            f"原始错误: {message}"
        )


def test_cross_storage_many_to_one_lazy_load(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """跨 storage 多对一懒加载应能通过模型类目标工作。"""
    product_db, favorite_db, _ = engine_pair
    Product, UserFavorite = build_cross_storage_models(product_db, favorite_db)

    product = Product.create(name="Widget")
    favorite = UserFavorite.create(user_id=1, product_id=product.id)

    reloaded_favorite = UserFavorite.get(favorite.id)
    assert reloaded_favorite is not None

    loaded_product = reloaded_favorite.product
    assert loaded_product is not None
    assert loaded_product.id == product.id
    assert loaded_product.name == "Widget"
    assert reloaded_favorite.product is loaded_product


def test_cross_storage_one_to_many_lazy_load(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """跨 storage 一对多懒加载应能通过模型类目标工作。"""
    product_db, favorite_db, _ = engine_pair
    Product, UserFavorite = build_cross_storage_models(product_db, favorite_db)

    product = Product.create(name="Widget")
    UserFavorite.create(user_id=10, product_id=product.id)
    UserFavorite.create(user_id=11, product_id=product.id)

    reloaded_product = Product.get(product.id)
    assert reloaded_product is not None

    favorites = reloaded_product.favorites
    assert {favorite.user_id for favorite in favorites} == {10, 11}
    assert len(favorites) == 2
    assert all(favorite.product_id == product.id for favorite in favorites)
    assert reloaded_product.favorites is favorites


def test_cross_storage_string_target_lazy_load(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """跨 storage 字符串目标解析应允许显式指定目标 storage。"""
    product_db, favorite_db, engines = engine_pair

    captured_models: list[tuple[type[CRUDBaseModel], type[CRUDBaseModel]]] = []

    def build_models() -> None:
        captured_models.append(
            build_cross_storage_models(
                product_db,
                favorite_db,
                use_string_target=True,
                target_storage=product_db,
            )
        )

    assert_only_missing_storage_parameter_gap(
        build_models,
        source_engine=engines[1],
        target_engine=engines[0],
    )

    Product, UserFavorite = captured_models[0]

    product = Product.create(name="Widget")
    favorite = UserFavorite.create(user_id=1, product_id=product.id)

    reloaded_favorite = UserFavorite.get(favorite.id)
    assert reloaded_favorite is not None

    loaded_product = reloaded_favorite.product
    assert loaded_product is not None
    assert loaded_product.id == product.id
    assert loaded_product.name == "Widget"


def test_cross_storage_prefetch_many_to_one(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """跨 storage 多对一预取应查询目标模型所在的 storage。"""
    product_db, favorite_db, _ = engine_pair
    Product, UserFavorite = build_cross_storage_models(product_db, favorite_db)

    product = Product.create(name="Widget")
    favorite = UserFavorite.create(user_id=1, product_id=product.id)

    favorites = UserFavorite.all()
    assert len(favorites) == 1
    assert favorites[0].id == favorite.id

    prefetch(favorites, "product")

    loaded_product = favorites[0].product
    assert loaded_product is not None
    assert loaded_product.id == product.id
    assert loaded_product.name == "Widget"


def test_cross_storage_prefetch_many_to_one_with_string_target_and_explicit_storage(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """跨 storage 多对一预取应支持字符串目标与显式 storage。"""
    product_db, favorite_db, engines = engine_pair

    captured_models: list[tuple[type[CRUDBaseModel], type[CRUDBaseModel]]] = []

    def build_models() -> None:
        captured_models.append(
            build_cross_storage_models(
                product_db,
                favorite_db,
                use_string_target=True,
                target_storage=product_db,
            )
        )

    assert_only_missing_storage_parameter_gap(
        build_models,
        source_engine=engines[1],
        target_engine=engines[0],
    )

    Product, UserFavorite = captured_models[0]
    product = Product.create(name="Widget")
    favorite = UserFavorite.create(user_id=1, product_id=product.id)

    favorites = UserFavorite.all()
    assert len(favorites) == 1
    assert favorites[0].id == favorite.id

    prefetch(favorites, "product")

    loaded_product = favorites[0].product
    assert loaded_product is not None
    assert loaded_product.id == product.id
    assert loaded_product.name == "Widget"


def test_cross_storage_prefetch_one_to_many(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """跨 storage 一对多预取应查询目标模型所在的 storage。"""
    product_db, favorite_db, _ = engine_pair
    Product, UserFavorite = build_cross_storage_models(product_db, favorite_db)

    product = Product.create(name="Widget")
    UserFavorite.create(user_id=10, product_id=product.id)
    UserFavorite.create(user_id=11, product_id=product.id)

    products = Product.all()
    assert len(products) == 1

    prefetch(products, "favorites")

    favorites = products[0].favorites
    assert len(favorites) == 2
    assert {favorite.user_id for favorite in favorites} == {10, 11}
    assert all(favorite.product_id == product.id for favorite in favorites)


def test_select_options_prefetch_supports_cross_storage_string_target(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """跨 storage 的 select().options(prefetch()) 应支持字符串目标与显式 storage。"""
    product_db, favorite_db, engines = engine_pair

    captured_models: list[tuple[type[CRUDBaseModel], type[CRUDBaseModel]]] = []

    def build_models() -> None:
        captured_models.append(
            build_cross_storage_models(
                product_db,
                favorite_db,
                use_string_target=True,
                target_storage=product_db,
            )
        )

    assert_only_missing_storage_parameter_gap(
        build_models,
        source_engine=engines[1],
        target_engine=engines[0],
    )

    Product, UserFavorite = captured_models[0]
    product = Product.create(name="Widget")
    favorite = UserFavorite.create(user_id=1, product_id=product.id)

    session = Session(favorite_db)
    try:
        stmt = select(UserFavorite).options(prefetch("product"))
        favorites = session.execute(stmt).all()
    finally:
        session.close()

    assert len(favorites) == 1
    assert favorites[0].id == favorite.id
    loaded_product = favorites[0].product
    assert loaded_product is not None
    assert loaded_product.id == product.id
    assert loaded_product.name == "Widget"


def test_relationship_storage_conflict_raises_validation_error(
    engine_pair: tuple[Storage, Storage, tuple[str, str]]
) -> None:
    """当显式 storage 与目标模型绑定 storage 冲突时，应抛出明确异常。"""
    product_db, favorite_db, _ = engine_pair
    ProductBase = declarative_base(product_db, crud=True)
    FavoriteBase = declarative_base(favorite_db, crud=True)

    class Product(ProductBase):
        __tablename__ = "products"

        id = Column(int, primary_key=True)
        name = Column(str)

    class UserFavorite(FavoriteBase):
        __tablename__ = "favorites"

        id = Column(int, primary_key=True)
        product_id = Column(int)
        product = Relationship(
            Product,
            foreign_key="product_id",
            storage=favorite_db,
            uselist=False,
        )

    product = Product.create(name="Widget")
    favorite = UserFavorite.create(product_id=product.id)
    reloaded_favorite = UserFavorite.get(favorite.id)
    assert reloaded_favorite is not None

    with pytest.raises(ValidationError, match="different storage"):
        _ = reloaded_favorite.product
