"""在未安装任何 extras 的独立环境中验证 Pytuck 核心。"""

from importlib import metadata
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Type


OPTIONAL_MODULES = {"duckdb", "lxml", "openpyxl", "orjson", "pytz"}
OPTIONAL_BACKEND_MODULES = {
    "pytuck.backends.backend_duckdb",
    "pytuck.backends.backend_excel",
    "pytuck.backends.backend_xml",
}


def _assert_distribution_has_no_core_dependencies() -> None:
    requirements = metadata.requires("pytuck") or []
    core_requirements = [requirement for requirement in requirements if "extra ==" not in requirement]
    if core_requirements:
        raise AssertionError(f"发现核心运行时依赖：{core_requirements}")


def main() -> None:
    """完成零依赖导入、CRUD 和重开验证。"""
    _assert_distribution_has_no_core_dependencies()

    from pytuck import Column, PureBaseModel, Session, Storage, declarative_base, insert, select

    imported_optional_modules = OPTIONAL_MODULES.intersection(sys.modules)
    if imported_optional_modules:
        raise AssertionError(f"核心导入加载了可选模块：{sorted(imported_optional_modules)}")

    with TemporaryDirectory(prefix="pytuck-zero-dependency-") as temp_dir:
        path = Path(temp_dir) / "smoke.pytuck"
        db = Storage(file_path=path, auto_flush=True)
        Base: Type[PureBaseModel] = declarative_base(db)

        class Item(Base):
            __tablename__ = "items"

            id = Column(int, primary_key=True)
            name = Column(str, nullable=False)

        session = Session(db)
        session.execute(insert(Item).values(name="zero-dependency"))
        session.commit()
        session.close()
        db.close()

        reopened = Storage(file_path=path)
        ReopenedBase: Type[PureBaseModel] = declarative_base(reopened)

        class ReopenedItem(ReopenedBase):
            __tablename__ = "items"

            id = Column(int, primary_key=True)
            name = Column(str, nullable=False)

        reopened_session = Session(reopened)
        item = reopened_session.execute(select(ReopenedItem)).one()
        if item.name != "zero-dependency":
            raise AssertionError(f"重开结果不正确：{item.name!r}")
        reopened_session.close()
        reopened.close()

    imported_optional_backends = OPTIONAL_BACKEND_MODULES.intersection(sys.modules)
    if imported_optional_backends:
        raise AssertionError(
            f"默认 Pytuck 路径加载了扩展后端：{sorted(imported_optional_backends)}"
        )

    from pytuck.backends import BackendRegistry

    if BackendRegistry.get("duckdb") is None:
        raise AssertionError("按需请求 duckdb 时未加载扩展适配器")
    if "pytuck.backends.backend_duckdb" not in sys.modules:
        raise AssertionError("duckdb 扩展适配器未按需导入")
    if "duckdb" in sys.modules:
        raise AssertionError("加载扩展适配器时不应提前导入第三方 duckdb")

    print("Pytuck 零依赖 wheel smoke 通过")


if __name__ == "__main__":
    main()
