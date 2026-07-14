"""按核心、内置零依赖和可选扩展分层验证后端契约。"""

from dataclasses import dataclass
from pathlib import Path
import random
from typing import Type

import pytest

from pytuck import Column, PureBaseModel, Session, Storage, declarative_base, insert, select
from pytuck.backends import BackendRegistry, StorageBackend
from pytuck.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class EngineContract:
    """描述后端所属层级和文件扩展名。"""

    name: str
    extension: str
    tier: str


ENGINE_CONTRACTS = (
    EngineContract("pytuck", "pytuck", "core"),
    EngineContract("json", "json", "bundled"),
    EngineContract("jsonl", "zip", "bundled"),
    EngineContract("csv", "zip", "bundled"),
    EngineContract("sqlite", "sqlite", "bundled"),
    EngineContract("duckdb", "duckdb", "optional"),
    EngineContract("excel", "xlsx", "optional"),
    EngineContract("xml", "xml", "optional"),
)


def _require_engine(contract: EngineContract) -> None:
    backend = BackendRegistry.get(contract.name)
    if backend is None or not backend.is_available():
        pytest.skip(f"{contract.name} 后端在当前环境不可用")


@pytest.mark.parametrize("contract", ENGINE_CONTRACTS, ids=lambda item: item.name)
def test_all_available_engines_follow_basic_object_contract(
    tmp_path: Path,
    contract: EngineContract,
) -> None:
    """所有可用后端都应支持最小模型、CRUD 和持久化重开。"""
    _require_engine(contract)
    database_path = tmp_path / f"contract.{contract.extension}"
    db = Storage(file_path=database_path, engine=contract.name)
    Base: Type[PureBaseModel] = declarative_base(db)

    class Item(Base):
        __tablename__ = "items"

        id = Column(int, primary_key=True)
        name = Column(str, nullable=False, index=True)
        score = Column(int, nullable=False)
        enabled = Column(bool, nullable=False)

    session = Session(db)
    session.execute(insert(Item).values(name="alpha", score=10, enabled=True))
    session.execute(insert(Item).values(name="beta", score=20, enabled=False))
    session.commit()
    session.close()
    db.close()

    reopened = Storage(file_path=database_path, engine=contract.name)
    ReopenedBase: Type[PureBaseModel] = declarative_base(reopened)

    class ReopenedItem(ReopenedBase):
        __tablename__ = "items"

        id = Column(int, primary_key=True)
        name = Column(str, nullable=False, index=True)
        score = Column(int, nullable=False)
        enabled = Column(bool, nullable=False)

    reopened_session = Session(reopened)
    rows = reopened_session.execute(select(ReopenedItem)).all()
    actual = sorted(
        (row.name, row.score, row.enabled)
        for row in rows
    )
    assert actual == [("alpha", 10, True), ("beta", 20, False)]
    reopened_session.close()
    reopened.close()


def test_contract_tiers_keep_external_dependencies_outside_core() -> None:
    """核心和内置层不得声明第三方依赖。"""
    standard_library_dependencies = {"sqlite3"}

    for contract in ENGINE_CONTRACTS:
        backend = BackendRegistry.get(contract.name)
        assert backend is not None
        dependencies = set(backend.REQUIRED_DEPENDENCIES)
        if contract.tier in {"core", "bundled"}:
            assert dependencies <= standard_library_dependencies
        else:
            assert dependencies - standard_library_dependencies


def test_lazy_builtin_engine_names_remain_reserved() -> None:
    """惰性适配器尚未导入时，第三方后端也不能抢占内置引擎名称。"""
    with pytest.raises(ConfigurationError, match="engine name is reserved"):
        class ConflictingDuckDBBackend(StorageBackend):
            ENGINE_NAME = "duckdb"



def test_lazy_loading_does_not_change_builtin_engine_order() -> None:
    """扩展适配器的请求顺序不得改变公开的内置引擎顺序。"""
    expected = [contract.name for contract in ENGINE_CONTRACTS]

    assert BackendRegistry.list_engines()[:len(expected)] == expected
    assert BackendRegistry.get("xml") is not None
    assert BackendRegistry.get("duckdb") is not None
    assert BackendRegistry.list_engines()[:len(expected)] == expected


def test_pytuck_core_state_machine_matches_python_oracle(tmp_path: Path) -> None:
    """用确定性操作序列验证 Pytuck CRUD、回滚和重开语义。"""
    database_path = tmp_path / "state-machine.pytuck"
    db = Storage(file_path=database_path, engine="pytuck")
    db.create_table(
        "items",
        [
            Column(int, name="id", primary_key=True),
            Column(str, name="name", nullable=False),
            Column(int, name="score", nullable=False),
        ],
    )

    oracle: dict[int, dict[str, object]] = {}
    generator = random.Random(20260714)
    for step in range(180):
        item_id = generator.randint(1, 48)
        if item_id not in oracle:
            record: dict[str, object] = {
                "id": item_id,
                "name": f"item-{step}",
                "score": generator.randint(-1000, 1000),
            }
            db.insert("items", record)
            oracle[item_id] = record.copy()
        elif generator.random() < 0.7:
            changes: dict[str, object] = {
                "name": f"updated-{step}",
                "score": generator.randint(-1000, 1000),
            }
            db.update("items", item_id, changes)
            oracle[item_id].update(changes)
        else:
            db.delete("items", item_id)
            del oracle[item_id]

        if step % 15 == 0:
            actual = {int(row["id"]): row for row in db.query("items", [])}
            assert actual == oracle

    before_rollback = {key: value.copy() for key, value in oracle.items()}
    with pytest.raises(RuntimeError, match="rollback-contract"):
        with db.transaction():
            db.insert("items", {"id": 999, "name": "temporary", "score": 1})
            if oracle:
                first_id = next(iter(oracle))
                db.update("items", first_id, {"score": 999999})
            raise RuntimeError("rollback-contract")

    assert {int(row["id"]): row for row in db.query("items", [])} == before_rollback
    db.flush()
    db.close()

    reopened = Storage(file_path=database_path, engine="pytuck")
    persisted = {int(row["id"]): row for row in reopened.query("items", [])}
    assert persisted == oracle
    reopened.close()
